#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""eb-from-text：纯文本小说 → EPUB（按「第X章 / Chapter N / 卷X」切章）。"""
import argparse
import os
import posixpath
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eb_common import (build_epub, die, html_lib, read_source, result,
                       setup_stdout, word_count, EXIT_USAGE)

DEFAULT_PATTERN = (r"^\s*(?:第[零一二三四五六七八九十百千〇两\d]+[章节回卷部篇]"
                   r"(?:\s+\S.*)?|(?:Chapter|CHAPTER)\s+\d+(?:\s+\S.*)?|"
                   r"卷[零一二三四五六七八九十\d]+(?:\s+\S.*)?)\s*$")


def text_to_xhtml(lines):
    out = []
    for line in lines:
        s = line.strip()
        if s:
            out.append("<p>%s</p>" % html_lib.escape(s, quote=False))
    return "\n".join(out)


def main():
    setup_stdout()
    ap = argparse.ArgumentParser(description="TXT 小说生成 EPUB")
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--title")
    ap.add_argument("--author")
    ap.add_argument("--language", default="zh-CN")
    ap.add_argument("--pattern", default=DEFAULT_PATTERN, help="章节标题正则")
    ap.add_argument("--encoding", help="文本编码，缺省自动探测 UTF-8 / GB18030")
    ap.add_argument("--cover", help="封面图片")
    args = ap.parse_args()
    try:
        rx = re.compile(args.pattern)
    except re.error as exc:
        die("章节正则无效：%s" % exc, EXIT_USAGE)

    text = read_source(args.input, args.encoding)
    stem = os.path.splitext(os.path.basename(args.input))[0]
    chunks, cur = [], None
    for line in text.splitlines():
        if rx.match(line):
            cur = {"title": line.strip(), "level": 1, "lines": [], "heading": True}
            chunks.append(cur)
            continue
        if cur is None:
            cur = {"title": args.title or stem, "level": 1,
                   "lines": [], "heading": False}
            chunks.append(cur)
        cur["lines"].append(line)
    # 书名/作者等前置内容并入第一章开头，避免多出一章「前言」但又不丢正文
    if len(chunks) > 1 and not chunks[0]["heading"]:
        chunks[1]["lines"] = chunks[0]["lines"] + chunks[1]["lines"]
        chunks.pop(0)
    chapters = [{"title": c["title"], "level": 1,
                 "body": text_to_xhtml(c["lines"])}
                for c in chunks if any(l.strip() for l in c["lines"])]
    if not chapters:
        die("输入内容为空", EXIT_USAGE)
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
