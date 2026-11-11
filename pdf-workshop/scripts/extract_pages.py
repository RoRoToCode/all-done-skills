#!/usr/bin/env python3
"""Extract a page range from a PDF into a new file, with content verification.

This is the positive counterpart of `pdf_ops.py delete`: instead of removing
pages, keep only the requested ones, in the order requested.

Usage:
  python extract_pages.py report.pdf -o excerpt.pdf --pages 3-5
  python extract_pages.py report.pdf -o excerpt.pdf --pages 1,3-5,8
"""

import argparse
import json
import sys
from pathlib import Path

from pypdf import PdfReader, PdfWriter


def parse_pages(spec, total):
    """Turn '1,3-5' into [1, 3, 4, 5] (1-based), rejecting out-of-range pages."""
    if not spec or not spec.strip():
        raise ValueError("--pages is empty")
    result = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            left, right = part.split("-", 1)
            start = int(left) if left.strip() else 1
            end = int(right) if right.strip() else total
            if start > end:
                raise ValueError("descending range is not supported: %s" % part)
            result.extend(range(start, end + 1))
        else:
            result.append(int(part))
    if not result:
        raise ValueError("--pages contains no page numbers")
    for n in result:
        if n < 1 or n > total:
            raise ValueError("page %d is out of range (document has %d pages)"
                             % (n, total))
    return result


def box_size(page):
    box = page.mediabox
    return (round(float(box.width), 3), round(float(box.height), 3))


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("input")
    p.add_argument("-o", "--output", required=True)
    p.add_argument("--pages", required=True,
                   help="1-based page numbers, e.g. 3-5 or 1,3-5,8")
    ns = p.parse_args()

    src, out = Path(ns.input).resolve(), Path(ns.output).resolve()
    if not src.is_file():
        print(json.dumps({"status": "error", "message": "input not found: %s" % src},
                         ensure_ascii=False))
        return 2
    if src == out:
        print(json.dumps({"status": "error", "message": "output must not overwrite input"},
                         ensure_ascii=False))
        return 2
    out.parent.mkdir(parents=True, exist_ok=True)

    reader = PdfReader(str(src))
    if reader.is_encrypted:
        print(json.dumps({"status": "error",
                          "message": "input is encrypted; decrypt it first with the pdf-decrypt action"},
                         ensure_ascii=False))
        return 2
    total = len(reader.pages)
    try:
        requested = parse_pages(ns.pages, total)
    except (ValueError, TypeError) as exc:
        print(json.dumps({"status": "error", "message": str(exc),
                          "source_pages": total}, ensure_ascii=False))
        return 2

    writer = PdfWriter()
    for n in requested:
        writer.add_page(reader.pages[n - 1])
    with out.open("wb") as fh:
        writer.write(fh)

    check = PdfReader(str(out))
    problems = []
    if len(check.pages) != len(requested):
        problems.append("page count %d != requested %d"
                        % (len(check.pages), len(requested)))
    else:
        for i, n in enumerate(requested):
            a, b = reader.pages[n - 1], check.pages[i]
            if (a.extract_text() or "") != (b.extract_text() or ""):
                problems.append("text differs on source page %d" % n)
            if box_size(a) != box_size(b):
                problems.append("page size differs on source page %d" % n)
    if problems:
        out.unlink(missing_ok=True)
        print(json.dumps({"status": "error", "message": "verification failed; output discarded",
                          "problems": problems}, ensure_ascii=False))
        return 3

    result = {
        "status": "ok",
        "input": str(src), "output": str(out),
        "file_bytes": out.stat().st_size,
        "source_pages": total,
        "requested_pages": requested,
        "extracted_pages": len(check.pages),
        "page_sizes_match": True,
        "text_unchanged": True,
        "source_size_bytes": src.stat().st_size,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
