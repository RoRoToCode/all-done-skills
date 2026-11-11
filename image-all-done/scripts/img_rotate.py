"""img-rotate：旋转 / 翻转，默认按 EXIF 方向自动校正。"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageOps
from img_common import need_pillow, no_overwrite, save_image, result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--angle", type=float, default=90, help="顺时针旋转角度")
    ap.add_argument("--flip", default="none", help="none / h(水平) / v(垂直)")
    ap.add_argument("--no-auto-orient", action="store_true", help="不做 EXIF 方向校正")
    args = ap.parse_args()

    need_pillow()
    no_overwrite(args.input, args.output)
    img = Image.open(args.input)
    if not args.no_auto_orient:
        img = ImageOps.exif_transpose(img)
    if args.angle:
        img = img.rotate(-args.angle, expand=True)
    if args.flip == "h":
        img = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    elif args.flip == "v":
        img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    fmt = os.path.splitext(args.output)[1].lower().lstrip(".")
    kwargs = {"optimize": True}
    if fmt in ("jpg", "jpeg"):
        if img.mode in ("RGBA", "LA"):
            img = img.convert("RGB")
        kwargs["quality"] = 90
    save_image(img, args.output, **kwargs)
    result(args.output, img)


if __name__ == "__main__":
    main()
