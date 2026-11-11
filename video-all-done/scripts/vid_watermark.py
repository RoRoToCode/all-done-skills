"""vid-watermark：文字或图片水印（文字用 Pillow 渲染，保证中文不乱码）。"""
import argparse
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vid_common import (need_ffmpeg, need_pillow, no_overwrite, ensure_parent,
                        result, probe, load_pil_font, hex_rgb)

# overlay 的位置表达式：W/H 是主画面宽高，w/h 是水印宽高。
# 老教程里的 tw/th 在 ffmpeg 7 起已被移除，用了会直接报
# "Undefined constant ... in 'tw-10'"，所以这里统一用 w/h。
POS = {
    "topleft": "10:10",
    "topright": "W-w-10:10",
    "bottomleft": "10:H-h-10",
    "bottomright": "W-w-10:H-h-10",
    "center": "(W-w)/2:(H-h)/2",
}


def render_text_png(text, size, color, opacity, out):
    Image = need_pillow()
    from PIL import ImageDraw
    font = load_pil_font(size)
    dummy = Image.new("RGBA", (1, 1))
    d = ImageDraw.Draw(dummy)
    lines = text.split("\n")
    maxw = max([d.textlength(ln, font=font) for ln in lines] or [10])
    pad = int(size * 0.4)
    W = int(maxw) + pad * 2
    H = int(size * 1.3 * len(lines)) + pad
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dd = ImageDraw.Draw(img)
    y = pad // 2
    for ln in lines:
        dd.text((pad, y), ln, font=font, fill=color + (opacity,))
        y += int(size * 1.3)
    img.save(out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--text", default=None)
    ap.add_argument("--logo", default=None, help="水印图片路径（PNG 优先带透明）")
    ap.add_argument("--position", default="bottomright", choices=list(POS))
    ap.add_argument("--opacity", type=int, default=180, help="文字透明度 0-255")
    ap.add_argument("--size", type=int, default=36, help="文字字号 / 图片目标高度(px)")
    ap.add_argument("--color", default="FFFFFF", help="文字颜色 RRGGBB")
    args = ap.parse_args()

    ffmpeg = need_ffmpeg()
    no_overwrite(args.input, args.output)
    ensure_parent(args.output)

    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    tmp.close()
    try:
        if args.text:
            render_text_png(args.text, args.size, hex_rgb(args.color),
                            args.opacity, tmp.name)
            overlay = tmp.name
            filt = "[0][1]overlay=%s[vout]" % POS[args.position]
        elif args.logo:
            overlay = args.logo
            filt = "[1]scale=-1:%d[wm];[0][wm]overlay=%s[vout]" % (args.size, POS[args.position])
        else:
            sys.stderr.write("请指定 --text 或 --logo。\n")
            sys.exit(2)

        # -filter_complex 会关闭默认流映射，必须显式指定视频与音频，否则音轨丢失。
        cmd = [ffmpeg, "-y", "-i", args.input, "-i", overlay,
               "-filter_complex", filt,
               "-map", "[vout]", "-map", "0:a?",
               "-c:v", "libx264", "-preset", "medium", "-c:a", "copy", args.output]
        rc = subprocess.run(cmd).returncode
    finally:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass

    if rc == 0:
        d, w, h = probe(args.output)
        result(args.output, d, w, h)
    sys.exit(rc)


if __name__ == "__main__":
    main()
