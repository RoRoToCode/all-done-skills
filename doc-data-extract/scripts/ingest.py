#!/usr/bin/env python3
"""Shared multi-format document ingestion for doc-data-extract.

extract(path) -> {"text": str, "pages": [{"page": int, "text": str}],
                   "warnings": [str], "format": str}

Ingestion order per format:
  PDF      -> host workbuddy-pdf CLI (pdf_cli) then pypdf fallback
  DOCX     -> python-docx
  XLSX     -> openpyxl (one pseudo-page per sheet)
  PPTX     -> python-pptx (one pseudo-page per slide)
  HTML     -> bs4
  TXT/MD/CSV/JSON -> plain read

All heavy imports are lazy so a missing library only degrades that format
instead of breaking the whole module.
"""

import importlib.util
import json
import os
import re
import sys
from pathlib import Path

PAGE_MARK = re.compile(r"<!--\s*page\s+(\d+)\s*-->", re.IGNORECASE)


def _pdf_text(path):
    warnings = []
    # Host CLI first (best layout fidelity), mirroring pdf-workshop.
    try:
        here = Path(__file__).resolve().parent
        spec = importlib.util.spec_from_file_location(
            "pdf_cli_local", here / "pdf_cli.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        prefix = mod.command_prefix()
        if prefix:
            import subprocess
            import tempfile
            out = tempfile.mktemp(suffix=".md")
            code = mod.run_action(["read", str(path), "-o", out, "-f", "md"])
            if code == 0 and Path(out).exists():
                text = Path(out).read_text(encoding="utf-8", errors="replace")
                os.remove(out)
                pages, w = _split_pages(text)
                return {"text": text, "pages": pages,
                        "warnings": warnings + w, "format": "pdf"}
    except Exception as exc:  # noqa: BLE001
        warnings.append("host PDF CLI 不可用：%s" % exc)

    # pypdf fallback.
    if importlib.util.find_spec("pypdf") is not None:
        import pypdf
        reader = pypdf.PdfReader(str(path))
        pages = []
        for i, pg in enumerate(reader.pages, 1):
            pages.append({"page": i, "text": pg.extract_text() or ""})
        warnings.append("PDF 走 pypdf 兜底（版式弱于宿主 CLI）")
        return {"text": "\n".join(p["text"] for p in pages), "pages": pages,
                "warnings": warnings, "format": "pdf"}

    warnings.append("缺宿主 PDF CLI 与 pypdf，无法读取 PDF")
    return {"text": "", "pages": [], "warnings": warnings, "format": "pdf"}


def _split_pages(md_text):
    marks = list(PAGE_MARK.finditer(md_text))
    if not marks:
        return [{"page": 1, "text": md_text.strip()}], \
               ["未检测到页码标记，整篇记为第 1 页"]
    pages = []
    for index, mark in enumerate(marks):
        start = mark.end()
        end = marks[index + 1].start() if index + 1 < len(marks) else len(md_text)
        pages.append({"page": int(mark.group(1)),
                      "text": md_text[start:end].strip()})
    return pages, []


def _docx_text(path):
    if importlib.util.find_spec("docx") is None:
        return None
    import docx
    doc = docx.Document(str(path))
    lines = [p.text for p in doc.paragraphs]
    for table in doc.tables:
        for row in table.rows:
            lines.append(" | ".join(c.text for c in row.cells))
    text = "\n".join(lines)
    return {"text": text, "pages": [{"page": 1, "text": text}], "warnings": [],
            "format": "docx"}


def _xlsx_text(path):
    if importlib.util.find_spec("openpyxl") is None:
        return None
    import openpyxl
    wb = openpyxl.load_workbook(str(path), data_only=True, read_only=True)
    pages = []
    for ws in wb.worksheets:
        rows = []
        for r in ws.iter_rows(values_only=True):
            rows.append(" | ".join("" if c is None else str(c) for c in r))
        text = "\n".join(rows)
        pages.append({"page": ws.title, "text": text})
    text = "\n".join(p["text"] for p in pages)
    return {"text": text, "pages": pages, "warnings": [], "format": "xlsx"}


def _pptx_text(path):
    if importlib.util.find_spec("pptx") is None:
        return None
    from pptx import Presentation
    prs = Presentation(str(path))
    pages = []
    for i, slide in enumerate(prs.slides, 1):
        texts = []
        for shape in slide.shapes:
            if shape.has_text_frame:
                texts.append(shape.text_frame.text)
        pages.append({"page": i, "text": "\n".join(texts)})
    text = "\n".join(p["text"] for p in pages)
    return {"text": text, "pages": pages, "warnings": [], "format": "pptx"}


def _html_text(path):
    if importlib.util.find_spec("bs4") is None:
        return None
    from bs4 import BeautifulSoup
    html = Path(path).read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "head", "noscript"]):
        tag.decompose()
    # Keep structure: headings become markdown levels, tables become pipe rows,
    # so downstream doc-structure sees a real outline instead of flat text.
    for heading in soup.find_all(re.compile(r"^h[1-6]$")):
        level = int(heading.name[1])
        heading.replace_with("\n%s %s\n" % ("#" * level,
                                           heading.get_text(" ", strip=True)))
    for table in soup.find_all("table"):
        rows = []
        for tr in table.find_all("tr"):
            cells = [c.get_text(" ", strip=True)
                     for c in tr.find_all(["th", "td"])]
            if cells:
                rows.append(" | ".join(cells))
        table.replace_with("\n%s\n" % "\n".join(rows) if rows else "")
    text = soup.get_text(separator="\n")
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return {"text": text, "pages": [{"page": 1, "text": text}], "warnings": [],
            "format": "html"}


def extract(path):
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _pdf_text(path)
    if suffix in (".docx",):
        res = _docx_text(path)
        if res:
            return res
        return {"text": "", "pages": [],
                "warnings": ["缺 python-docx，无法读取 DOCX"], "format": "docx"}
    if suffix in (".xlsx", ".xlsm"):
        res = _xlsx_text(path)
        if res:
            return res
        return {"text": "", "pages": [],
                "warnings": ["缺 openpyxl，无法读取 XLSX"], "format": "xlsx"}
    if suffix in (".pptx",):
        res = _pptx_text(path)
        if res:
            return res
        return {"text": "", "pages": [],
                "warnings": ["缺 python-pptx，无法读取 PPTX"], "format": "pptx"}
    if suffix in (".html", ".htm"):
        res = _html_text(path)
        if res:
            return res
        return {"text": "", "pages": [],
                "warnings": ["缺 bs4，无法读取 HTML"], "format": "html"}
    # Plain text / markdown / csv / json
    text = path.read_text(encoding="utf-8", errors="replace")
    return {"text": text, "pages": [{"page": 1, "text": text}],
            "warnings": [], "format": suffix.lstrip(".") or "txt"}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python ingest.py <file>", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(extract(sys.argv[1]), ensure_ascii=False, indent=2))
