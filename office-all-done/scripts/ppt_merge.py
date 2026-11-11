#!/usr/bin/env python3
"""Merge multiple .pptx decks into one, in argument order.

Each source slide is cloned by copying its shape tree onto a new slide that
reuses the target deck's layout — matched by layout name first, then a blank
layout, so the merged deck keeps the first file's master and palette.

Embedded pictures are carried over: every relationship referenced by a cloned
shape (r:embed / r:link) is re-created in the target package and the cloned
attribute is rewritten to the new rId. Audio/video and other OLE parts are not
copied; those placeholders are dropped and reported.

Install python-pptx via `python scripts/bootstrap.py install`.
"""

import argparse
import copy
import sys
from io import BytesIO
from pathlib import Path

try:
    from pptx import Presentation
    from pptx.oxml.ns import qn
except ImportError:
    sys.exit("缺少 python-pptx。请先运行：python scripts/bootstrap.py install")

R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def drop_default_slides(prs):
    """Remove the template's starter slides together with their relationships."""
    sldIdLst = prs.slides._sldIdLst
    for sldId in list(sldIdLst):
        rId = sldId.get(qn("r:id"))
        sldIdLst.remove(sldId)
        if rId:
            try:
                prs.part.drop_rel(rId)
            except KeyError:
                pass


def pick_layout(target, source_slide):
    """Prefer the source layout by name, else the deck's blankest layout."""
    name = source_slide.slide_layout.name
    for layout in target.slide_layouts:
        if layout.name == name:
            return layout
    for layout in target.slide_layouts:
        if (layout.name or "").lower() == "blank":
            return layout
    return min(target.slide_layouts, key=lambda l: len(l.placeholders))


def remap_rels(element, src_slide, dst_slide, stats):
    """Rewrite r:* relationship ids in a cloned element for the target package."""
    for el in element.iter():
        for attr, value in list(el.attrib.items()):
            if not attr.startswith("{%s}" % R_NS):
                continue
            try:
                rel = src_slide.part.rels[value]
            except KeyError:
                continue
            if rel.is_external:
                el.set(attr, dst_slide.part.rels.get_or_add_ext_rel(
                    rel.reltype, rel.target_ref))
                continue
            part = rel.target_part
            if not str(part.content_type).startswith("image/"):
                el.attrib.pop(attr)
                stats["dropped"] += 1
                continue
            _, new_rid = dst_slide.part.get_or_add_image_part(BytesIO(part.blob))
            el.set(attr, new_rid)
            stats["images"] += 1


def merge_deck(target, source, stats):
    added = 0
    for slide in source.slides:
        new_slide = target.slides.add_slide(pick_layout(target, slide))
        # add_slide inherits layout placeholders; drop them so the clone is the
        # only content (otherwise empty "Click to add title" boxes appear).
        for shp in list(new_slide.shapes):
            shp._element.getparent().remove(shp._element)
        for shp in slide.shapes:
            new_el = copy.deepcopy(shp._element)
            remap_rels(new_el, slide, new_slide, stats)
            new_slide.shapes._spTree.append(new_el)
        added += 1
    return added


def main():
    p = argparse.ArgumentParser(description="Merge .pptx decks")
    p.add_argument("inputs", nargs="+")
    p.add_argument("-o", "--output", required=True)
    ns = p.parse_args()

    out = Path(ns.output).resolve()
    if str(out) in [str(Path(i).resolve()) for i in ns.inputs]:
        sys.exit("refusing to overwrite an input file")

    target = Presentation()
    drop_default_slides(target)
    stats = {"images": 0, "dropped": 0}

    count = 0
    for src_path in ns.inputs:
        count += merge_deck(target, Presentation(src_path), stats)

    out.parent.mkdir(parents=True, exist_ok=True)
    target.save(str(out))
    print("done: %s" % out)
    print("sources=%d slides=%d images=%d bytes=%d" %
          (len(ns.inputs), count, stats["images"], out.stat().st_size))
    if stats["dropped"]:
        print("note: %d 个音视频/OLE 部件未复制，请手动补回" % stats["dropped"])
    print("note: 母版与配色以首个文件为准；动画与切换效果不保留")
    return 0


if __name__ == "__main__":
    sys.exit(main())
