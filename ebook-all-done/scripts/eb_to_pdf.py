#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""eb-to-pdf：EPUB 正文 → PDF（本机 Edge / Chrome 无头打印，中文走系统字体）。"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eb_common import (Epub, STYLE_CSS, chapter_payload, html_to_pdf,
                       need_browser, result, setup_stdout, xml_escape)

PDF_CSS = STYLE_CSS + """
@page { size: A4; margin: 18mm 16mm; }
body { font-size: 11pt; }
.chapter { page-break-before: always; }
.chapter:first-of-type { page-break-before: auto; }
h1.chapter-title { font-size: 1.6em; text-align: center; margin: 1.2em 0 1.4em; }
"""

PAGE_SIZES = {"a4": "210mm 297mm", "a5": "148mm 210mm",
              "letter": "216mm 279mm", "b5": "176mm 250mm"}


def main():
    setup_stdout()
    ap = argparse.ArgumentParser(description="EPUB 转 PDF")
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--page-size", default="A4",
                    help="A4 / A5 / B5 / Letter，或自定义如 595x842（pt）")
    ap.add_argument("--no-images", action="store_true", help="去掉正文里的图片")
    ap.add_argument("--css", help="追加自定义 CSS 文件")
    args = ap.parse_args()
    need_browser()

    size = PAGE_SIZES.get(args.page_size.lower())
    if not size:
        if not re.fullmatch(r"\d+(?:\.\d+)?x\d+(?:\.\d+)?", args.page_size.lower()):
            from eb_common import die, EXIT_USAGE
            die("--page-size 需为 A4/A5/B5/Letter 或 595x842 形式", EXIT_USAGE)
        w, h = args.page_size.lower().split("x")
        size = "%spt %spt" % (w, h)
    css = PDF_CSS.replace("size: A4;", "size: %s;" % size)
    if args.css:
        with open(args.css, encoding="utf-8") as f:
            css += "\n" + f.read()

    ep = Epub(args.input)
    chapters = ep.chapters()
    if not chapters:
        from eb_common import die, EXIT_FORMAT
        die("这本书没有可读章节", EXIT_FORMAT)
    bodies, assets = chapter_payload(ep, chapters, "assets")
    parts = []
    for i, ch in enumerate(bodies, 1):
        body = ch["body"]
        if args.no_images:
            body = re.sub(r"<img\b[^>]*/>", "", body, flags=re.I)
        parts.append('<section class="chapter"><h1 class="chapter-title">%s</h1>\n%s\n</section>'
                     % (xml_escape(ch["title"]), body))
    html = ('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
            '<title>%s</title><style>%s</style></head><body>%s</body></html>'
            % (xml_escape(ep.title()), css, "\n".join(parts)))
    size_bytes = html_to_pdf(html, args.output,
                             assets={} if args.no_images else assets)
    pages = None
    try:
        from pypdf import PdfReader
        pages = len(PdfReader(args.output).pages)
    except Exception:
        pass
    print("章节 %d，资源 %d，页数 %s" % (len(chapters), len(assets),
                                        pages if pages is not None else "未探测"))
    result(args.output, 章节=len(chapters), 页数=pages, 字节=size_bytes)
    ep.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
