#!/usr/bin/env python3
"""Render Markdown or HTML into a PDF using a local headless Chromium browser.

Zero third-party Python dependencies. Chinese text renders through system fonts
(Microsoft YaHei / SimSun / Noto Sans CJK), so CJK content works out of the box.
"""

import argparse
import html as html_lib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CSS = SKILL_DIR / "assets" / "report.css"


def find_browser():
    override = os.environ.get("PDF_BROWSER")
    if override and Path(override).exists():
        return str(Path(override).resolve())
    for name in ("msedge", "microsoft-edge", "chrome", "google-chrome",
                 "chromium", "chromium-browser"):
        found = shutil.which(name)
        if found:
            return found
    candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/usr/bin/chromium",
        "/usr/bin/google-chrome",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    return None


def _inline(text):
    text = html_lib.escape(text, quote=False)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r'<img alt="\1" src="\2">', text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    return text


def _table_row(line):
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _is_table_sep(line):
    return bool(re.match(r"^\s*\|?\s*:?-{2,}", line)) and "|" in line


def markdown_to_html(md_text, title=None):
    lines = md_text.splitlines()
    out = []
    i = 0
    paragraph = []

    def flush_paragraph():
        if paragraph:
            out.append("<p>" + _inline(" ".join(paragraph)) + "</p>")
            paragraph.clear()

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("```"):
            flush_paragraph()
            lang = stripped[3:].strip()
            i += 1
            code = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            i += 1
            cls = ' class="language-%s"' % html_lib.escape(lang) if lang else ""
            out.append("<pre><code%s>%s</code></pre>" %
                       (cls, html_lib.escape("\n".join(code))))
            continue

        if stripped.lower() in ("<!-- pagebreak -->", "<!-- page break -->", "\\pagebreak"):
            flush_paragraph()
            out.append('<div class="page-break"></div>')
            i += 1
            continue

        if not stripped:
            flush_paragraph()
            i += 1
            continue

        heading = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if heading:
            flush_paragraph()
            level = len(heading.group(1))
            out.append("<h%d>%s</h%d>" % (level, _inline(heading.group(2)), level))
            i += 1
            continue

        if re.match(r"^(\*\s*){3,}$|^(-{3,})\s*$", stripped):
            flush_paragraph()
            out.append("<hr>")
            i += 1
            continue

        if i + 1 < len(lines) and stripped.startswith("|") and _is_table_sep(lines[i + 1]):
            flush_paragraph()
            header = _table_row(stripped)
            i += 2
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(_table_row(lines[i]))
                i += 1
            thead = "".join("<th>%s</th>" % _inline(c) for c in header)
            tbody = "".join(
                "<tr>" + "".join("<td>%s</td>" % _inline(c) for c in row) + "</tr>"
                for row in rows)
            out.append("<table><thead><tr>%s</tr></thead><tbody>%s</tbody></table>" %
                       (thead, tbody))
            continue

        if stripped.startswith("> "):
            flush_paragraph()
            quote = []
            while i < len(lines) and lines[i].strip().startswith("> "):
                quote.append(lines[i].strip()[2:])
                i += 1
            out.append("<blockquote><p>%s</p></blockquote>" %
                       _inline(" ".join(quote)))
            continue

        unordered = re.match(r"^[-*+]\s+(.*)$", stripped)
        ordered = re.match(r"^\d+[.)]\s+(.*)$", stripped)
        if unordered or ordered:
            flush_paragraph()
            tag = "ul" if unordered else "ol"
            items = []
            while i < len(lines):
                current = lines[i].strip()
                match = (re.match(r"^[-*+]\s+(.*)$", current) if tag == "ul"
                         else re.match(r"^\d+[.)]\s+(.*)$", current))
                if not match:
                    break
                items.append("<li>%s</li>" % _inline(match.group(1)))
                i += 1
            out.append("<%s>%s</%s>" % (tag, "".join(items), tag))
            continue

        paragraph.append(stripped)
        i += 1

    flush_paragraph()
    body = "\n".join(out)
    if title:
        body = "<h1 class=\"doc-title\">%s</h1>\n" % _inline(title) + body
    return body


