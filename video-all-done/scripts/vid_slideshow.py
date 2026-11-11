"""vid-slideshow：图片序列 + 可选背景音乐 -> 视频（支持淡入淡出与缓慢推近）。"""
import argparse
import glob
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vid_common import (need_ffmpeg, need_pillow, no_overwrite, ensure_parent,
                        result, probe, cover_fit, assemble)

IMG_EXT = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff")


def collect(images, image_dir):
    files = []
    if images:
        for part in images.split(","):
            part = part.strip()
            if not part:
                continue
            # glob 对已存在的目录会原样返回该目录，这里只保留文件
            m = [x for x in glob.glob(part) if os.path.isfile(x)]
            if m:
                files += sorted(m)
            elif os.path.isdir(part):
                # 直接给目录也认，省得被当成单张图片塞进后续流程
                for f in sorted(os.listdir(part)):
                    if f.lower().endswith(IMG_EXT):
                        files.append(os.path.join(part, f))
            elif os.path.exists(part):
                files.append(part)
    if image_dir:
        for f in sorted(os.listdir(image_dir)):
            if f.lower().endswith(IMG_EXT):
                files.append(os.path.join(image_dir, f))
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", default=None, help="逗号分隔图片路径或通配符")
    ap.add_argument("--image-dir", default=None, help="图片目录（按名排序）")
    ap.add_argument("--output", required=True)
    ap.add_argument("--duration", type=float, default=3.0, help="每页时长(秒)")
    ap.add_argument("--transition", default="fade", choices=["fade", "none"])
    ap.add_argument("--fade-dur", type=float, default=0.6)
    ap.add_argument("--resolution", default="1280x720")
    ap.add_argument("--fps", type=int, default=25)
    ap.add_argument("--audio", default=None)
    ap.add_argument("--kenburns", action="store_true", help="缓慢推近（Ken Burns）")
    ap.add_argument("--bg", default="#000000", help="填充底色 RRGGBB")
    args = ap.parse_args()

    need_pillow()
    ffmpeg = need_ffmpeg()
    if args.audio:
        no_overwrite(args.audio, args.output)
    ensure_parent(args.output)

    files = collect(args.images, args.image_dir)
    if len(files) < 1:
        sys.stderr.write("未找到任何图片。\n")
        sys.exit(3)

    try:
        W, H = (int(x) for x in args.resolution.lower().split("x"))
    except Exception:
        sys.stderr.write("分辨率格式应为 宽x高，如 1280x720。\n")
        sys.exit(2)

    tmp = tempfile.mkdtemp(prefix="vidslide_")
    try:
        pngs = []
        for i, f in enumerate(files):
            dst = os.path.join(tmp, "s_%03d.png" % i)
            cover_fit(f, dst, W, H, args.bg)
            pngs.append(dst)
        assemble(pngs, args.output, args.duration, args.transition,
                 args.fade_dur, args.fps, args.audio, args.kenburns, W, H, ffmpeg)
    finally:
        for f in os.listdir(tmp):
            try:
                os.unlink(os.path.join(tmp, f))
            except Exception:
                pass
        try:
            os.rmdir(tmp)
        except Exception:
            pass

    if os.path.exists(args.output):
        d, w, h = probe(args.output)
        result(args.output, d, w, h)
    sys.exit(0)


if __name__ == "__main__":
    main()
