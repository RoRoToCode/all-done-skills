#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""eb-merge：把多本 EPUB 合成一本，书名作一级目录、原章节作二级。"""
import argparse
import glob
import os
import posixpath
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eb_common import (Epub, build_epub, chapter_payload, result, setup_stdout,
                       xml_escape, EXIT_USAGE)


def main():
    setup_stdout()
    ap = argparse.ArgumentParser(description="合并多本 EPUB")
    ap.add_argument("--inputs", help="逗号分隔的 EPUB 路径，也支持通配符")
    ap.add_argument("--input-dir", help="目录（取其中全部 .epub）")
    ap.add_argument("--output", required=True, help="合并后的 EPUB")
    ap.add_argument("--title", help="合集书名")
    ap.add_argument("--author", help="合集作者")
    ap.add_argument("--no-volume-page", action="store_true", help="不生成每本书的扉页章节")
    args = ap.parse_args()

    paths = []
    if args.inputs:
        for part in args.inputs.split(","):
            part = part.strip().strip('"').strip("'")
            if not part:
                continue
            hit = sorted(glob.glob(part)) if any(c in part for c in "*?[") else [part]
            paths.extend(hit)
    if args.input_dir:
        paths.extend(sorted(glob.glob(os.path.join(args.input_dir, "*.epub"))))
    paths = [p for p in dict.fromkeys(os.path.abspath(p) for p in paths)
             if p.lower().endswith(".epub") and os.path.isfile(p)]
    if len(paths) < 2:
        from eb_common import die
        die("合并至少需要 2 本 EPUB（当前 %d 本）" % len(paths), EXIT_USAGE)

    all_chapters, resources, authors = [], {}, []
    cover = None
    for i, path in enumerate(paths, 1):
        ep = Epub(path)
        ep.guard_writable()
        if cover is None and ep.cover_path() and ep.has(ep.cover_path()):
            cover = (posixpath.basename(ep.cover_path()), ep.read(ep.cover_path()))
        if ep.dc("creator"):
            authors.extend(ep.metadata["creator"])
        if not args.no_volume_page:
            info = "%s · %s" % ("/".join(ep.metadata.get("creator") or []) or "佚名",
                                ep.dc("publisher") or "")
            all_chapters.append({
                "title": ep.title(), "level": 1,
                "body": "<h1>%s</h1><p>%s</p>" % (xml_escape(ep.title()),
                                                    xml_escape(info.strip(" ·"))),
            })
        bodies, res = chapter_payload(ep, ep.chapters(),
                                     "images/book%03d" % i)
        for ch in bodies:
            ch["level"] = min(3, int(ch["level"]) + (0 if args.no_volume_page else 1))
        all_chapters.extend(bodies)
        resources.update(res)
        print("  [%d/%d] %s — %d 章" % (i, len(paths), ep.title(), len(bodies)))
        ep.close()

    meta = {"title": args.title or "电子书合集",
            "creator": [args.author] if args.author else list(dict.fromkeys(authors)),
            "language": "zh-CN"}
    out = build_epub(args.output, all_chapters, meta, cover=cover,
                     resources=resources) or args.output
    result(out, 来源=len(paths), 章节=len(all_chapters),
           资源=len(resources), 字节=os.path.getsize(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
