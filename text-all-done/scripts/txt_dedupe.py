#!/usr/bin/env python3
"""按行去重，保留顺序（默认）或排序，并报告重复了什么。

键的归一化可以忽略大小写 / 首尾空白 / 全部空白，但不改动写出的那一行——
输出用的是第一次（或最后一次）出现的**原始文本**，不是归一化后的键。
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import txt_common as C  # noqa: E402

C.main_guard()


def key_of(line, ns):
    key = line.strip() if ns.strip else line
    if ns.ignore_space:
        key = "".join(key.split())
    if ns.ignore_case:
        key = key.casefold()
    return key


def main():
    p = argparse.ArgumentParser(description="按行去重")
    p.add_argument("input")
    p.add_argument("-o", "--output")
    p.add_argument("--ignore-case", action="store_true")
    p.add_argument("--ignore-space", action="store_true", help="忽略所有空白差异")
    p.add_argument("--no-strip", dest="strip", action="store_false",
                   help="不忽略首尾空白（默认忽略）")
    p.add_argument("--keep", default="first", choices=("first", "last"))
    p.add_argument("--sort", action="store_true", help="按字典序排序后输出")
    p.add_argument("--drop-blank", action="store_true", help="丢弃纯空行")
    p.add_argument("--from", dest="source_encoding")
    p.add_argument("--to", default="utf-8")
    p.add_argument("--newline", default="keep", choices=("keep", "lf", "crlf", "cr"))
    p.add_argument("--report-only", action="store_true", help="只统计，不写文件")
    p.set_defaults(strip=True)
    ns = p.parse_args()

    text, info = C.read_text(ns.input, ns.source_encoding)
    lines = text.splitlines()
    total = len(lines)
    seen, kept, duplicates = {}, [], {}
    for line in lines:
        if ns.drop_blank and not line.strip():
            continue
        key = key_of(line, ns)
        if key not in seen:
            seen[key] = len(kept)
            kept.append(line)
        else:
            duplicates[line] = duplicates.get(line, 0) + 1
            if ns.keep == "last":
                kept[seen[key]] = line

    if ns.sort:
        kept.sort()

    body = "\n".join(kept) + ("\n" if kept else "")
    payload = {"input": str(Path(ns.input).resolve()), "source_encoding": info["encoding"],
               "lines_in": total, "lines_out": len(kept),
               "removed": total - len(kept),
               "unique_keys": len(seen), "keep": ns.keep,
               "top_duplicates": sorted(duplicates.items(), key=lambda kv: -kv[1])[:10]}
    if ns.report_only:
        payload["report_only"] = True
        return C.emit(payload)

    target = ns.output or C.derive_output(ns.input, "-unique" + Path(ns.input).suffix)
    source, target = C.guard_paths(ns.input, target)
    written = C.write_text(target, body, ns.to, ns.newline)
    payload["output"] = str(written)
    return C.emit(payload)


if __name__ == "__main__":
    sys.exit(main())
