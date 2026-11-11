#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""eb-search：跨章节全文检索（关键词 / 正则），输出命中上下文。"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eb_common import (Epub, conflict_path, json_dump, plain_text, result,
                       setup_stdout)


def main():
    setup_stdout()
    ap = argparse.ArgumentParser(description="电子书全文检索")
    ap.add_argument("--input", required=True)
    ap.add_argument("--query", help="要搜索的关键词")
    ap.add_argument("--regex", help="正则表达式（与 --query 二选一）")
    ap.add_argument("--ignore-case", action="store_true")
    ap.add_argument("--context", type=int, default=30, help="上下文字符数")
    ap.add_argument("--max", type=int, default=0, help="最多保留多少条，0 表示不限")
    ap.add_argument("--output", help="结果文件（.json 或 .md）")
    args = ap.parse_args()
    if bool(args.query) == bool(args.regex):
        from eb_common import die, EXIT_USAGE
        die("--query 与 --regex 必须恰好给一个", EXIT_USAGE)

    flags = re.I if args.ignore_case else 0
    pattern = re.escape(args.query) if args.query else args.regex
    try:
        rx = re.compile(pattern, flags)
    except re.error as exc:
        from eb_common import die, EXIT_USAGE
        die("正则无效：%s" % exc, EXIT_USAGE)

    ep = Epub(args.input)
    hits = []
    for idx, ch in enumerate(ep.chapters(), 1):
        text = plain_text(ep.read(ch["path"]))
        for m in rx.finditer(text):
            lo, hi = max(0, m.start() - args.context), min(len(text), m.end() + args.context)
            hits.append({
                "chapter": idx, "title": ch["title"], "source": ch["path"],
                "offset": m.start(), "match": m.group(0),
                "context": ("…" if lo else "") + text[lo:hi] + ("…" if hi < len(text) else ""),
            })
            if args.max and len(hits) >= args.max:
                break
        if args.max and len(hits) >= args.max:
            break
    payload = {
        "source": os.path.abspath(ep.path), "title": ep.title(),
        "pattern": pattern, "mode": "query" if args.query else "regex",
        "ignore_case": bool(args.ignore_case), "total": len(hits),
        "chapters_searched": len(ep.chapters()), "hits": hits,
    }
    print("检索「%s」：命中 %d 处，涉及 %d 个章节" %
          (args.query or args.regex, len(hits),
           len({h["chapter"] for h in hits})))
    for h in hits[:5]:
        print("  [%s] …%s…" % (h["title"], h["context"][:80]))
    if args.output:
        if args.output.lower().endswith(".md"):
            lines = ["# 检索结果：%s" % (args.query or args.regex), "",
                     "命中 %d 处" % len(hits), ""]
            for h in hits:
                lines.append("## %s（位置 %d）" % (h["title"], h["offset"]))
                lines.append("> %s" % h["context"].replace("\n", " "))
                lines.append("")
            target = conflict_path(args.output)
            if target is not None:
                with open(target, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines))
            else:
                print("已跳过（输出已存在，EBOOK_ON_CONFLICT=skip）")
        else:
            json_dump(args.output, payload)
        result(args.output, 命中=len(hits))
    ep.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
