"""img-crop：裁剪（绝对像素框 / 居中正方形 / 居中指定比例）。"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from img_common import need_pillow, no_overwrite, save_image, result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--box", default=None, help="绝对像素框 x0,y0,x1,y1")
    ap.add_argument("--square", action="store_true", help="居中裁成最大正方形")
    ap.add_argument("--ratio", default=None, help="居中裁成指定比例 W:H，如 16:9")
    args = ap.parse_args()

    Image = need_pillow()
    no_overwrite(args.input, args.output)
    img = Image.open(args.input)
    w, h = img.size

    if args.box:
        x0, y0, x1, y1 = (int(v) for v in args.box.split(","))
        if x1 <= x0 or y1 <= y0 or x1 > w or y1 > h:
            sys.stderr.write("box 超出图像范围\n")
            sys.exit(1)
        box = (x0, y0, x1, y1)
    elif args.square:
        s = min(w, h)
        box = ((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s)
    elif args.ratio:
        rw, rh = (int(v) for v in args.ratio.split(":"))
        target = rw / float(rh)
        cur = w / float(h)
        if cur > target:
            nh = h
            nw = int(round(h * target))
        else:
            nw = w
            nh = int(round(w / target))
        box = ((w - nw) // 2, (h - nh) // 2, (w - nw) // 2 + nw, (h - nh) // 2 + nh)
    else:
        sys.stderr.write("请指定 --box / --square / --ratio 之一\n")
        sys.exit(1)

    img = img.crop(box)
    save_image(img, args.output, optimize=True)
    result(args.output, img)


if __name__ == "__main__":
    main()
