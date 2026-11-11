#!/usr/bin/env python3
"""Merge multiple .docx files into one, in argument order.

The first file supplies page setup, theme and section layout; every later file
is appended before its final section break. Styles, list numbering definitions,
images and hyperlinks from all sources are carried over, so headings, bullets
and pictures survive the merge.

Known limits: headers/footers come from the first file only; footnotes,
endnotes, comments and tracked changes are not merged.

Install python-docx via `python scripts/bootstrap.py install`.
"""

import argparse
import copy
import sys
from io import BytesIO
from pathlib import Path

try:
    from docx import Document
    from docx.enum.text import WD_BREAK
    from docx.opc.constants import RELATIONSHIP_TYPE as RT
    from docx.oxml.ns import qn
except ImportError:
    sys.exit("缺少 python-docx。请先运行：python scripts/bootstrap.py install")

R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def merge_styles(target, src):
    """Copy style definitions from src into target, keeping existing ones."""
    t_styles = target.styles.element
    existing = {s.get(qn("w:styleId")) for s in t_styles.findall(qn("w:style"))}
    for style in src.styles.element.findall(qn("w:style")):
        sid = style.get(qn("w:styleId"))
        if sid and sid not in existing:
            t_styles.append(copy.deepcopy(style))
            existing.add(sid)


def import_numbering(target, src):
    """Copy numbering definitions and return {old numId: new numId}."""
    tgt = target.part.numbering_part.element
    src_num = src.part.numbering_part.element

    nums = tgt.findall(qn("w:num"))
    abstracts = tgt.findall(qn("w:abstractNum"))
    next_num = max([int(n.get(qn("w:numId"))) for n in nums] or [0]) + 1
    next_abs = max([int(a.get(qn("w:abstractNumId"))) for a in abstracts] or [0]) + 1

    # w:abstractNum must precede every w:num in the schema, so insert them
    # before the first existing w:num instead of appending.
    first_num = nums[0] if nums else None
    abs_map = {}
    for absn in src_num.findall(qn("w:abstractNum")):
        old = int(absn.get(qn("w:abstractNumId")))
        clone = copy.deepcopy(absn)
        clone.set(qn("w:abstractNumId"), str(next_abs))
        if first_num is not None:
            first_num.addprevious(clone)
        else:
            tgt.append(clone)
        abs_map[old] = next_abs
        next_abs += 1

    num_map = {}
    for num in src_num.findall(qn("w:num")):
        old = int(num.get(qn("w:numId")))
        clone = copy.deepcopy(num)
        ref = clone.find(qn("w:abstractNumId"))
        if ref is not None:
            aid = int(ref.get(qn("w:val")))
            ref.set(qn("w:val"), str(abs_map.get(aid, aid)))
        clone.set(qn("w:numId"), str(next_num))
        tgt.append(clone)
        num_map[old] = next_num
        next_num += 1
    return num_map


def add_image_part(doc, blob):
    """Add an image part to doc and return its rId.

    python-docx renamed this API: 1.1 exposes get_or_add_image_part, 1.2
    exposes get_or_add_image. Both return (rId, image).
    """
    api = getattr(doc.part, "get_or_add_image", None) or getattr(
        doc.part, "get_or_add_image_part")
    r_id, _image = api(BytesIO(blob))
    return r_id


def remap_rels(element, src_doc, dst_doc, stats):
    """Rewrite r:* relationship ids in a cloned element for the target package."""
    for el in element.iter():
        for attr, value in list(el.attrib.items()):
            if not attr.startswith("{%s}" % R_NS):
                continue
            try:
                rel = src_doc.part.rels[value]
            except KeyError:
                continue
            if rel.is_external:
                el.set(attr, dst_doc.part.relate_to(
                    rel.target_ref, rel.reltype, is_external=True))
                continue
            part = rel.target_part
            if not str(part.content_type).startswith("image/"):
                el.attrib.pop(attr)
                stats["dropped"] += 1
                continue
            el.set(attr, add_image_part(dst_doc, part.blob))
            stats["images"] += 1


def remap_numbering(element, num_map):
    if not num_map:
        return
    for num_id in element.iter(qn("w:numId")):
        old = num_id.get(qn("w:val"))
        if old is not None and old.isdigit() and int(old) in num_map:
            num_id.set(qn("w:val"), str(num_map[int(old)]))


def main():
    p = argparse.ArgumentParser(description="Merge .docx files")
    p.add_argument("inputs", nargs="+")
    p.add_argument("-o", "--output", required=True)
    p.add_argument("--page-break", action="store_true",
                   help="start each merged document on a new page")
    ns = p.parse_args()

    out = Path(ns.output).resolve()
    if str(out) in [str(Path(i).resolve()) for i in ns.inputs]:
        sys.exit("refusing to overwrite an input file")

    target = Document(ns.inputs[0])
    body = target.element.body
    sectPr = body.find(qn("w:sectPr"))
    stats = {"images": 0, "dropped": 0}
    merged = 1

    for src_path in ns.inputs[1:]:
        src = Document(src_path)
        merge_styles(target, src)
        num_map = import_numbering(target, src)
        if ns.page_break:
            paragraph = target.add_paragraph()
            paragraph.add_run().add_break(WD_BREAK.PAGE)
        for child in list(src.element.body):
            if child.tag == qn("w:sectPr"):
                continue  # page setup of later files is dropped on purpose
            clone = copy.deepcopy(child)
            remap_rels(clone, src, target, stats)
            remap_numbering(clone, num_map)
            if sectPr is not None:
                sectPr.addprevious(clone)
            else:
                body.append(clone)
        merged += 1

    out.parent.mkdir(parents=True, exist_ok=True)
    target.save(str(out))
    print("done: %s" % out)
    print("merged=%d images=%d bytes=%d" %
          (merged, stats["images"], out.stat().st_size))
    if stats["dropped"]:
        print("note: %d 个非图片部件（图表/OLE/视频）未复制，请手动补回"
              % stats["dropped"])
    print("note: 页眉页脚取首个文件；页码、目录需在 Word 中重新更新域")
    return 0


if __name__ == "__main__":
    sys.exit(main())
