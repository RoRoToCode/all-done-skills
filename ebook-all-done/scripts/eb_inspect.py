#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""eb-inspect：电子书体检（元数据 / 结构 / 章节 / 字数 / 资源 / DRM）。"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eb_common import (Epub, IMAGE_EXT, FONT_EXT, STYLE_EXT, ext_of, json_dump,
                       plain_text, result, setup_stdout, word_count)


def main():
    setup_stdout()
    ap = argparse.ArgumentParser(description="电子书体检")
    ap.add_argument("--input", required=True, help="EPUB 文件")
    ap.add_argument("--output", help="把完整报告另存为 JSON")
    args = ap.parse_args()

    ep = Epub(args.input)
    info = ep.infos
    mimetype_first = ep.zf.namelist()[0].replace("\\", "/") == "mimetype"
    mimetype_stored = (mimetype_first and
                       info["mimetype"].compress_type == 0) if "mimetype" in info else False
    docs = ep.spine_docs()
    chapters = ep.chapters()
    assets = ep.assets()
    words = sum(word_count(plain_text(ep.read(d["path"]))) for d in docs)
    cover = ep.cover_path()
    data = {
        "file": os.path.abspath(ep.path),
        "size_bytes": os.path.getsize(ep.path),
        "epub_version": ep.version,
        "title": ep.title(),
        "creator": ep.metadata.get("creator") or [],
        "language": ep.dc("language"),
        "publisher": ep.dc("publisher"),
        "identifier": ep.dc("identifier"),
        "description": ep.dc("description"),
        "metadata": ep.metadata,
        "opf_path": ep.opf_path,
        "manifest_items": len(ep.manifest),
        "spine_items": len(ep.spine),
        "spine_docs": len(docs),
        "chapters": [{"title": c["title"], "level": c["level"], "path": c["path"]}
                     for c in chapters],
        "chapter_count": len(chapters),
        "word_count": words,
        "toc_source": ("nav.xhtml" if ep.nav_path() else
                       "toc.ncx" if ep.ncx_path() else "章节标题推断"),
        "nav": ep.nav_path(),
        "ncx": ep.ncx_path(),
        "cover": cover,
        "assets": {
            "images": sum(1 for a in assets if a["kind"] == "image"),
            "fonts": sum(1 for a in assets if a["kind"] == "font"),
            "styles": sum(1 for a in assets if a["kind"] == "style"),
            "total": len(assets),
        },
        "protected": ep.protected(),
        "mimetype_first": mimetype_first,
        "mimetype_stored": mimetype_stored,
        "zip_entries": len(ep.members),
    }
    print("书名: %s" % data["title"])
    print("作者: %s  |  语言: %s  |  EPUB %s" %
          ("/".join(data["creator"]) or "—", data["language"] or "—", data["epub_version"]))
    print("章节: %d  |  正文文件: %d  |  字数: %d  |  图片: %d  |  目录来源: %s" %
          (data["chapter_count"], data["spine_docs"], words,
           data["assets"]["images"], data["toc_source"]))
    print("封面: %s  |  DRM: %s  |  体积: %d 字节" %
          (cover or "无", "有（本技能不处理）" if data["protected"] else "无",
           data["size_bytes"]))
    if args.output:
        json_dump(args.output, data)
        result(args.output, 章节=data["chapter_count"], 字数=words)
    ep.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