def wrap_document(body, css_text, page_size=None, landscape=False,
                  header_footer=False, extra_head=""):
    size = "A4"
    if page_size:
        size = "%spt %spt" % (page_size[0], page_size[1])
    orientation = " landscape" if landscape else ""
    header_note = "" if header_footer else "--no-pdf-header-footer is passed to the browser"
    return ("<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
            "<title>PDF Workshop</title>"
            "<style>@page { size: %s%s; margin: 0 }%s</style>"
            "<style>%s</style>%s</head><body>%s</body></html>" %
            (size, orientation, "/* %s */" % header_note if header_note else "",
             css_text, extra_head, body))


def html_to_pdf(html_text, out_path, browser=None, page_size=None,
                landscape=False, header_footer=False, workdir=None):
    browser = browser or find_browser()
    if not browser:
        raise RuntimeError(
            "未找到 Edge / Chrome。请安装浏览器，或用 PDF_BROWSER 指定可执行文件路径。")
    out_path = Path(out_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    temp_root = Path(workdir) if workdir else Path(tempfile.mkdtemp(prefix="pdf-workshop-"))
    temp_root.mkdir(parents=True, exist_ok=True)
    html_path = temp_root / "source.html"
    html_path.write_text(html_text, encoding="utf-8")
    profile = temp_root / "browser-profile"
    cmd = [
        browser, "--headless", "--disable-gpu", "--no-sandbox",
        "--no-first-run", "--no-default-browser-check",
        "--disable-extensions", "--allow-file-access-from-files",
        "--user-data-dir=" + str(profile),
        "--virtual-time-budget=8000",
        "--print-to-pdf=" + str(out_path),
    ]
    if not header_footer:
        cmd.append("--no-pdf-header-footer")
    cmd.append(html_path.resolve().as_uri())
    proc = subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=180)
    if not out_path.exists() or out_path.stat().st_size == 0:
        raise RuntimeError("浏览器未能生成 PDF。stderr: %s" %
                           (proc.stderr or "")[-1200:])
    return {"pdf": str(out_path), "html": str(html_path),
            "bytes": out_path.stat().st_size}


def build_pdf(source, out_path, title=None, css_path=None, as_html=False,
              page_size=None, landscape=False, header_footer=False, workdir=None):
    text = Path(source).read_text(encoding="utf-8")
    css_text = Path(css_path).read_text(encoding="utf-8") if css_path else (
        DEFAULT_CSS.read_text(encoding="utf-8") if DEFAULT_CSS.exists() else "")
    if as_html:
        if "<html" in text.lower():
            document = text.replace("</head>", "<style>%s</style></head>" % css_text, 1) \
                if css_text else text
        else:
            document = wrap_document(text, css_text, page_size, landscape,
                                     header_footer)
    else:
        body = markdown_to_html(text, title)
        document = wrap_document(body, css_text, page_size, landscape,
                                 header_footer)
    return html_to_pdf(document, out_path, page_size=page_size,
                       landscape=landscape, header_footer=header_footer,
                       workdir=workdir)


def main():
    p = argparse.ArgumentParser(description="Markdown / HTML to PDF")
    p.add_argument("source")
    p.add_argument("-o", "--output", required=True)
    p.add_argument("--title")
    p.add_argument("--css")
    p.add_argument("--html", action="store_true", help="treat source as HTML")
    p.add_argument("--landscape", action="store_true")
    p.add_argument("--header-footer", action="store_true")
    p.add_argument("--page-size", help="custom page size in points, e.g. 595x842")
    p.add_argument("--workdir")
    ns = p.parse_args()
    page_size = None
    if ns.page_size:
        try:
            page_size = tuple(float(x) for x in ns.page_size.lower().split("x"))
        except ValueError:
            p.error("--page-size must look like 595x842")
    try:
        result = build_pdf(ns.source, ns.output, title=ns.title, css_path=ns.css,
                           as_html=ns.html, page_size=page_size,
                           landscape=ns.landscape, header_footer=ns.header_footer,
                           workdir=ns.workdir)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)},
                         ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
