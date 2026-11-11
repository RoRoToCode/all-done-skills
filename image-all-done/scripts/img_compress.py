"""img-compress：压缩图片体积（有损按质量/目标体积，PNG 按优化）。"""
import argparse
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from img_common import need_pillow, no_overwrite, save_image, result


def _lossy_bytes(img, fmt, quality):
    buf = io.BytesIO()
    if fmt == "jpg":
        img.convert("RGB").save(buf, format="JPEG", quality=quality, optimize=True)
    else:
        img.save(buf, format="WEBP", quality=quality)
    return buf.getvalue()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--quality", type=int, default=75, help="jpg/webp 质量 1-100")
    ap.add_argument("--target-kb", type=float, default=None, help="目标体积(KB)，自动选质量")
    args = ap.parse_args()

    Image = need_pillow()
    no_overwrite(args.input, args.output)
    img = Image.open(args.input)
    fmt = os.path.splitext(args.output)[1].lower().lstrip(".")
    if fmt not in ("jpg", "jpeg", "webp"):
        # 非有损格式：只做优化（PNG 等）
        save_image(img, args.output, optimize=True)
        result(args.output, img)
        return

    quality = args.quality
    if args.target_kb:
        lo, hi = 10, 95
        for _ in range(12):
            quality = (lo + hi) // 2
            kb = len(_lossy_bytes(img, fmt, quality)) / 1024.0
            if kb > args.target_kb:
                lo = quality + 1
            else:
                hi = quality - 1
    data = _lossy_bytes(img, fmt, quality)
    with open(args.output, "wb") as f:
        f.write(data)
    size = os.path.getsize(args.output)
    print("已保存 %s  格式=%s 质量=%d 体积=%d 字节（原 %.1f KB）"
          % (args.output, fmt.upper(), quality, size,
             os.path.getsize(args.input) / 1024.0))
    if args.target_kb and size / 1024.0 > args.target_kb:
        print("提示：已逼近质量下限仍未达目标体积，可换格式或接受当前结果。")


if __name__ == "__main__":
    main()
