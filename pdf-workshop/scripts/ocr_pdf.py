#!/usr/bin/env python3
"""Turn scanned PDFs into searchable Markdown text and (when possible) tables.

Three independent paths are combined, in order of preference:
  1. The official workbuddy-pdf CLI with -f md-plain / table, which auto-detects
     scans and preserves layout and tables when an OCR engine (Tesseract or
     PaddleOCR) is installed on PATH.
  2. A Tesseract fallback that renders every page to PNG and produces per-page
     text with explicit page markers.
  3. A RapidOCR (onnxruntime) fallback that needs no external binary at all and
     rebuilds rows / columns from the recognised text boxes.

A real text-layer PDF (with baked-in text) is not produced here; the OCR
output is Markdown / per-page text meant for downstream search and extraction.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wb_pdf  # noqa: E402


def tesseract_binary():
    override = os.environ.get("TESSERACT") or os.environ.get("PDF2DOCX_TESSERACT")
    if override and Path(override).exists():
        return str(Path(override).resolve())
    return shutil.which("tesseract")


def available_languages(binary):
    try:
        proc = subprocess.run([binary, "--list-langs"], capture_output=True,
                              text=True, encoding="utf-8", errors="replace")
        return [line.strip() for line in proc.stdout.splitlines()[1:] if line.strip()]
    except OSError:
        return []


def render_pages(source, outdir, dpi):
    pages_dir = Path(outdir) / "pages-png"
    code = wb_pdf.run_action(["render", source, "-o", str(pages_dir),
                              "-f", "png", "--dpi", str(dpi)])
    if code != 0:
        return []
    return sorted(pages_dir.glob("*.png"), key=lambda p: _page_number(p.name))


def _page_number(name):
    match = re.search(r"(\d+)", name)
    return int(match.group(1)) if match else 0


# ---------------------------------------------------------------- RapidOCR ----

def rapidocr_engine():
    """Return a RapidOCR instance, or None when the package is unusable."""
    try:
        from rapidocr_onnxruntime import RapidOCR
    except Exception:
        return None
    try:
        return RapidOCR()
    except Exception:
        return None


def _blocks_from_result(result):
    blocks = []
    for box, text, score in result or []:
        text = (text or "").strip()
        if not text:
            continue
        xs = [point[0] for point in box]
        ys = [point[1] for point in box]
        blocks.append({"left": float(min(xs)), "right": float(max(xs)),
                       "top": float(min(ys)), "bottom": float(max(ys)),
                       "text": text, "score": float(score)})
    return blocks


def cluster_rows(blocks, tol_ratio=0.6):
    """Group text blocks into visual rows, left-to-right inside each row."""
    if not blocks:
        return []
    ordered = sorted(blocks, key=lambda b: (b["top"], b["left"]))
    heights = [max(1.0, b["bottom"] - b["top"]) for b in ordered]
    tol = max(8.0, (sum(heights) / len(heights)) * tol_ratio)
    rows, current = [], [ordered[0]]
    for block in ordered[1:]:
        anchor = sum(x["top"] for x in current) / len(current)
        if abs(block["top"] - anchor) <= tol:
            current.append(block)
        else:
            rows.append(current)
            current = [block]
    rows.append(current)
    for row in rows:
        row.sort(key=lambda b: b["left"])
    return rows


def rows_to_markdown(rows):
    """Render rows as lines, upgrading aligned multi-cell runs into tables."""
    parts, index = [], 0
    while index < len(rows):
        if len(rows[index]) >= 3:
            end = index
            while end < len(rows) and len(rows[end]) >= 3:
                end += 1
            if end - index >= 2:  # a header row plus at least one body row
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


def ocr_with_rapidocr(images, text_dir, outdir):
    engine = rapidocr_engine()
    if engine is None:
        return None
    chunks, scores, page_rows = [], [], {}
    for index, image in enumerate(images, start=1):
        result, _ = engine(str(image))
        blocks = _blocks_from_result(result)
        rows = cluster_rows(blocks)
        body = rows_to_markdown(rows)
        (text_dir / ("page-%04d.txt" % index)).write_text(body, encoding="utf-8")
        chunks.append("<!-- page %d -->\n\n%s" % (index, body))
        scores.extend(block["score"] for block in blocks)
        page_rows[index] = len(rows)
    ocr_md = Path(outdir) / "ocr.md"
    ocr_md.write_text("\n\n".join(chunks), encoding="utf-8")
    return {"file": str(ocr_md), "pages": len(images),
            "mean_confidence": round(sum(scores) / len(scores), 4) if scores else 0.0,
            "rows": page_rows}


def main():
    p = argparse.ArgumentParser(description="OCR scanned PDFs into text / tables")
    p.add_argument("input")
    p.add_argument("-o", "--output", required=True, help="output directory")
    p.add_argument("--lang", default="chi_sim+eng")
    p.add_argument("--dpi", type=int, default=200)
    p.add_argument("--tables", action="store_true",
                   help="also run the CLI table recogniser")
    p.add_argument("--password")
    ns = p.parse_args()

    outdir = Path(ns.output).resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    manifest = {"input": str(Path(ns.input).resolve()), "files": [],
                "engines": [], "warnings": []}

    layout_md = outdir / "layout.md"
    read_args = ["read", ns.input, "-o", str(layout_md), "-f", "md-plain"]
    if ns.password:
        read_args += ["-p", ns.password]
    if wb_pdf.run_action(read_args) == 0 and layout_md.exists():
        manifest["files"].append(str(layout_md))
        manifest["engines"].append("workbuddy-pdf/md-plain")
    else:
        manifest["warnings"].append(
            "CLI 版面识别失败（缺少 Tesseract / PaddleOCR 或组件未就绪），已转向本地引擎兜底。")

    if ns.tables:
        tables_dir = outdir / "tables"
        if wb_pdf.run_action(["read", ns.input, "-o", str(tables_dir),
                              "-f", "table", "--table-format", "csv"]) == 0:
            files = sorted(str(x) for x in tables_dir.glob("*") if x.is_file())
            manifest["files"].extend(files)
            if files:
                manifest["engines"].append("workbuddy-pdf/table")
        else:
            manifest["warnings"].append("表格识别失败，扫描表格的行列与合并跨度只能近似还原。")

    text_dir = outdir / "pages"
    text_dir.mkdir(exist_ok=True)
    images = [] if manifest["engines"] else render_pages(ns.input, outdir, ns.dpi)

    binary = tesseract_binary()
    if binary:
        languages = available_languages(binary)
        requested = ns.lang.split("+")
        usable = [x for x in requested if x in languages]
        if not usable:
            usable = ["eng"] if "eng" in languages else []
            manifest["warnings"].append(
                "缺少语言包 %s，已降级为 %s" % (ns.lang, "+".join(usable) or "无"))
        if usable and not manifest["engines"]:
            images = images or render_pages(ns.input, outdir, ns.dpi)
            if not images:
                manifest["warnings"].append("页面渲染失败，Tesseract 路径未产出结果。")
            else:
                chunks = []
                for index, image in enumerate(images, start=1):
                    proc = subprocess.run(
                        [binary, str(image), "stdout", "-l", "+".join(usable),
                         "--psm", "3"],
                        capture_output=True, text=True, encoding="utf-8",
                        errors="replace")
                    text = (proc.stdout or "").strip()
                    (text_dir / ("page-%04d.txt" % index)).write_text(
                        text, encoding="utf-8")
                    chunks.append("<!-- page %d -->\n\n%s" % (index, text))
                ocr_md = outdir / "ocr.md"
                ocr_md.write_text("\n\n".join(chunks), encoding="utf-8")
                manifest["files"].append(str(ocr_md))
                manifest["files"].append(str(text_dir))
                manifest["engines"].append("tesseract/%s" % "+".join(usable))
                manifest["pages"] = len(images)
                manifest["languages"] = usable
    else:
        manifest["warnings"].append(
            "未找到 Tesseract。中文 OCR 需安装 Tesseract（含 chi_sim 语言包）或 PaddleOCR。")

    if not manifest["engines"]:
        images = images or render_pages(ns.input, outdir, ns.dpi)
        if not images:
            manifest["warnings"].append("页面渲染失败，RapidOCR 路径未产出结果。")
        else:
            rapid = ocr_with_rapidocr(images, text_dir, outdir)
            if rapid is None:
                manifest["warnings"].append(
                    "未找到 RapidOCR（pip install rapidocr-onnxruntime），三条通道均不可用。")
            else:
                manifest["files"].append(rapid["file"])
                manifest["files"].append(str(text_dir))
                manifest["engines"].append("rapidocr/onnxruntime")
                manifest["pages"] = rapid["pages"]
                manifest["mean_confidence"] = rapid["mean_confidence"]
                manifest["rows_per_page"] = rapid["rows"]

    manifest["status"] = "ok" if manifest["engines"] else "no_engine"
    (outdir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0 if manifest["status"] == "ok" else 2


if __name__ == "__main__":
    sys.exit(main())
