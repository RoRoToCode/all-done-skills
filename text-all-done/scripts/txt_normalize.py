#!/usr/bin/env python3
"""规范化文本：换行风格、行尾空白、连续空行、可选去 BOM。

这些是排版前最常见的清洗步骤。默认全部动作都开，用 --keep-* 关掉其中某一项，
而不是让调用方拼一串互相矛盾的开关。
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import txt_common as C  # noqa: E402

C.main_guard()


def normalise(text, ns):
    stats = {"trailing_removed": 0, "blank_collapsed": 0, "bom_removed": False}
    if text.startswith("\ufeff"):
        text = text.lstrip("\ufeff")
        stats["bom_removed"] = True
    lines = text.splitlines()
    out = []
    blank_run = 0
    for line in lines:
        if not ns.keep_trailing:
            stripped = line.rstrip()
            if stripped != line:
                stats["trailing_removed"] += 1
            line = stripped
        if not line.strip():
            blank_run += 1
            if blank_run > ns.max_blank:
                stats["blank_collapsed"] += 1
                continue
        else:
            blank_run = 0
        out.append(line)
    while out and not out[-1].strip() and ns.trim_ends:
        out.pop()
    while out and not out[0].strip() and ns.trim_ends:
        out.pop(0)
    body = "\n".join(out)
    if ns.final_newline and body:
        body += "\n"
    stats["lines"] = len(out)
    return body, stats


def main():
    p = argparse.ArgumentParser(description="文本规范化（换行/行尾空白/空行）")
    p.add_argument("input")
    p.add_argument("-o", "--output")
    p.add_argument("--newline", default="keep", choices=("keep", "lf", "crlf", "cr"))
    p.add_argument("--from", dest="source_encoding")
    p.add_argument("--to", default="utf-8")
    p.add_argument("--max-blank", type=int, default=1,
                   help="允许的连续空行数，默认 1（即最多一个空行）")
    p.add_argument("--keep-trailing", action="store_true", help="保留行尾空白")
    p.add_argument("--no-trim-ends", dest="trim_ends", action="store_false",
                   help="保留首尾空行")
    p.add_argument("--no-final-newline", dest="final_newline", action="store_false")
    p.set_defaults(trim_ends=True, final_newline=True)
    ns = p.parse_args()

    text, info = C.read_text(ns.input, ns.source_encoding)
    body, stats = normalise(text, ns)
    target = ns.output or C.derive_output(ns.input, "-clean" + Path(ns.input).suffix)
    source, target = C.guard_paths(ns.input, target)
    written = C.write_text(target, body, ns.to, ns.newline)
    return C.emit({"output": str(written), "source_encoding": info["encoding"],
                   "encoding_out": C.normalise_encoding(ns.to),
                   "newline": ns.newline, **stats})


if __name__ == "__main__":
    sys.exit(main())
