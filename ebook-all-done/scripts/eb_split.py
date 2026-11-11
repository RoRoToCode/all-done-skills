#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""eb-split：按目录顶层 / 章节 / 固定章数拆成多本独立 EPUB。"""
import argparse
import os
import posixpath
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eb_common import (Epub, build_epub, chapter_payload, conflict_dir, json_dump, result,
                       setup_stdout, EXIT_FORMAT)


def groups_of(ep, chapters, by, per):
    if not chapters:
        from eb_common import die
        die("这本书没有可读章节", EXIT_FORMAT)
    if by == "chapters":
        return [[c] for c in chapters]
    if by == "count":
        return [chapters[i:i + per] for i in range(0, len(chapters), per)]
    groups, cur = [], None
    for ch in chapters:
        if cur is None or int(ch.get("level") or 1) <= 1:
            cur = {"title": ch["title"], "chapters": []}
            groups.append(cur)
        cur["chapters"].append(ch)
    return [g["chapters"] for g in groups]


def main():
    setup_stdout()
    ap = argparse.ArgumentParser(description="按章拆分 EPUB")
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True, help="输出目录")
    ap.add_argument("--by", choices=["top", "chapters", "count"], default="top",
                    help="top=按目录顶层分卷，chapters=每章一本，count=每 N 章一本")
    ap.add_argument("--per", type=int, default=5, help="--by count 时每卷章数")
    args = ap.parse_args()
    args.output = conflict_dir(args.output)
    if args.output is None:
        print("已跳过（输出目录已存在，EBOOK_ON_CONFLICT=skip）")
        return 0
    os.makedirs(args.output, exist_ok=True)

    ep = Epub(args.input)
    ep.guard_writable()
    chapters = ep.chapters()
    groups = groups_of(ep, chapters, args.by, max(1, args.per))
    cover_path = ep.cover_path()
    cover = ((posixpath.basename(cover_path), ep.read(cover_path))
             if cover_path and ep.has(cover_path) else None)
    base_meta = {"title": ep.title(), "creator": ep.metadata.get("creator") or [],
                 "language": ep.dc("language") or "zh-CN",
                 "identifier": ep.dc("identifier") or ""}
    manifest = []
    for n, group in enumerate(groups, 1):
        bodies, resources = chapter_payload(ep, group, "images/vol%03d" % n)
        for ch in bodies:
            ch["level"] = int(ch.get("level") or 1)
        meta = dict(base_meta)
        meta["title"] = "%s（第 %d 卷）" % (base_meta["title"], n)
        meta["identifier"] = (base_meta["identifier"] or "ebook-all-done") + "-vol%03d" % n
        fname = "volume-%03d.epub" % n
        target = os.path.join(args.output, fname)
        actual = build_epub(target, bodies, meta, cover=cover,
                            resources=resources) or target
        manifest.append({"file": os.path.basename(actual), "title": meta["title"],
                         "chapters": [c["title"] for c in group],
                         "chapter_count": len(group),
                         "size_bytes": os.path.getsize(actual)})
        print("  第 %d 卷：%d 章，%d 资源，%d 字节" %
              (n, len(group), len(resources), os.path.getsize(actual)))
    payload = {"source": os.path.abspath(ep.path), "by": args.by,
               "volumes": manifest, "volume_count": len(manifest)}
    json_dump(os.path.join(args.output, "manifest.json"), payload)
    result(args.output, 分卷=len(manifest), 章节=len(chapters))
    ep.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
