#!/usr/bin/env python3
"""Shrink a PDF without touching its text layer.

Two independent levers, applied in this order:

  structure  garbage collection + stream deflate + content clean-up. Always
             lossless, usually 3-25% on documents exported by office suites.
  images     re-encode embedded bitmaps to JPEG and cap their long edge. This
             is what actually moves the needle on scanned files, and it is
             lossy — say so in the report instead of pretending otherwise.

Transparency masks (SMask) are skipped: flattening them would change how the
page looks. Files that do not get smaller are still written, with a warning,
so the caller can decide instead of guessing why nothing happened.
"""

import argparse
import json
import sys
from pathlib import Path


def load_pymupdf():
    try:
        import pymupdf  # PyMuPDF >= 1.24
        return pymupdf
    except ImportError:
        try:
            import fitz as pymupdf
            return pymupdf
        except ImportError:
            raise SystemExit(
                "缺少 PyMuPDF，无法压缩：python scripts/bootstrap.py install --pdf"
                "（或 python -m pip install pymupdf）")


LEVELS = {
    "light": {"max_side": 2000, "quality": 82},
    "balanced": {"max_side": 1400, "quality": 72},
    "strong": {"max_side": 1000, "quality": 60},
}


def human(size):
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return "%.1f %s" % (size, unit) if unit != "B" else "%d B" % size
        size /= 1024.0


def downsample_images(doc, max_side, quality):
    """Re-encode oversized bitmaps in place. Returns (changed, skipped)."""
    pymupdf = load_pymupdf()
    changed = skipped = 0
    seen = set()
    for page in doc:
        try:
            images = page.get_images(full=True)
        except Exception:  # noqa: BLE001 - broken page resources
            continue
        for item in images:
            xref = item[0]
            if xref in seen:
                continue
            seen.add(xref)
            try:
                smask = doc.xref_get_key(xref, "SMask")[1]
                if smask not in ("null", ""):
                    skipped += 1
                    continue
                pix = pymupdf.Pixmap(doc, xref)
                if pix.width <= 1 or pix.height <= 1:
                    skipped += 1
                    continue
                if max(pix.width, pix.height) <= max_side:
                    skipped += 1
                    continue
                if pix.colorspace and pix.colorspace.n not in (1, 3):
                    pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
                scale = float(max_side) / max(pix.width, pix.height)
                width = max(1, int(round(pix.width * scale)))
                height = max(1, int(round(pix.height * scale)))
                small = pymupdf.Pixmap(pix, width, height, None)
                data = small.tobytes("jpeg", jpg_quality=int(quality))
                doc.update_stream(xref, data, compress=False)
                doc.xref_set_key(xref, "Width", str(width))
                doc.xref_set_key(xref, "Height", str(height))
                doc.xref_set_key(xref, "Filter", "/DCTDecode")
                doc.xref_set_key(xref, "ColorSpace", "/DeviceRGB")
                doc.xref_set_key(xref, "BitsPerComponent", "8")
                changed += 1
            except Exception:  # noqa: BLE001 - keep the original bitmap
                skipped += 1
    return changed, skipped


def main():
    p = argparse.ArgumentParser(description="Compress a PDF (structure + images)")
    p.add_argument("input")
    p.add_argument("-o", "--output", required=True)
    p.add_argument("-p", "--password")
    p.add_argument("--level", default="balanced",
                   choices=sorted(LEVELS), help="image preset, default balanced")
    p.add_argument("--max-side", type=int,
                   help="override the preset long edge in pixels (0 = keep size)")
    p.add_argument("--quality", type=int, help="override the preset JPEG quality")
    p.add_argument("--no-images", action="store_true",
                   help="structural compression only (fully lossless)")
    p.add_argument("--dry-run", action="store_true")
    ns = p.parse_args()

    source = Path(ns.input).resolve()
    target = Path(ns.output).resolve()
    if not source.is_file():
        raise SystemExit("输入不存在：%s" % source)
    if source == target:
        raise SystemExit("输出不能覆盖输入：%s" % target)

    preset = LEVELS[ns.level]
    max_side = ns.max_side if ns.max_side is not None else preset["max_side"]
    quality = ns.quality if ns.quality is not None else preset["quality"]

    pymupdf = load_pymupdf()
    doc = pymupdf.open(str(source))
    if doc.needs_pass and not (ns.password and doc.authenticate(ns.password)):
        raise SystemExit("PDF 已加密，需要正确的 --password")

    original = source.stat().st_size
    images, skipped = (0, 0)
    if not ns.no_images and max_side > 0:
        images, skipped = downsample_images(doc, max_side, quality)

    if ns.dry_run:
        doc.close()
        print(json.dumps({"input": str(source), "bytes": original,
                          "level": ns.level, "max_side": max_side,
                          "quality": quality, "images_would_touch": images,
                          "dry_run": True}, ensure_ascii=False))
        return 0

    target.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(target), garbage=4, deflate=True, clean=True)
    pages = doc.page_count
    doc.close()

    result = target.stat().st_size
    ratio = 0.0 if original == 0 else (1 - result / float(original)) * 100
    warnings = []
    if result >= original:
        warnings.append("压缩后未变小（原文件已优化或图片占比很低）；"
                        "可换 --level strong 或加 --max-side")
    if result == 0:
        warnings.append("输出为 0 字节，请检查输入文件是否完整")
    print(json.dumps({"output": str(target), "pages": pages,
                      "original_bytes": original, "output_bytes": result,
                      "original_human": human(original),
                      "output_human": human(result),
                      "saved_percent": round(ratio, 1),
                      "level": ns.level, "max_side": max_side,
                      "quality": quality, "images_reencoded": images,
                      "images_skipped": skipped,
                      "lossless": bool(ns.no_images or images == 0),
                      "warnings": warnings}, ensure_ascii=False))
    return 0 if result > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
