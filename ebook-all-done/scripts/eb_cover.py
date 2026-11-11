#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""eb-cover：封面提取 / 替换 / 生成。"""
import argparse
import io
import os
import posixpath
import sys
from xml.etree import ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eb_common import (OPF_NS, Epub, conflict_path, edit_opf, ensure_parent, ext_of,
                       manifest_element, meta_element, mime_of,
                       no_overwrite, result, rewrite_epub, setup_stdout,
                       EXIT_FORMAT, EXIT_USAGE)


def make_cover(title, author):
    """用 Pillow 生成一张简洁的纯色文字封面，返回 PNG 字节串。"""
    from eb_common import need_pillow
    need_pillow()
    from PIL import Image, ImageDraw, ImageFont

    W, H = 800, 1200
    img = Image.new("RGB", (W, H), "#16213e")
    d = ImageDraw.Draw(img)
    d.rectangle([70, 70, W - 70, H - 70], outline="#5b8cff", width=4)
    d.rectangle([120, 250, 380, 262], fill="#5b8cff")

    def font(size):
        paths = [r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf",
                 "/System/Library/Fonts/PingFang.ttc",
                 "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                 "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"]
        for p in paths:
            if os.path.isfile(p):
                try:
                    return ImageFont.truetype(p, size)
                except Exception:
                    pass
        return ImageFont.load_default()

    def wrap(text, f, max_w):
        lines, line = [], ""
        for ch in text:
            if d.textlength(line + ch, font=f) <= max_w:
                line += ch
            else:
                if line:
                    lines.append(line)
                line = ch
        if line:
            lines.append(line)
        return lines

    tf = font(68)
    y = 340
    for ln in wrap(title or "未命名", tf, W - 240):
        d.text((120, y), ln, font=tf, fill="#ffffff")
        y += 100
    af = font(34)
    if author:
        d.text((120, H - 220), author, font=af, fill="#a8b8d8")
    d.text((120, H - 150), "ebook-all-done", font=font(22), fill="#6b7a99")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def set_cover_opf(ep, rel_href, media_type):
    def apply(root):
        md, mf = meta_element(root), manifest_element(root)
        cover_id = None
        for attrs, _ in ep.meta_tags:
            if attrs.get("name", "").lower() == "cover":
                cover_id = attrs.get("content")
        item = None
        for child in mf:
            if (child.get("id") == cover_id or
                    "cover-image" in (child.get("properties") or "").split()):
                item = child
                break
        if item is None:
            item = ET.SubElement(mf, "{%s}item" % OPF_NS,
                                 {"id": "ebook-cover-image"})
            cover_id = "ebook-cover-image"
        else:
            cover_id = item.get("id") or "ebook-cover-image"
        item.set("href", rel_href)
        item.set("media-type", media_type)
        props = set((item.get("properties") or "").split())
        props.add("cover-image")
        item.set("properties", " ".join(sorted(props)))
        for child in list(md):
            if (child.tag.endswith("}meta") or child.tag == "meta") and \
                    child.get("name", "").lower() == "cover":
                md.remove(child)
        ET.SubElement(md, "{%s}meta" % OPF_NS,
                      {"name": "cover", "content": cover_id})
    return edit_opf(ep, apply)


def main():
    setup_stdout()
    ap = argparse.ArgumentParser(description="电子书封面提取 / 替换 / 生成")
    ap.add_argument("--input", required=True, help="源 EPUB")
    ap.add_argument("--output", required=True, help="提取时为图片路径；替换/生成时为新 EPUB")
    ap.add_argument("--replace", help="用作新封面的图片")
    ap.add_argument("--generate", action="store_true", help="生成文字封面（需 Pillow）")
    ap.add_argument("--title", help="生成封面时的书名")
    ap.add_argument("--author", help="生成封面时的作者")
    args = ap.parse_args()

    ep = Epub(args.input)
    # 提取
    if not args.replace and not args.generate:
        cover = ep.cover_path()
        if not cover:
            from eb_common import die
            die("这本书没有可识别的封面（OPF 无 cover 声明、也无封面文件）", EXIT_FORMAT)
        out = args.output
        if os.path.isdir(out) or not os.path.splitext(out)[1]:
            out = os.path.join(out if os.path.isdir(out) else os.path.dirname(out) or ".",
                               "cover" + ext_of(cover))
        out = conflict_path(out)
        if out is None:
            print("已跳过（输出已存在，EBOOK_ON_CONFLICT=skip）")
            return 0
        ensure_parent(out)
        with open(out, "wb") as f:
            f.write(ep.read(cover))
        result(out, 原始路径=cover, 字节=os.path.getsize(out))
        ep.close()
        return 0

    no_overwrite(args.input, args.output)
    ep.guard_writable()
    if args.generate:
        image_bytes = make_cover(args.title or ep.title(),
                                 args.author or ep.dc("creator"))
        new_ext = ".png"
    else:
        if not os.path.isfile(args.replace):
            from eb_common import die
            die("封面图片不存在：%s" % args.replace, EXIT_USAGE)
        with open(args.replace, "rb") as f:
            image_bytes = f.read()
        new_ext = ext_of(args.replace) or ".jpg"
    filename = "ebook-cover" + new_ext
    new_path = posixpath.join(ep.opf_dir, "images", filename).lstrip("/")
    rel_href = posixpath.relpath(new_path, ep.opf_dir or ".")
    additions = {new_path: image_bytes,
                 ep.opf_path: set_cover_opf(ep, rel_href, mime_of(filename))}
    rewrite_epub(ep, args.output, replacements=additions)
    result(args.output, 封面=new_path, 字节=len(image_bytes))
    ep.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
