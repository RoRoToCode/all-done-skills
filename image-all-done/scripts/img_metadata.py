"""img-metadata：读取 EXIF；--output 另存（默认剥离元信息），--clear 显式清除。"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ExifTags
from img_common import need_pillow, no_overwrite, save_image, result


def tag_name(tag):
    return ExifTags.TAGS.get(tag, "0x%04X" % tag)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", default=None, help="另存路径；给定则剥离 EXIF")
    ap.add_argument("--clear", action="store_true", help="另存并剥离全部 EXIF 元信息")
    args = ap.parse_args()

    need_pillow()
    img = Image.open(args.input)
    exif = img.getexif()
    if exif:
        print("EXIF 字段：")
        for tag, val in exif.items():
            if isinstance(val, bytes):
                val = "<二进制 %d 字节>" % len(val)
            print("  %s = %s" % (tag_name(tag), val))
    else:
        print("该图片无 EXIF 元信息。")

    if args.output:
        no_overwrite(args.input, args.output)
        fmt = os.path.splitext(args.output)[1].lower().lstrip(".")
        kwargs = {"optimize": True}
        if fmt in ("jpg", "jpeg"):
            kwargs["quality"] = 90
            img = img.convert("RGB")
        # 不传 exif 即剥离；PNG 本身不保存 EXIF
        save_image(img, args.output, **kwargs)
        result(args.output, img)
        print("已%s EXIF 元信息。" % ("清除" if args.clear else "剥离"))


if __name__ == "__main__":
    main()
