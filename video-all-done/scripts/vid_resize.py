"""vid-resize：改分辨率 / 比例。"""
import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vid_common import need_ffmpeg, no_overwrite, ensure_parent, result, probe


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--width", type=int, default=None)
    ap.add_argument("--height", type=int, default=None)
    ap.add_argument("--scale", type=float, default=None, help="整体缩放百分比，如 50")
    ap.add_argument("--no-keep-ratio", action="store_true", help="不保持比例（需同时给宽高）")
    args = ap.parse_args()

    ffmpeg = need_ffmpeg()
    no_overwrite(args.input, args.output)
    ensure_parent(args.output)

    if args.scale:
        vf = ("scale='trunc(iw*%f/100/2)*2':'trunc(ih*%f/100/2)*2'"
              % (args.scale, args.scale))
    elif args.width and args.height and args.no_keep_ratio:
        vf = "scale=%d:%d" % (args.width, args.height)
    elif args.width and args.height:
        vf = ("scale=%d:%d:force_original_aspect_ratio=decrease,"
              "pad=%d:%d:(ow-iw)/2:(oh-ih)/2:(0x000000)"
              % (args.width, args.height, args.width, args.height))
    elif args.width:
        vf = "scale=%d:-2" % args.width
    elif args.height:
        vf = "scale=-2:%d" % args.height
    else:
        sys.stderr.write("请至少提供 --width / --height / --scale 之一。\n")
        sys.exit(2)

    cmd = [ffmpeg, "-y", "-i", args.input, "-vf", vf,
           "-c:v", "libx264", "-preset", "medium", "-c:a", "copy", args.output]
    rc = subprocess.run(cmd).returncode
    if rc == 0:
        d, w, h = probe(args.output)
        result(args.output, d, w, h)
    sys.exit(rc)


if __name__ == "__main__":
    main()
