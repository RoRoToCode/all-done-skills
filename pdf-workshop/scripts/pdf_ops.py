#!/usr/bin/env python3
"""Page-level PDF editing and batch processing.

Merge / split / encrypt / decrypt are delegated to the official workbuddy-pdf
CLI through wb_pdf.py (no third-party dependency). Rotate / delete / reorder /
crop / page numbers / watermark use pypdf, which is installed by bootstrap.py.
"""

import argparse
import io
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import md_to_pdf  # noqa: E402
import wb_pdf  # noqa: E402

from pypdf import PdfReader, PdfWriter  # noqa: E402
from pypdf.generic import (DecodedStreamObject, DictionaryObject,  # noqa: E402
                           NameObject, RectangleObject)


def parse_pages(spec, total):
    """Turn '1,3-5,8' into a set of zero-based page indices."""
    if not spec:
        return set(range(total))
    result = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = part.split("-", 1)
            lo, hi = int(start), int(end)
        else:
            lo = hi = int(part)
        if lo < 1 or hi > total or lo > hi:
            raise ValueError("页码超出范围: %s (共 %d 页)" % (part, total))
        result.update(range(lo - 1, hi))
    return result


def open_reader(path, password=None):
    reader = PdfReader(str(path))
    if reader.is_encrypted:
        if not password or not reader.decrypt(password):
            raise RuntimeError("PDF 已加密，需要 -p/--password")
    return reader


def write_pdf(writer, out_path):
    out_path = Path(out_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("wb") as handle:
        writer.write(handle)
    return str(out_path)


def op_info(args):
    reader = open_reader(args.input, args.password)
    sizes = []
    for page in reader.pages:
        box = page.mediabox
        sizes.append([round(float(box.width), 2), round(float(box.height), 2)])
    meta = {}
    if reader.metadata:
        for key, value in reader.metadata.items():
            meta[str(key)] = str(value)
    payload = {"file": str(Path(args.input).resolve()), "pages": len(reader.pages),
               "encrypted": bool(reader.is_encrypted), "page_sizes": sizes,
               "metadata": meta}
    if getattr(args, "output", None):
        out_path = Path(args.output).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                            encoding="utf-8")
        print(json.dumps({"output": str(out_path), "pages": len(reader.pages)},
                         ensure_ascii=False))
        return 0
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def op_rotate(args):
    reader = open_reader(args.input, args.password)
    targets = parse_pages(args.pages, len(reader.pages))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    for index in targets:
        writer.pages[index].rotate(args.angle)
    print(json.dumps({"output": write_pdf(writer, args.output),
                      "rotated": len(targets), "angle": args.angle}, ensure_ascii=False))
    return 0


def op_delete(args):
    reader = open_reader(args.input, args.password)
    drop = parse_pages(args.pages, len(reader.pages))
    writer = PdfWriter()
    kept = 0
    for index, page in enumerate(reader.pages):
        if index not in drop:
            writer.add_page(page)
            kept += 1
    print(json.dumps({"output": write_pdf(writer, args.output),
                      "pages": kept}, ensure_ascii=False))
    return 0


def op_reorder(args):
    reader = open_reader(args.input, args.password)
    order = [int(x) - 1 for x in args.order.split(",")]
    if sorted(order) != list(range(len(reader.pages))):
        raise ValueError("--order 必须是不重复且覆盖全部页的排列，例如 3,1,2")
    writer = PdfWriter()
    for index in order:
        writer.add_page(reader.pages[index])
    print(json.dumps({"output": write_pdf(writer, args.output), "order": order},
                     ensure_ascii=False))
    return 0


def op_crop(args):
    left, bottom, right, top = [float(x) for x in args.box.split(",")]
    reader = open_reader(args.input, args.password)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    for page in writer.pages:
        box = page.mediabox
        width, height = float(box.width), float(box.height)
        new_box = RectangleObject((left, bottom, width - right, height - top))
        page.mediabox = new_box
        page.cropbox = RectangleObject((left, bottom, width - right, height - top))
    print(json.dumps({"output": write_pdf(writer, args.output),
                      "box": [left, bottom, right, top]}, ensure_ascii=False))
    return 0


def _text_overlay_page(width, height, text, x, y, font_size=10, gray=0.45):
    writer = PdfWriter()
    page = writer.add_blank_page(width=width, height=height)
    escaped = text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
    content = ("BT /F1 %.2f Tf %.2f g %.2f %.2f Td (%s) Tj ET\n" %
               (font_size, gray, x, y, escaped))
    font = DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
        NameObject("/Encoding"): NameObject("/WinAnsiEncoding"),
    })
    page[NameObject("/Resources")] = DictionaryObject({
        NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})
    })
    stream = DecodedStreamObject()
    stream.set_data(content.encode("ascii", "backslashreplace"))
    page[NameObject("/Contents")] = stream
    buffer = io.BytesIO()
    writer.write(buffer)
    buffer.seek(0)
    return PdfReader(buffer).pages[0]


