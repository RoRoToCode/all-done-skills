"""img-merge：多图拼接（横向 / 纵向 / 网格）。"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image
from img_common import need_pillow, no_overwrite, save_image, result, hex_rgb


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", required=True, nargs="+")
    ap.add_argument("--output", required=True)
    ap.add_argument("--layout", default="h", help="h(横) / v(纵) / grid(网格)")
    ap.add_argument("--cols", type=int, default=2, help="grid 列数")
    ap.add_argument("--gap", type=int, default=0, help="间距像素")
    ap.add_argument("--bg", default="FFFFFF", help="背景色 RRGGBB")
    args = ap.parse_args()

    need_pillow()
    for i in args.inputs:
        no_overwrite(i, args.output)
    imgs = [Image.open(p).convert("RGB") for p in args.inputs]
    bg = hex_rgb(args.bg)
    g = args.gap

    if args.layout == "h":
        h = max(i.height for i in imgs)
        w = sum(i.width for i in imgs) + g * (len(imgs) - 1)
        canvas = Image.new("RGB", (w, h), bg)
        x = 0
        for i in imgs:
            canvas.paste(i, (x, (h - i.height) // 2))
            x += i.width + g
    elif args.layout == "v":
        w = max(i.width for i in imgs)
        h = sum(i.height for i in imgs) + g * (len(imgs) - 1)
        canvas = Image.new("RGB", (w, h), bg)
        y = 0
        for i in imgs:
            canvas.paste(i, ((w - i.width) // 2, y))
            y += i.height + g
    else:
        cols = max(1, args.cols)
        rows = (len(imgs) + cols - 1) // cols
        cw = max(i.width for i in imgs)
        ch = max(i.height for i in imgs)
        w = cols * cw + g * (cols - 1)
        h = rows * ch + g * (rows - 1)
        canvas = Image.new("RGB", (w, h), bg)
        for idx, i in enumerate(imgs):
            r, c = divmod(idx, cols)
            x = c * (cw + g) + (cw - i.width) // 2
            y = r * (ch + g) + (ch - i.height) // 2
            canvas.paste(i, (x, y))

    save_image(canvas, args.output, quality=90, optimize=True)
    result(args.output, canvas)


if __name__ == "__main__":
    main()
