#!/usr/bin/env python3
"""批量查找替换，支持正则与分组引用。

默认走正则；--literal 则把 pattern 当纯文本（内部 re.escape），避免文件里的
括号、点号被当成元字符。--dry-run 只报命中数，常用于先确认再落地。
"""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import txt_common as C  # noqa: E402

C.main_guard()


def build_pattern(ns):
    if ns.literal:
        source = re.escape(ns.pattern)
    else:
        source = ns.pattern
    if ns.multiline:
        source = "(?m)" + source
    if ns.dotall:
        source = "(?s)" + source
    flags = re.IGNORECASE if ns.ignore_case else 0
    try:
        return re.compile(source, flags)
    except re.error as exc:
        raise SystemExit("正则无效：%s" % exc)


def main():
    p = argparse.ArgumentParser(description="文本查找替换（支持正则）")
    p.add_argument("input")
    p.add_argument("-o", "--output")
    p.add_argument("--pattern", required=True, help="要查找的内容（默认按正则）")
    p.add_argument("--repl", default="", help="替换为，支持 \\1 分组引用；默认删掉")
    p.add_argument("--literal", action="store_true", help="把 --pattern 当纯文本")
    p.add_argument("--ignore-case", action="store_true")
    p.add_argument("--multiline", action="store_true", help="^ / $ 匹配每行首尾")
    p.add_argument("--dotall", action="store_true", help=". 匹配换行")
    p.add_argument("--limit", type=int, default=0, help="最多替换 N 处，0 为不限")
    p.add_argument("--dry-run", action="store_true", help="只报命中，不写文件")
    p.add_argument("--from", dest="source_encoding")
    p.add_argument("--to", default="utf-8")
    p.add_argument("--newline", default="keep", choices=("keep", "lf", "crlf", "cr"))
    ns = p.parse_args()

    text, info = C.read_text(ns.input, ns.source_encoding)
    pattern = build_pattern(ns)
    hits = pattern.findall(text)
    sample = Counter(h if isinstance(h, str) else "|".join(h) for h in hits)
    count = ns.limit if ns.limit > 0 else 0
    new_text, replaced = pattern.subn(ns.repl, text, count=count)

    payload = {"input": str(Path(ns.input).resolve()), "source_encoding": info["encoding"],
               "pattern": ns.pattern, "literal": ns.literal,
               "matches": len(hits), "replaced": replaced,
               "top_matches": sample.most_common(10)}
    if ns.dry_run or not ns.output:
        payload["dry_run"] = True
        return C.emit(payload)

    target = ns.output
    source, target = C.guard_paths(ns.input, target)
    written = C.write_text(target, new_text, ns.to, ns.newline)
    payload["output"] = str(written)
    payload["bytes_out"] = written.stat().st_size
    return C.emit(payload)


if __name__ == "__main__":
    sys.exit(main())