def op_page_numbers(args):
    reader = open_reader(args.input, args.password)
    total = len(reader.pages)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    for index, page in enumerate(writer.pages):
        box = page.mediabox
        width, height = float(box.width), float(box.height)
        number = args.start + index
        label = args.format.replace("{n}", str(number)).replace("{total}", str(total))
        if args.position == "bc":
            x, y = width / 2 - len(label) * 2.6, 24
        elif args.position == "bl":
            x, y = 36, 24
        else:
            x, y = width - 36 - len(label) * 5, 24
        overlay = _text_overlay_page(width, height, label, x, y,
                                     font_size=args.font_size)
        page.merge_page(overlay)
    print(json.dumps({"output": write_pdf(writer, args.output),
                      "pages": total, "start": args.start}, ensure_ascii=False))
    return 0


def _watermark_overlay(width, height, text, font_size, angle, opacity, workdir):
    safe = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    document = ("<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
                "<style>@page{size:%spt %spt;margin:0}"
                "html,body{margin:0;padding:0;width:%spt;height:%spt;overflow:hidden}"
                ".wm{position:absolute;top:50%%;left:50%%;"
                "transform:translate(-50%%,-50%%) rotate(%sdeg);"
                "font-family:'Microsoft YaHei','SimSun',sans-serif;"
                "font-size:%spt;font-weight:bold;white-space:nowrap;"
                "color:rgba(0,0,0,%s)}</style></head>"
                "<body><div class=\"wm\">%s</div></body></html>" %
                (width, height, width, height, angle, font_size, opacity, safe))
    out = Path(workdir) / ("wm_%sx%s.pdf" % (int(width), int(height)))
    md_to_pdf.html_to_pdf(document, out, page_size=(width, height), workdir=workdir)
    return PdfReader(str(out)).pages[0]


def op_watermark(args):
    reader = open_reader(args.input, args.password)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    cache = {}
    with tempfile.TemporaryDirectory(prefix="pdf-workshop-wm-") as workdir:
        for page in writer.pages:
            box = page.mediabox
            width, height = float(box.width), float(box.height)
            key = (round(width), round(height))
            if key not in cache:
                cache[key] = _watermark_overlay(width, height, args.text,
                                                args.font_size, args.angle,
                                                args.opacity, workdir)
            page.merge_page(cache[key])
    print(json.dumps({"output": write_pdf(writer, args.output),
                      "pages": len(reader.pages), "text": args.text}, ensure_ascii=False))
    return 0


def op_encrypt(args):
    """The Windows build of workbuddy-pdf cannot write encrypted documents."""
    reader = open_reader(args.input, args.password)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.encrypt(user_password=args.new_password,
                   owner_password=args.owner_password or args.new_password,
                   algorithm=args.algorithm)
    print(json.dumps({"output": write_pdf(writer, args.output),
                      "pages": len(reader.pages), "algorithm": args.algorithm},
                     ensure_ascii=False))
    return 0


def op_decrypt(args):
    reader = PdfReader(str(args.input))
    if reader.is_encrypted and not reader.decrypt(args.password):
        raise RuntimeError("密码不正确或该 PDF 无法解密")
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    print(json.dumps({"output": write_pdf(writer, args.output),
                      "pages": len(reader.pages)}, ensure_ascii=False))
    return 0


DELEGATED = {
    "merge": lambda a: (["merge"] + a.inputs + ["-o", a.output]),
    "split": lambda a: (["split", a.input, "-o", a.output]),
}


def op_delegated(args):
    code = wb_pdf.run_action(DELEGATED[args.action](args))
    if code == 0:
        print(json.dumps({"output": str(Path(args.output).resolve()),
                          "action": args.action}, ensure_ascii=False))
    return code


