#!/usr/bin/env python3
"""比较两个文本文件，输出 unified diff。

只做文本层比较：编码先各自嗅探解码，再按行比。所以 UTF-8 的 a.txt 和 GBK 的
b.txt 只要内容一致就是"无差异"，这正是实际排查时想要的结果。
"""

import argparse
import difflib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import txt_common as C  # noqa: E402

C.main_guard()


def prepare(path, ns):
    text, info = C.read_text(path, ns.source_encoding)
    lines = text.splitlines()
    if ns.ignore_space:
        lines = [" ".join(line.split()) for line in lines]
    if ns.ignore_case:
        lines = [line.casefold() for line in lines]
    return text.splitlines(), lines, info


def main():
    p = argparse.ArgumentParser(description="文本 diff（unified）")
    p.add_argument("left", help="旧文件 / 基准文件")
    p.add_argument("right", help="新文件 / 对比文件")
    p.add_argument("-o", "--output", help="把 diff 写到文件；默认打印到 stdout")
    p.add_argument("--context", type=int, default=3, help="上下文行数，默认 3")
    p.add_argument("--ignore-space", action="store_true")
    p.add_argument("--ignore-case", action="store_true")
    p.add_argument("--stat", action="store_true", help="只输出增删统计")
    p.add_argument("--json", action="store_true", help="以 JSON 报告代替 diff 文本")
    p.add_argument("--from", dest="source_encoding")
    ns = p.parse_args()

    left_raw, left_cmp, left_info = prepare(ns.left, ns)
    right_raw, right_cmp, right_info = prepare(ns.right, ns)

    matcher = difflib.SequenceMatcher(None, left_cmp, right_cmp)
    added = removed = 0
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag in ("replace", "delete"):
            removed += i2 - i1
        if tag in ("replace", "insert"):
            added += j2 - j1

    diff_lines = list(difflib.unified_diff(
        left_raw, right_raw, fromfile=str(Path(ns.left).name),
        tofile=str(Path(ns.right).name), n=ns.context, lineterm=""))
    identical = not diff_lines

    payload = {"left": str(Path(ns.left).resolve()),
               "right": str(Path(ns.right).resolve()),
               "left_encoding": left_info["encoding"],
               "right_encoding": right_info["encoding"],
               "identical": identical, "added": added, "removed": removed,
               "changed": added + removed, "similarity": round(matcher.ratio(), 4)}

    if ns.json or ns.stat:
        if ns.output:
            target = Path(ns.output).resolve()
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                              encoding="utf-8")
            payload["output"] = str(target)
        return C.emit(payload)

    body = "\n".join(diff_lines) + ("\n" if diff_lines else "")
    if ns.output:
        target = Path(ns.output).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
        payload["output"] = str(target)
        payload["diff_lines"] = len(diff_lines)
        return C.emit(payload)
    if body:
        sys.stdout.write(body)
    sys.stderr.write(json.dumps({"identical": identical, "added": added,
                                 "removed": removed,
                                 "similarity": payload["similarity"]},
                                ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
