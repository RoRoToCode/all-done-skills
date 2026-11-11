#!/usr/bin/env python3
"""Extract text from a .docx file, preserving heading levels and tables.

Output is plain text: headings prefixed with "#" by level, lists with "-",
and tables rendered as tab-separated rows. Install python-docx via
`python scripts/bootstrap.py install`.
"""

import argparse
import sys
from pathlib import Path

try:
    import docx
    from docx.oxml.ns import qn
except ImportError:
    sys.exit("缺少 python-docx。请先运行：python scripts/bootstrap.py install")


def text_of(paragraph):
    """Concatenate every w:t in the paragraph, so hyperlink runs are kept."""
    return "".join(node.text or "" for node in paragraph._p.iter(qn("w:t")))


def iter_block_items(parent):
    """Yield paragraphs and tables in document order."""
    from docx.document import Document as _Doc
    from docx.oxml.table import CT_Tbl
    from docx.oxml.text.paragraph import CT_P
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    body = parent.element.body
    for child in body.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)


def heading_prefix(style_name):
    if style_name and style_name.startswith("Heading"):
        digits = "".join(ch for ch in style_name if ch.isdigit())
        level = int(digits) if digits else 1
        return "#" * max(1, min(level, 6)) + " "
    if style_name in ("Title",):
        return "# "
    return ""


def extract(path):
    document = docx.Document(path)
    lines = []
    table_count = 0
    for block in iter_block_items(document):
        if block.__class__.__name__ == "Paragraph":
            style = block.style.name if block.style else ""
            text = text_of(block)
            prefix = heading_prefix(style)
            lines.append(prefix + text)
        else:  # Table
            table_count += 1
            lines.append("<!-- table %d -->" % table_count)
            for row in block.rows:
                cells = [c.text.replace("\n", " ") for c in row.cells]
                lines.append("\t".join(cells))
            lines.append("<!-- /table %d -->" % table_count)
    return "\n".join(lines).strip() + "\n", len(document.paragraphs), table_count


def main():
    p = argparse.ArgumentParser(description="Extract text from a .docx")
    p.add_argument("input")
    p.add_argument("-o", "--output", required=True)
    ns = p.parse_args()

    text, n_para, n_tables = extract(ns.input)
    out = Path(ns.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8", newline="\n")
    print("done: %s" % out)
    print("paragraphs=%d tables=%d bytes=%d" %
          (n_para, n_tables, out.stat().st_size))
    return 0


if __name__ == "__main__":
    sys.exit(main())
