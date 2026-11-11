# -*- coding: utf-8 -*-
"""Shared OCR primitives: engine selection, page rendering, layout rebuilding.

Deliberately free of argparse so the same helpers can be reused by other
skills. Two engines are supported:

  rapidocr  rapidocr_onnxruntime — pure Python, models ship inside the wheel,
            no external binary, best Chinese quality. Preferred.
  tesseract  external binary plus language packs; used when it is the only
            engine present. Returns text only (no boxes), so JSON output from
            this backend has no coordinates.

Everything else (layout, tables, page markers) is built from the recognised
text boxes, not from the engine.
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}
PDF_SUFFIXES = {".pdf"}

_ENGINE_CACHE = {}


# ------------------------------------------------------------------ engines --

def tesseract_binary():
    override = os.environ.get("TESSERACT") or os.environ.get("PDF2DOCX_TESSERACT")
    if override and Path(override).exists():
        return str(Path(override).resolve())
    return shutil.which("tesseract")


def tesseract_languages(binary=None):
    binary = binary or tesseract_binary()
    if not binary:
        return []
    try:
        proc = subprocess.run([binary, "--list-langs"], capture_output=True,
                              text=True, encoding="utf-8", errors="replace")
    except OSError:
        return []
    return [line.strip() for line in proc.stdout.splitlines()[1:] if line.strip()]


def engine_status():
    status = {"rapidocr": {"available": False, "detail": ""},
              "tesseract": {"available": False, "detail": ""}}
    try:
        import rapidocr_onnxruntime  # noqa: F401
        status["rapidocr"] = {"available": True,
                              "detail": getattr(rapidocr_onnxruntime,
                                                "__version__", "installed")}
    except Exception as exc:  # noqa: BLE001 - report any import failure
        status["rapidocr"]["detail"] = str(exc)[:120]
    binary = tesseract_binary()
    if binary:
        langs = tesseract_languages(binary)
        status["tesseract"] = {"available": True, "binary": binary,
                               "languages": langs,
                               "chinese": "chi_sim" in langs}
    else:
        status["tesseract"]["detail"] = "binary not found on PATH"
    usable = [name for name, item in status.items() if item["available"]]
    status["usable"] = usable
    status["preferred"] = usable[0] if usable else None
    return status


def _rapidocr():
    if "rapidocr" not in _ENGINE_CACHE:
        from rapidocr_onnxruntime import RapidOCR
        _ENGINE_CACHE["rapidocr"] = RapidOCR()
    return _ENGINE_CACHE["rapidocr"]


def resolve_engine(requested="auto"):
    """Return the backend name to use, or raise SystemExit with a hint."""
    status = engine_status()
    if requested and requested != "auto":
        if requested not in status["usable"]:
            raise SystemExit(
                "engine %r is not available（可用：%s）。装引擎：python scripts/bootstrap.py install --ocr"
                % (requested, ", ".join(status["usable"]) or "无"))
        return requested
    if not status["usable"]:
        raise SystemExit(
            "未找到 OCR 引擎。装 RapidOCR：python scripts/bootstrap.py install --ocr\n"
            "或装 Tesseract（含 chi_sim 语言包）后重试。")
    return status["preferred"]


def recognize(image_path, engine="auto", min_score=0.0):
    """Recognise one image file. Returns (blocks, backend_name)."""
    backend = resolve_engine(engine)
    if backend == "rapidocr":
        result, _ = _rapidocr()(str(image_path))
        blocks = []
        for box, text, score in result or []:
            text = (text or "").strip()
            if not text or float(score) < min_score:
                continue
            xs = [float(point[0]) for point in box]
            ys = [float(point[1]) for point in box]
            blocks.append({"text": text, "score": round(float(score), 4),
                           "box": [min(xs), min(ys), max(xs), max(ys)]})
        return blocks, backend

    binary = tesseract_binary()
    lang = os.environ.get("OCR_LANG", "chi_sim+eng")
    languages = tesseract_languages(binary)
    usable = [code for code in lang.split("+") if code in languages] or \
        (["eng"] if "eng" in languages else [])
    if not usable:
        raise SystemExit("Tesseract 缺少可用语言包（需要 chi_sim 或 eng）。")
    proc = subprocess.run([binary, str(image_path), "stdout",
                           "-l", "+".join(usable), "--psm", "3"],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace")
    text = (proc.stdout or "").strip()
    blocks = [{"text": line.strip(), "score": None, "box": None}
              for line in text.splitlines() if line.strip()]
    return blocks, "tesseract"


# ------------------------------------------------------------------- inputs --

def iter_inputs(target, recursive=True):
    """Expand a file or directory into an ordered list of image / PDF paths."""
    path = Path(target)
    if path.is_file():
        return [path]
    if not path.is_dir():
        raise SystemExit("输入不存在：%s" % path)
    pattern = "**/*" if recursive else "*"
    files = [p for p in path.glob(pattern)
             if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES | PDF_SUFFIXES]
    return sorted(files)


def parse_pages(spec):
    """Parse a 1-based page spec such as '3-5,7' into a set of ints."""
    if not spec:
        return None
    wanted = set()
    for chunk in str(spec).split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" in chunk:
            start, end = chunk.split("-", 1)
            wanted.update(range(int(start), int(end) + 1))
        else:
            wanted.add(int(chunk))
    return wanted


def render_pdf(pdf_path, out_png_dir, dpi=200, pages=None, password=None):
    """Render PDF pages to PNG. Returns [(page_no, png_path)]."""
    try:
        import pymupdf
    except ImportError:  # older PyMuPDF exposes the same API as `fitz`
        try:
            import fitz as pymupdf
        except ImportError:
            raise SystemExit(
                "缺少 PyMuPDF，无法渲染 PDF 页面：\n"
                "  python scripts/bootstrap.py install --pdf")
    out_png_dir = Path(out_png_dir)
    out_png_dir.mkdir(parents=True, exist_ok=True)
    wanted = parse_pages(pages)
    doc = pymupdf.open(str(pdf_path))
    if doc.needs_pass:
        if not password or not doc.authenticate(password):
            raise SystemExit("PDF 已加密，需要正确的 --password。")
    rendered = []
    for index, page in enumerate(doc, start=1):
        if wanted is not None and index not in wanted:
            continue
        png = out_png_dir / ("page-%04d.png" % index)
        page.get_pixmap(dpi=dpi).save(str(png))
        rendered.append((index, png))
    doc.close()
    return rendered


# ------------------------------------------------------------------- layout --

def cluster_rows(blocks, tol_ratio=0.6):
    """Group blocks into visual rows by vertical overlap, left-to-right inside."""
    located = [b for b in blocks if b.get("box")]
    if not located:
        return [[b] for b in blocks]
    ordered = sorted(located, key=lambda b: (b["box"][1], b["box"][0]))
    heights = [max(1.0, b["box"][3] - b["box"][1]) for b in ordered]
    tol = max(8.0, (sum(heights) / len(heights)) * tol_ratio)
    rows, current = [], [ordered[0]]
    for block in ordered[1:]:
        anchor = sum(x["box"][1] for x in current) / len(current)
        if abs(block["box"][1] - anchor) <= tol:
            current.append(block)
        else:
            rows.append(current)
            current = [block]
    rows.append(current)
    for row in rows:
        row.sort(key=lambda b: b["box"][0])
    return rows


def rows_to_markdown(rows, table_min_cols=3, table_min_rows=2):
    """Plain lines, with aligned multi-cell runs promoted to Markdown tables."""
    parts, index = [], 0
    while index < len(rows):
        if len(rows[index]) >= table_min_cols:
            end = index
            while end < len(rows) and len(rows[end]) >= table_min_cols:
                end += 1
            if end - index >= table_min_rows:
                run = rows[index:end]
                width = max(len(row) for row in run)
                grid = [[cell["text"] for cell in row] + [""] * (width - len(row))
                        for row in run]
                lines = ["| " + " | ".join(grid[0]) + " |",
                         "| " + " | ".join(["---"] * width) + " |"]
                lines += ["| " + " | ".join(row) + " |" for row in grid[1:]]
                parts.append("\n".join(lines))
                index = end
                continue
        parts.append(" ".join(cell["text"] for cell in rows[index]))
        index += 1
    return "\n".join(parts)


def rows_to_csv(rows, min_cols=2):
    """Serialise multi-cell rows as CSV; returns '' when no table is found."""
    import csv
    import io
    table = [row for row in rows if len(row) >= min_cols]
    if len(table) < 2:
        return ""
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    for row in table:
        writer.writerow([cell["text"] for cell in row])
    return buf.getvalue()


def mean_score(blocks):
    scores = [b["score"] for b in blocks if isinstance(b.get("score"), float)]
    return round(sum(scores) / len(scores), 4) if scores else None


def slug(path):
    """Filesystem-safe stem for output directory names."""
    stem = Path(path).stem or "output"
    return re.sub(r"[^\w.\-]+", "-", stem).strip("-") or "output"
