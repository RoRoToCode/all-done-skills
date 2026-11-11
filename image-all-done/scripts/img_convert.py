"""img-convert：图片格式互转（png/jpg/webp/bmp/tiff）。"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from img_common import need_pillow, no_overwrite, save_image, result, hex_rgb


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--quality", type=int, default=90, help="jpg/webp 质量 1-100")
    ap.add_argument("--background", default="FFFFFF", help="透明背景填充色 RRGGBB")
    args = ap.parse_args()

    Image = need_pillow()
    no_overwrite(args.input, args.output)
    img = Image.open(args.input)
    fmt = os.path.splitext(args.output)[1].lower().lstrip(".")
    if img.mode == "P":
        img = img.convert("RGBA")
    if fmt in ("jpg", "jpeg"):
        if img.mode in ("RGBA", "LA"):
            bg = Image.new("RGB", img.size, hex_rgb(args.background))
            bg.paste(img, mask=img.split()[-1])
            img = bg
        else:
            img = img.convert("RGB")
        save_image(img, args.output, quality=args.quality, optimize=True)
    else:
        kwargs = {}
        if fmt == "webp":
            kwargs["quality"] = args.quality
        elif fmt == "png":
            kwargs["optimize"] = True
        save_image(img, args.output, **kwargs)
    result(args.output, img)


if __name__ == "__main__":
    main()
