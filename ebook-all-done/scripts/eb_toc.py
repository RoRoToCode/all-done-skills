#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""eb-toc：导出目录（toc.md + toc.json）。"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eb_common import Epub, conflict_dir, conflict_path, json_dump, result, setup_stdout


def main():
    setup_stdout()
    ap = argparse.ArgumentParser(description="导出电子书目录")
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True, help="输出目录")
    args = ap.parse_args()

    ep = Epub(args.input)
    entries = ep.toc_entries()
    args.output = conflict_dir(args.output)
    if args.output is None:
        print("已跳过（输出目录已存在，EBOOK_ON_CONFLICT=skip）")
        return 0
    os.makedirs(args.output, exist_ok=True)
    lines = ["# 目录", ""]
    for e in entries:
        indent = "  " * (max(1, int(e.get("level") or 1)) - 1)
        href = e.get("href") or ""
        lines.append("%s- [%s](%s)" % (indent, e["title"], href))
    md = conflict_path(os.path.join(args.output, "toc.md"))
    with open(md, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    js = os.path.join(args.output, "toc.json")
    payload = {
        "source": os.path.abspath(ep.path),
        "title": ep.title(),
        "toc_source": ("nav.xhtml" if ep.nav_path() else
                       "toc.ncx" if ep.ncx_path() else "章节标题推断"),
        "entries": entries,
    }
    json_dump(js, payload)
    print("目录来源: %s，共 %d 项" % (payload["toc_source"], len(entries)))
    for e in entries[:12]:
        print("  %s%s" % ("  " * (int(e.get("level") or 1) - 1), e["title"]))
    if len(entries) > 12:
        print("  … 其余 %d 项见 toc.md" % (len(entries) - 12))
    result(md, 目录项=len(entries))
    result(js)
    ep.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
