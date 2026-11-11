#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OCR images and PDFs into Markdown / text / structured JSON.

Usage:
  python scripts/ocr_cli.py <input> -o <outdir> [options]

  <input> may be an image, a PDF, or a directory (batch).
  Every run writes <stem>.md, <stem>.json and manifest.json into <outdir>;
  PDF runs also write pages/page-NNNN.txt and (with --table) tables/*.csv.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ocr_core  # noqa: E402


def process_image(image_path, outdir, ns, label=None):
    blocks, backend = ocr_core.recognize(image_path, ns.engine, ns.min_score)
    rows = ocr_core.cluster_rows(blocks)
    markdown = ocr_core.rows_to_markdown(rows)
    page = {"page": label or 1, "image": str(image_path),
            "text": markdown, "mean_score": ocr_core.mean_score(blocks),
            "blocks": blocks}
    return page, backend


def process_pdf(pdf_path, outdir, ns):
    png_dir = outdir / "pages-png"
    rendered = ocr_core.render_pdf(pdf_path, png_dir, dpi=ns.dpi,
                                   pages=ns.pages, password=ns.password)
    if not rendered:
        raise SystemExit("PDF 没有可识别的页面（检查 --pages 取值）。")
    text_dir = outdir / "pages"
    text_dir.mkdir(parents=True, exist_ok=True)
    table_dir = outdir / "tables"
    pages, backend = [], None
    for page_no, png in rendered:
        blocks, backend = ocr_core.recognize(png, ns.engine, ns.min_score)
        rows = ocr_core.cluster_rows(blocks)
        body = ocr_core.rows_to_markdown(rows)
        (text_dir / ("page-%04d.txt" % page_no)).write_text(body, encoding="utf-8")
        if ns.table:
            csv_text = ocr_core.rows_to_csv(rows)
            if csv_text:
                table_dir.mkdir(parents=True, exist_ok=True)
                (table_dir / ("page-%04d.csv" % page_no)).write_text(
                    csv_text, encoding="utf-8-sig")
        pages.append({"page": page_no, "image": str(png), "text": body,
                      "mean_score": ocr_core.mean_score(blocks),
                      "blocks": blocks})
    return pages, backend


def write_outputs(outdir, stem, pages, source, backend, ns, with_markers):
    outdir.mkdir(parents=True, exist_ok=True)
    markdown = "\n\n".join(
        ("<!-- page %s -->\n\n%s" % (p["page"], p["text"])) if with_markers
        else p["text"] for p in pages)
    md_path = outdir / ("%s.md" % stem)
    md_path.write_text(markdown + "\n", encoding="utf-8")

    payload = {"source": str(source), "engine": backend, "dpi": ns.dpi,
               "page_count": len(pages),
               "mean_score": ocr_core.mean_score(
                   [b for p in pages for b in p["blocks"]]),
               "pages": pages}
    json_path = outdir / ("%s.json" % stem)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                         encoding="utf-8")
    return md_path, json_path, payload


def run_one(source, outdir, ns):
    source = Path(source)
    stem = ocr_core.slug(source)
    is_pdf = source.suffix.lower() in ocr_core.PDF_SUFFIXES
    if is_pdf:
        pages, backend = process_pdf(source, outdir, ns)
    else:
        page, backend = process_image(source, outdir, ns)
        pages = [page]
    md_path, json_path, payload = write_outputs(
        outdir, stem, pages, source, backend, ns, with_markers=is_pdf)
    entry = {"source": str(source), "engine": backend,
             "pages": payload["page_count"], "md": str(md_path),
             "json": str(json_path)}
    if payload["mean_score"] is not None:
        entry["mean_score"] = payload["mean_score"]
    return entry


def main():
    p = argparse.ArgumentParser(
        description="OCR images / PDFs into Markdown, text and structured JSON")
    p.add_argument("input", help="image, PDF, or directory (batch)")
    p.add_argument("-o", "--output", required=True, help="output directory")
    p.add_argument("--mode", default="auto",
                   choices=("auto", "image", "pdf", "batch", "table"),
                   help="auto detects from the input path")
    p.add_argument("--engine", default="auto", choices=("auto", "rapidocr", "tesseract"))
    p.add_argument("--dpi", type=int, default=200, help="PDF render DPI")
    p.add_argument("--min-score", type=float, default=0.0,
                   help="drop blocks below this confidence (0-1)")
    p.add_argument("--pages", help="1-based page spec for PDFs, e.g. 3-5,7")
    p.add_argument("--password", help="password for encrypted PDFs")
    p.add_argument("--table", action="store_true",
                   help="also write per-page table CSV when a grid is detected")
    p.add_argument("--dry-run", action="store_true")
    ns = p.parse_args()

    outdir = Path(ns.output).resolve()
    mode = ns.mode
    requested = ns.mode
    if mode == "table":
        ns.table = True
        mode = "auto"
    status = ocr_core.engine_status()
    if ns.dry_run:
        print(json.dumps({"input": str(Path(ns.input).resolve()),
                          "engines": status, "mode": mode},
                         ensure_ascii=False, indent=2))
        return 0

    targets = ocr_core.iter_inputs(ns.input)
    if not targets:
        raise SystemExit("没有找到可识别的图片或 PDF：%s" % ns.input)
    batch = mode == "batch" or len(targets) > 1

    manifest = {"input": str(Path(ns.input).resolve()),
                "mode": "table" if requested == "table" else (
                    "batch" if batch else (
                        "pdf" if targets[0].suffix.lower() in ocr_core.PDF_SUFFIXES
                        else "image")),
                "items": [], "warnings": [], "engines": status["usable"]}
    if not status["usable"]:
        raise SystemExit("未找到 OCR 引擎。装 RapidOCR：python scripts/bootstrap.py install --ocr")

    for target in targets:
        target_out = outdir / ocr_core.slug(target) if batch else outdir
        entry = run_one(target, target_out, ns)
        entry["output_dir"] = str(target_out)
        manifest["items"].append(entry)
        print("%s -> %s (%s, %s page(s)%s)" % (
            target.name, entry["output_dir"], entry["engine"], entry["pages"],
            ", mean %.4f" % entry["mean_score"] if "mean_score" in entry else ""))

    total_pages = sum(item["pages"] for item in manifest["items"])
    manifest["files"] = len(manifest["items"])
    manifest["pages"] = total_pages
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print("manifest: %s" % (outdir / "manifest.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
