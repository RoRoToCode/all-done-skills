"""img-watermark：文字水印（平铺或居中），可调透明度/位置/颜色。"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw
from img_common import need_pillow, no_overwrite, save_image, result, hex_rgb, load_font


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--text", required=True)
    ap.add_argument("--font-size", type=int, default=36)
    ap.add_argument("--opacity", type=int, default=128, help="0-255，越大越实")
    ap.add_argument("--color", default="FFFFFF", help="文字色 RRGGBB")
    ap.add_argument("--position", default="tile", help="tile(平铺) / center(居中)")
    ap.add_argument("--margin", type=int, default=20)
    args = ap.parse_args()

    need_pillow()
    no_overwrite(args.input, args.output)
    img = Image.open(args.input).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font = load_font(args.font_size)

    color = hex_rgb(args.color) + (max(0, min(255, args.opacity)),)
    tw, th = draw.textbbox((0, 0), args.text, font=font)[2:]
    step_x, step_y = tw + 40, th + 40

    if args.position == "center":
        draw.text(((img.width - tw) // 2, (img.height - th) // 2), args.text,
                  font=font, fill=color)
    else:
        y = args.margin
        while y < img.height:
            x = args.margin
            while x < img.width:
                draw.text((x, y), args.text, font=font, fill=color)
                x += step_x
            y += step_y

    out = Image.alpha_composite(img, overlay).convert("RGB")
    save_image(out, args.output, quality=90, optimize=True)
    result(args.output, out)


if __name__ == "__main__":
    main()
