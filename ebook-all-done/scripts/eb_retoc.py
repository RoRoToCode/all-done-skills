#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""eb-retoc：按缩进目录文本重建 NCX 与 nav.xhtml，另存新 EPUB。"""
import argparse
import os
import posixpath
import sys
from xml.etree import ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eb_common import (OPF_NS, Epub, edit_opf, manifest_element, nav_xhtml,
                       ncx_xml, no_overwrite, read_source, result, rewrite_epub,
                       setup_stdout, spine_element, EXIT_FORMAT, EXIT_USAGE)


def parse_toc_text(text, ep):
    docs = ep.spine_docs()
    entries, auto = [], 0
    for raw in text.splitlines():
        line = raw.rstrip("\r")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" \t"))
        expanded = line.replace("\t", "  ")
        indent = len(expanded) - len(expanded.lstrip(" "))
        level = 1 + indent // 2
        content = expanded.strip()
        explicit = None
        if "|" in content:
            content, target = content.rsplit("|", 1)
            content = content.strip()
            target = target.strip()
            if target:
                resolved = posixpath.normpath(posixpath.join(ep.opf_dir, target)).lstrip("/")
                if ep.has(resolved):
                    explicit = resolved
                elif ep.has(target):
                    explicit = target
                else:
                    from eb_common import die
                    die("目录项指向的文件不存在：%s" % target, EXIT_FORMAT)
        path = explicit
        if path is None:
            if auto >= len(docs):
                continue
            path = docs[auto]["path"]
            auto += 1
        href = posixpath.relpath(path, ep.opf_dir or ".")
        entries.append({"title": content or "未命名", "level": level,
                        "href": href, "path": path})
    if not entries:
        from eb_common import die
        die("目录文本里没有有效条目", EXIT_USAGE)
    return entries


def main():
    setup_stdout()
    ap = argparse.ArgumentParser(description="重建电子书目录")
    ap.add_argument("--input", required=True)
    ap.add_argument("--toc", required=True, help="缩进目录文本（每行一条，可分章用 | 文件名.xhtml）")
    ap.add_argument("--output", required=True, help="另存的新 EPUB")
    args = ap.parse_args()
    no_overwrite(args.input, args.output)
    ep = Epub(args.input)
    ep.guard_writable()
    entries = parse_toc_text(read_source(args.toc), ep)

    nav_path = posixpath.join(ep.opf_dir, "nav.xhtml").lstrip("/")
    ncx_path = posixpath.join(ep.opf_dir, "toc.ncx").lstrip("/")
    book_title = ep.title()
    nav_bytes = nav_xhtml(entries, book_title).encode("utf-8")
    ncx_bytes = ncx_xml(entries, ep.dc("identifier") or "ebook-all-done",
                        book_title).encode("utf-8")

    nav_href = posixpath.basename(nav_path)
    ncx_href = posixpath.basename(ncx_path)

    def apply(root):
        mf, sp = manifest_element(root), spine_element(root)
        nav_item = next((c for c in mf
                         if "nav" in (c.get("properties") or "").split()), None)
        if nav_item is None:
            nav_item = ET.SubElement(mf, "{%s}item" % OPF_NS, {"id": "ebook-nav"})
        nav_item.set("href", nav_href)
        nav_item.set("media-type", "application/xhtml+xml")
        nav_item.set("properties", "nav")
        ncx_item = next((c for c in mf
                         if c.get("media-type") == "application/x-dtbncx+xml"
                         or posixpath.splitext(c.get("href") or "")[1] == ".ncx"), None)
        if ncx_item is None:
            ncx_item = ET.SubElement(mf, "{%s}item" % OPF_NS, {"id": "ebook-ncx"})
        ncx_item.set("href", ncx_href)
        ncx_item.set("media-type", "application/x-dtbncx+xml")
        if sp is not None:
            sp.set("toc", ncx_item.get("id") or "ebook-ncx")

    replacements = {
        nav_path: nav_bytes,
        ncx_path: ncx_bytes,
        ep.opf_path: edit_opf(ep, apply),
    }
    rewrite_epub(ep, args.output, replacements=replacements)
    print("目录 %d 项，层级 %s" % (len(entries),
                                  sorted({e["level"] for e in entries})))
    for e in entries[:8]:
        print("  %s%s -> %s" % ("  " * (e["level"] - 1), e["title"], e["href"]))
    result(args.output, 目录项=len(entries), nav=nav_path, ncx=ncx_path)
    ep.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
