#!/usr/bin/env python3
"""按行数、字符数或字节数把大文本切成多份。

切分只发生在行边界，不会把一个字/一个词劈成两半；单行就超过阈值时该行独立
成一份并在报告里标 oversized。目标目录里同名文件自动加 -2/-3，不覆盖旧产物。
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import txt_common as C  # noqa: E402

C.main_guard()


def sized_chunks(lines, by, size, encoding):
    chunk, weight = [], 0
    for line in lines:
        cost = 1 if by == "lines" else (
            len(line) if by == "chars" else len(line.encode(encoding, "replace")))
        if chunk and weight + cost > size:
            yield chunk
            chunk, weight = [], 0
        chunk.append(line)
        weight += cost
    if chunk:
        yield chunk


def unique_path(directory, prefix, index, suffix):
    candidate = directory / ("%s-%03d%s" % (prefix, index, suffix))
    bump = 2
    while candidate.exists():
        candidate = directory / ("%s-%03d-%d%s" % (prefix, index, bump, suffix))
        bump += 1
    return candidate


def main():
    p = argparse.ArgumentParser(description="按行/字符/字节切分文本")
    p.add_argument("input")
    p.add_argument("-o", "--output", required=True, help="输出目录")
    p.add_argument("--by", default="lines", choices=("lines", "chars", "bytes"))
    p.add_argument("--size", type=int, required=True, help="每份的最大行数/字符数/字节数")
    p.add_argument("--prefix", help="文件名前缀，默认取输入文件名")
    p.add_argument("--from", dest="source_encoding")
    p.add_argument("--to", default="utf-8")
    p.add_argument("--newline", default="keep", choices=("keep", "lf", "crlf", "cr"))
    ns = p.parse_args()

    if ns.size <= 0:
        C.fail("--size 必须是正整数", 2)
    text, info = C.read_text(ns.input, ns.source_encoding)
    lines = text.splitlines()
    source = Path(ns.input).resolve()
    outdir = Path(ns.output).resolve()
    if outdir == source:
        raise SystemExit("输出目录不能是输入文件本身")
    outdir.mkdir(parents=True, exist_ok=True)
    prefix = ns.prefix or source.stem
    suffix = source.suffix or ".txt"
    codec = C.normalise_encoding(ns.to) or "utf-8"

    parts, oversized = [], []
    for index, chunk in enumerate(sized_chunks(lines, ns.by, ns.size, codec), start=1):
        target = unique_path(outdir, prefix, index, suffix)
        written = C.write_text(target, "\n".join(chunk) + "\n", ns.to, ns.newline)
        weight = len(chunk) if ns.by == "lines" else (
            sum(len(line) for line in chunk) if ns.by == "chars"
            else sum(len(line.encode(codec, "replace")) for line in chunk))
        entry = {"part": index, "file": str(written), "lines": len(chunk),
                 "weight": weight}
        if len(chunk) == 1 and weight > ns.size:
            oversized.append(index)
            entry["oversized"] = True
        parts.append(entry)

    manifest = outdir / ("%s-manifest.json" % prefix)
    bump = 2
    while manifest.exists():
        manifest = outdir / ("%s-manifest-%d.json" % (prefix, bump))
        bump += 1
    manifest.write_text(json.dumps({"source": str(source), "by": ns.by,
                                    "size": ns.size, "parts": len(parts),
                                    "encoding": codec, "items": parts},
                                   ensure_ascii=False, indent=2), encoding="utf-8")
    return C.emit({"output_dir": str(outdir), "parts": len(parts),
                   "by": ns.by, "size": ns.size,
                   "oversized_parts": oversized, "manifest": str(manifest),
                   "warnings": (["有单行超过 --size，已独立成一份：%s" % oversized]
                                if oversized else [])})


if __name__ == "__main__":
    sys.exit(main())
