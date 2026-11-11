#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""eb-extract：把 EPUB 正文按章节导出为 Markdown / TXT，可选导出图片。"""
import argparse
import os
import posixpath
import re
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eb_common import (Epub, conflict_dir, ext_of, json_dump, norm_href,
                       plain_text, result, safe_name, setup_stdout, word_count,
                       xhtml_to_markdown)

IMG_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")


def main():
    setup_stdout()
    ap = argparse.ArgumentParser(description="导出 EPUB 正文")
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True, help="输出目录")
    ap.add_argument("--format", choices=["md", "txt"], default="md")
    ap.add_argument("--no-images", action="store_true", help="不导出图片（保留原始引用）")
    args = ap.parse_args()

    ep = Epub(args.input)
    chapters = ep.chapters()
    if not chapters:
        from eb_common import die, EXIT_FORMAT
        die("这本书没有可读章节", EXIT_FORMAT)

    outdir = conflict_dir(args.output)
    if outdir is None:
        print("已跳过（输出目录已存在，EBOOK_ON_CONFLICT=skip）")
        return 0
    args.output = outdir
    chap_dir = os.path.join(outdir, "chapters")
    img_dir = os.path.join(outdir, "images")
    os.makedirs(chap_dir, exist_ok=True)
    if not args.no_images:
        os.makedirs(img_dir, exist_ok=True)

    cache = {}
    manifest = []

    def remap(md, doc_path, prefix):
        """把 Markdown 里的图片引用改写到导出目录，并复制图片文件。"""
        copied = []

        def repl(m):
            alt, raw = m.group(1), m.group(2)
            key = norm_href(doc_path, raw)
            if not key or not ep.has(key):
                return m.group(0)
            if key not in cache:
                base = safe_name(posixpath.basename(key), 40)
                cache[key] = "%03d-%s" % (len(cache) + 1, base)
            name = cache[key]
            if not args.no_images:
                dst = os.path.join(img_dir, name)
                if not os.path.isfile(dst):
                    with open(dst, "wb") as f:
                        f.write(ep.read(key))
                copied.append(name)
            return "![%s](%s%s)" % (alt, prefix, urllib.parse.quote(name))
        return IMG_RE.sub(repl, md), copied

    full_parts = []
    for i, ch in enumerate(chapters, 1):
        data = ep.read(ch["path"])
        if args.format == "md":
            text = xhtml_to_markdown(data)
            text, imgs = remap(text, ch["path"], "../images/")
            full_text, _ = remap(xhtml_to_markdown(data), ch["path"], "images/")
        else:
            text = plain_text(data)
            full_text = text
            imgs = []
        fname = "chapter-%03d.%s" % (i, args.format)
        with open(os.path.join(chap_dir, fname), "w", encoding="utf-8") as f:
            f.write(text.rstrip() + "\n")
        heading = "# %s" % ch["title"] if args.format == "md" else ch["title"]
        full_parts.append(heading + "\n\n" + full_text.rstrip())
        manifest.append({
            "index": i, "title": ch["title"], "level": ch["level"],
            "source": ch["path"], "file": "chapters/" + fname,
            "words": word_count(text), "images": imgs,
        })

    full_name = "full." + args.format
    with open(os.path.join(outdir, full_name), "w", encoding="utf-8") as f:
        f.write("\n\n".join(full_parts) + "\n")
    payload = {
        "source": os.path.abspath(ep.path), "title": ep.title(),
        "format": args.format, "chapters": manifest,
        "chapter_count": len(manifest),
        "word_count": sum(c["words"] for c in manifest),
        "images": sorted(set(cache.values())),
    }
    json_dump(os.path.join(outdir, "manifest.json"), payload)
    result(os.path.join(outdir, full_name), 章节=len(manifest),
           字数=payload["word_count"], 图片=len(payload["images"]))
    result(os.path.join(outdir, "manifest.json"))
    ep.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
