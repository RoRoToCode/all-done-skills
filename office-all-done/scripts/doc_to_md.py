#!/usr/bin/env python3
"""Convert a .docx file to Markdown.

Blocks are separated by a blank line (so the Markdown renders as typed),
headings map to "#" levels, bullet/numbered lists to "-"/"1." with indentation,
bold/italic to **/*, hyperlinks to [text](url) and tables to GFM pipe tables.
Images become `![](name)` placeholders; pass `--images DIR` to also export the
embedded picture files there.

Install python-docx via `python scripts/bootstrap.py install`.
"""

import argparse
import sys
from pathlib import Path

try:
    import docx
    from docx.oxml.ns import qn
except ImportError:
    sys.exit("缺少 python-docx。请先运行：python scripts/bootstrap.py install")

R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def heading_level(style_name):
    if not style_name:
        return 0
    if style_name.startswith("Heading"):
        digits = "".join(ch for ch in style_name if ch.isdigit())
        return max(1, min(int(digits) if digits else 1, 6))
    if style_name == "Title":
        return 1
    return 0


def text_of(element):
    return "".join(node.text or "" for node in element.iter(qn("w:t")))


def switch_on(rpr, tag):
    """True when the run property is switched on. Word writes <w:b w:val="0"/>
    for an explicit OFF, so presence alone is not enough."""
    if rpr is None:
        return False
    el = rpr.find(qn(tag))
    if el is None:
        return False
    return (el.get(qn("w:val")) or "true").lower() not in ("0", "false", "off")


def run_md(run, part, images_dir, stats):
    """Render one w:r: formatted text plus any inline picture."""
    pieces = []
    rpr = run.find(qn("w:rPr"))
    bold = switch_on(rpr, "w:b")
    italic = switch_on(rpr, "w:i")
    strike = switch_on(rpr, "w:strike")

    for blip in run.iter(qn("a:blip")):
        rid = blip.get("{%s}embed" % R_NS)
        if not rid:
            continue
        try:
            image_part = part.rels[rid].target_part
        except KeyError:
            continue
        name = Path(str(image_part.partname)).name
        if images_dir is not None:
            target = Path(images_dir) / name
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                target.write_bytes(image_part.blob)
        stats["images"] += 1
        pieces.append("![](%s)" % name)

    text = "".join(node.text or "" for node in run.iter(qn("w:t")))
    if text:
        if bold and italic:
            text = "***%s***" % text
        elif bold:
            text = "**%s**" % text
        elif italic:
            text = "*%s*" % text
        if strike:
            text = "~~%s~~" % text
        pieces.append(text)
    return "".join(pieces)


def paragraph_md(paragraph, part, images_dir, stats):
    pieces = []
    for child in paragraph._p.iterchildren():
        tag = child.tag
        if tag == qn("w:r"):
            pieces.append(run_md(child, part, images_dir, stats))
        elif tag == qn("w:hyperlink"):
            label = text_of(child)
            rid = child.get("{%s}id" % R_NS)
            url = ""
            if rid:
                try:
                    rel = part.rels[rid]
                    url = rel.target_ref or ""
                except KeyError:
                    url = ""
            if not label:
                continue
            pieces.append("[%s](%s)" % (label, url) if url and url.startswith("http")
                          else label)
        elif tag == qn("w:fldSimple"):
            pieces.append(text_of(child))
    return "".join(pieces)


def list_prefix(paragraph):
    """Return ("- " | "1. " | None, indent) for a list paragraph."""
    style = paragraph.style.name if paragraph.style else ""
    num_pr = paragraph._p.find(qn("w:pPr") + "/" + qn("w:numPr"))
    if "List" not in style and num_pr is None:
        return None, 0
    level = 0
    if num_pr is not None:
        ilvl = num_pr.find(qn("w:ilvl"))
        if ilvl is not None and (ilvl.get(qn("w:val")) or "").isdigit():
            level = int(ilvl.get(qn("w:val")))
    ordered = "Number" in style or (num_pr is not None and "Bullet" not in style)
    marker = "1. " if ordered else "- "
    return marker, min(level, 4) * 2


def table_to_md(table):
    rows = []
    for index, row in enumerate(table.rows):
        cells = [c.text.replace("\n", " ").replace("|", "\\|").strip()
                 for c in row.cells]
        rows.append("| " + " | ".join(cells) + " |")
        if index == 0:
            rows.append("| " + " | ".join(["---"] * len(cells)) + " |")
    return "\n".join(rows)


def convert(path, images_dir=None):
    document = docx.Document(path)
    part = document.part
    stats = {"images": 0}
    blocks = []
    pending_list = []
    pending_kind = None

    def flush():
        if pending_list:
            blocks.append("\n".join(pending_list))
            pending_list.clear()

    for block in _iter(document):
        if block.__class__.__name__ == "Paragraph":
            style = block.style.name if block.style else ""
            level = heading_level(style)
            body = paragraph_md(block, part, images_dir, stats).strip()
            if level:
                flush()
                if body:
                    blocks.append("#" * level + " " + body)
                continue
            marker, indent = list_prefix(block)
            if marker:
                if marker != pending_kind:  # bullet and ordered runs stay apart
                    flush()
                    pending_kind = marker
                if body:
                    pending_list.append(" " * indent + marker + body)
                continue
            flush()
            pending_kind = None
            if body:
                blocks.append(body)
        else:
            flush()
            pending_kind = None
            blocks.append(table_to_md(block))
    flush()
    return "\n\n".join(blocks).strip() + "\n", stats


def _iter(parent):
    from docx.oxml.table import CT_Tbl
    from docx.oxml.text.paragraph import CT_P
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    for child in parent.element.body.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)


def main():
    p = argparse.ArgumentParser(description="Convert .docx to Markdown")
    p.add_argument("input")
    p.add_argument("-o", "--output", required=True)
    p.add_argument("--images", help="directory to export embedded pictures into")
    ns = p.parse_args()

    md, stats = convert(ns.input, ns.images)
    out = Path(ns.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md, encoding="utf-8", newline="\n")
    print("done: %s" % out)
    print("bytes=%d images=%d" % (out.stat().st_size, stats["images"]))
    if stats["images"] and not ns.images:
        print("note: 图片仅以文件名占位，加 --images DIR 可导出图片文件")
    return 0


if __name__ == "__main__":
    sys.exit(main())