def op_batch(args):
    files = []
    for item in args.inputs:
        path = Path(item)
        if path.is_dir():
            files.extend(sorted(path.glob(args.pattern)))
        else:
            files.extend(sorted(Path().glob(item)) if any(c in item for c in "*?[]") else [path])
    files = [f for f in files if f.suffix.lower() == ".pdf"]
    if not files:
        raise RuntimeError("没有找到匹配的 PDF 文件")
    if args.op == "delete" and not args.pages:
        raise RuntimeError("批量 delete 必须显式指定 --pages，避免误删全部页面")
    outdir = Path(args.output).resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    results = []
    for source in files:
        target = outdir / source.name
        child = argparse.Namespace(**vars(args))
        child.input = str(source)
        child.output = str(target)
        if args.op == "watermark":
            child.angle = args.angle_wm
        handler = {
            "rotate": op_rotate, "delete": op_delete, "reorder": op_reorder,
            "crop": op_crop, "page-numbers": op_page_numbers,
            "watermark": op_watermark,
        }[args.op]
        try:
            handler(child)
            results.append({"file": source.name, "status": "ok",
                            "output": str(target)})
        except Exception as exc:
            results.append({"file": source.name, "status": "error",
                            "message": str(exc)})
    manifest = outdir / "batch-manifest.json"
    manifest.write_text(json.dumps(results, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    print(json.dumps({"count": len(results),
                      "ok": sum(1 for r in results if r["status"] == "ok"),
                      "manifest": str(manifest)}, ensure_ascii=False))
    return 0 if all(r["status"] == "ok" for r in results) else 1


def build_parser():
    p = argparse.ArgumentParser(description="PDF page operations and batch processing")
    sub = p.add_subparsers(dest="action", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("input")
    common.add_argument("-o", "--output")
    common.add_argument("-p", "--password")

    sub.add_parser("info", parents=[common], help="page count, sizes, metadata")
    r = sub.add_parser("rotate", parents=[common], help="rotate selected pages")
    r.add_argument("--angle", type=int, default=90)
    r.add_argument("--pages", help="1-based ranges, e.g. 1,3-5")
    d = sub.add_parser("delete", parents=[common], help="delete selected pages")
    d.add_argument("--pages", required=True)
    o = sub.add_parser("reorder", parents=[common], help="reorder all pages")
    o.add_argument("--order", required=True, help="e.g. 3,1,2")
    c = sub.add_parser("crop", parents=[common], help="inset margins in points")
    c.add_argument("--box", required=True, help="left,bottom,right,top in pt")
    n = sub.add_parser("page-numbers", parents=[common], help="add ASCII page numbers")
    n.add_argument("--start", type=int, default=1)
    n.add_argument("--position", choices=["bl", "bc", "br"], default="bc")
    n.add_argument("--format", default="{n} / {total}")
    n.add_argument("--font-size", type=float, default=9)
    w = sub.add_parser("watermark", parents=[common], help="CJK-safe text watermark")
    w.add_argument("--text", required=True)
    w.add_argument("--font-size", type=float, default=48)
    w.add_argument("--angle", type=float, default=-30)
    w.add_argument("--opacity", type=float, default=0.12)

    m = sub.add_parser("merge", help="official CLI: join PDFs")
    m.add_argument("inputs", nargs="+")
    m.add_argument("-o", "--output", required=True)
    s = sub.add_parser("split", help="official CLI: one file per page")
    s.add_argument("input")
    s.add_argument("-o", "--output", required=True)
    e = sub.add_parser("encrypt", help="pypdf: set an opening password")
    e.add_argument("input")
    e.add_argument("-o", "--output", required=True)
    e.add_argument("--new-password", required=True)
    e.add_argument("--owner-password")
    e.add_argument("-p", "--password", help="password of an already encrypted input")
    e.add_argument("--algorithm", default="RC4-128",
                   choices=["RC4-128", "AES-128", "AES-256"])
    k = sub.add_parser("decrypt", help="pypdf: remove password protection")
    k.add_argument("input")
    k.add_argument("-o", "--output", required=True)
    k.add_argument("-p", "--password", required=True)

    b = sub.add_parser("batch", help="apply a page operation to many PDFs")
    b.add_argument("inputs", nargs="+", help="directories, globs or files")
    b.add_argument("-o", "--output", required=True, help="output directory")
    b.add_argument("--op", required=True,
                   choices=["rotate", "delete", "reorder", "crop",
                            "page-numbers", "watermark"])
    b.add_argument("--pattern", default="*.pdf")
    b.add_argument("-p", "--password")
    b.add_argument("--angle", type=int, default=90)
    b.add_argument("--pages")
    b.add_argument("--order")
    b.add_argument("--box")
    b.add_argument("--start", type=int, default=1)
    b.add_argument("--format", default="{n} / {total}")
    b.add_argument("--font-size", type=float, default=9)
    b.add_argument("--position", choices=["bl", "bc", "br"], default="bc")
    b.add_argument("--text", default="CONFIDENTIAL")
    b.add_argument("--opacity", type=float, default=0.12)
    b.add_argument("--angle-wm", type=float, default=-30,
                   help="watermark rotation, used with --op watermark")
    return p


def main():
    args = build_parser().parse_args()
    if args.action != "info" and not getattr(args, "output", None):
        print(json.dumps({"status": "error", "message": "该操作需要 -o/--output"},
                         ensure_ascii=False))
        return 2
    if args.action in DELEGATED:
        return op_delegated(args)
    handlers = {
        "info": op_info, "rotate": op_rotate, "delete": op_delete,
        "reorder": op_reorder, "crop": op_crop,
        "page-numbers": op_page_numbers, "watermark": op_watermark,
        "encrypt": op_encrypt, "decrypt": op_decrypt,
        "batch": op_batch,
    }
    try:
        return handlers[args.action](args)
    except Exception as exc:
        print(json.dumps({"status": "error", "action": args.action,
                          "message": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
