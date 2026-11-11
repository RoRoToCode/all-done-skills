"""img-resize：改尺寸（长边 / 固定宽高 / 百分比），默认保持比例。"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from img_common import need_pillow, no_overwrite, save_image, result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--width", type=int, default=None)
    ap.add_argument("--height", type=int, default=None)
    ap.add_argument("--long-edge", type=int, default=None, help="最长边像素")
    ap.add_argument("--scale", type=float, default=None, help="百分比，如 50 表示一半")
    ap.add_argument("--no-keep-ratio", action="store_true", help="强行拉伸到 width x height")
    args = ap.parse_args()

    Image = need_pillow()
    no_overwrite(args.input, args.output)
    img = Image.open(args.input)
    w, h = img.size

    if args.no_keep_ratio and args.width and args.height:
        nw, nh = args.width, args.height
    elif args.long_edge:
        ratio = args.long_edge / float(max(w, h))
        nw, nh = int(round(w * ratio)), int(round(h * ratio))
    elif args.scale:
        nw, nh = int(round(w * args.scale / 100.0)), int(round(h * args.scale / 100.0))
    elif args.width and args.height:
        nw, nh = args.width, args.height
    elif args.width:
        ratio = args.width / float(w)
        nw, nh = args.width, int(round(h * ratio))
    elif args.height:
        ratio = args.height / float(h)
        nw, nh = int(round(w * ratio)), args.height
    else:
        sys.stderr.write("请至少提供 --width / --height / --long-edge / --scale 之一\n")
        sys.exit(1)

    nw, nh = max(1, nw), max(1, nh)
    img = img.resize((nw, nh), Image.LANCZOS)
    save_image(img, args.output, optimize=True)
    result(args.output, img)


if __name__ == "__main__":
    main()
