#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""eb-from-md：Markdown / HTML → EPUB3（按 # 标题切章，带 nav + NCX）。"""
import argparse
import os
import posixpath
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eb_common import (build_epub, die, html_body, markdown_to_xhtml,
                       read_source, result, setup_stdout, word_count,
                       EXIT_USAGE)


def split_markdown(text, split_level):
    """按 #~###### 中不超过 split_level 的标题切章，标题行保留在章节正文里。"""
    chunks, cur = [], None
    for line in text.splitlines():
        m = re.match(r"^(#{1,6})\s+(.*)$", line.strip())
        if m and len(m.group(1)) <= split_level:
            cur = {"title": m.group(2).strip() or "未命名",
                   "level": len(m.group(1)), "lines": []}
            chunks.append(cur)
        if cur is None:
            cur = {"title": "正文", "level": 1, "lines": []}
            chunks.append(cur)
        cur["lines"].append(line)
    return [c for c in chunks if "".join(c["lines"]).strip()]


def main():
    setup_stdout()
    ap = argparse.ArgumentParser(description="Markdown / HTML 生成 EPUB")
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--title")
    ap.add_argument("--author")
    ap.add_argument("--language", default="zh-CN")
    ap.add_argument("--cover", help="封面图片")
    ap.add_argument("--split-level", type=int, default=1,
                    help="切章的最大标题级数（1=只按 # 切）")
    ap.add_argument("--html", action="store_true", help="把输入当作 HTML 片段")
    ap.add_argument("--encoding")
    args = ap.parse_args()
    if not 1 <= args.split_level <= 6:
        die("--split-level 需在 1-6 之间", EXIT_USAGE)

    text = read_source(args.input, args.encoding)
    stem = os.path.splitext(os.path.basename(args.input))[0]
    if args.html:
        chapters = [{"title": args.title or stem, "level": 1,
                     "body": html_body(text.encode("utf-8"))}]
    else:
        chunks = split_markdown(text, args.split_level)
        if not chunks:
            die("输入内容为空", EXIT_USAGE)
        chapters = [{"title": c["title"], "level": c["level"],
                     "body": markdown_to_xhtml("\n".join(c["lines"]))}
                    for c in chunks]
    cover = None
    if args.cover:
        if not os.path.isfile(args.cover):
            die("封面图片不存在：%s" % args.cover, EXIT_USAGE)
        with open(args.cover, "rb") as f:
            cover = (posixpath.basename(args.cover), f.read())
    meta = {"title": args.title or stem,
            "creator": [args.author] if args.author else [],
            "language": args.language}
    out = build_epub(args.output, chapters, meta, cover=cover) or args.output
    words = sum(word_count(c["body"]) for c in chapters)
    result(out, 章节=len(chapters), 字数=words, 字节=os.path.getsize(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
