"""vid-subs：把 SRT 字幕烧录（硬字幕）进视频。"""
import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vid_common import filter_path,  need_ffmpeg, no_overwrite, ensure_parent, result, probe


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--subs", required=True, help="SRT 字幕文件路径")
    ap.add_argument("--font-size", type=int, default=24)
    ap.add_argument("--font-color", default="&HFFFFFF", help="ASS 颜色，如 &HFFFFFF（白）")
    ap.add_argument("--outline", type=int, default=2)
    args = ap.parse_args()

    ffmpeg = need_ffmpeg()
    if not os.path.exists(args.subs):
        sys.stderr.write("字幕文件不存在：%s\n" % args.subs)
        sys.exit(3)
    no_overwrite(args.input, args.output)
    ensure_parent(args.output)

    style = ("FontSize=%d,PrimaryColour=%s,Outline=%d,Alignment=2,Bold=1"
             % (args.font_size, args.font_color, args.outline))
    subarg = "subtitles=%s:force_style='%s'" % (filter_path(args.subs), style)

    cmd = [ffmpeg, "-y", "-i", args.input, "-vf", subarg,
           "-c:v", "libx264", "-preset", "medium", "-c:a", "copy", args.output]
    rc = subprocess.run(cmd).returncode
    if rc == 0:
        d, w, h = probe(args.output)
        result(args.output, d, w, h)
    sys.exit(rc)


if __name__ == "__main__":
    main()
