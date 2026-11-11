"""vid-rotate：旋转 / 翻转。"""
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
    ap.add_argument("--angle", type=int, default=0, help="顺时针角度（90 的倍数最稳）")
    ap.add_argument("--flip", choices=["h", "v"], default=None, help="水平/垂直翻转")
    args = ap.parse_args()

    ffmpeg = need_ffmpeg()
    no_overwrite(args.input, args.output)
    ensure_parent(args.output)

    if args.angle % 90 != 0:
        sys.stderr.write("非 90 倍数角度易变形，建议用 90 倍数。\n")
        sys.exit(2)

    vf = []
    a = args.angle % 360
    if a == 90:
        vf.append("transpose=1")
    elif a == 180:
        vf.append("transpose=1,transpose=1")
    elif a == 270:
        vf.append("transpose=2")
    if args.flip == "h":
        vf.append("hflip")
    elif args.flip == "v":
        vf.append("vflip")
    if not vf:
        sys.stderr.write("未指定旋转或翻转。\n")
        sys.exit(2)

    cmd = [ffmpeg, "-y", "-i", args.input, "-vf", ",".join(vf),
           "-c:v", "libx264", "-preset", "medium", "-c:a", "copy", args.output]
    rc = subprocess.run(cmd).returncode
    if rc == 0:
        d, w, h = probe(args.output)
        result(args.output, d, w, h)
    sys.exit(rc)


if __name__ == "__main__":
    main()
