#!/usr/bin/env python3
"""Extract text from a .pptx file, one section per slide.

Collects the title placeholder, body text frames, and table cells for each
slide, plus speaker notes when present. Install python-pptx via
`python scripts/bootstrap.py install`.
"""

import argparse
import sys
from pathlib import Path

try:
    from pptx import Presentation
except ImportError:
    sys.exit("缺少 python-pptx。请先运行：python scripts/bootstrap.py install")


def shape_text(shape):
    texts = []
    if shape.has_text_frame:
        for para in shape.text_frame.paragraphs:
            line = "".join(run.text for run in para.runs)
            if line.strip():
                texts.append(line)
    if shape.has_table:
        for row in shape.table.rows:
            cells = [c.text for c in row.cells]
            texts.append(" | ".join(cells))
    return texts


def extract(path):
    prs = Presentation(path)
    sections = []
    slide_count = 0
    for i, slide in enumerate(prs.slides, 1):
        slide_count += 1
        lines = ["--- Slide %d ---" % i]
        for shape in slide.shapes:
            for t in shape_text(shape):
                lines.append(t)
        if slide.has_notes_slide:
            notes = slide.notes_slide.notes_text_frame.text.strip()
            if notes:
                lines.append("")
                lines.append("[备注] " + notes.replace("\n", " "))
        sections.append("\n".join(lines))
    return "\n\n".join(sections) + "\n", slide_count


def main():
    p = argparse.ArgumentParser(description="Extract text from a .pptx")
    p.add_argument("input")
    p.add_argument("-o", "--output", required=True)
    ns = p.parse_args()

    text, n = extract(ns.input)
    out = Path(ns.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8", newline="\n")
    print("done: %s" % out)
    print("slides=%d bytes=%d" % (n, out.stat().st_size))
    return 0


if __name__ == "__main__":
    sys.exit(main())
