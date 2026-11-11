"""vid-gif：视频转 GIF / GIF 转视频。"""
import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vid_common import need_ffmpeg, no_overwrite, ensure_parent, result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--fps", type=int, default=15)
    ap.add_argument("--width", type=int, default=480)
    ap.add_argument("--reverse", action="store_true", help="GIF 转视频（输入为 .gif）")
    ap.add_argument("--start", default="0")
    ap.add_argument("--duration", default=None)
    args = ap.parse_args()

    ffmpeg = need_ffmpeg()
    no_overwrite(args.input, args.output)
    ensure_parent(args.output)

    if args.reverse:
        cmd = [ffmpeg, "-y", "-i", args.input, args.output]
        rc = subprocess.run(cmd).returncode
    else:
        cmd = [ffmpeg, "-y"]
        if args.duration:
            cmd += ["-ss", str(args.start), "-t", str(args.duration)]
        else:
            cmd += ["-ss", str(args.start)]
        cmd += ["-i", args.input]
        vf = ("fps=%d,scale=%d:-1:flags=lanczos,split[s0][s1];"
              "[s0]palettegen[p];[s1][p]paletteuse" % (args.fps, args.width))
        cmd += ["-vf", vf, args.output]
        rc = subprocess.run(cmd).returncode

    if rc == 0:
        result(args.output)
    sys.exit(rc)


if __name__ == "__main__":
    main()
