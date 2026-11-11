"""vid-convert：视频格式互转（mp4/webm/mov/mkv/avi）。"""
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
    ap.add_argument("--vcodec", default="libx264", help="视频编码器，如 libx264/libvp9/libx265")
    ap.add_argument("--acodec", default="aac", help="音频编码器，如 aac/copy")
    ap.add_argument("--crf", type=int, default=None, help="质量 0-51（libx264/libx265 生效）")
    ap.add_argument("--preset", default="medium")
    args = ap.parse_args()

    ffmpeg = need_ffmpeg()
    no_overwrite(args.input, args.output)
    ensure_parent(args.output)

    cmd = [ffmpeg, "-y", "-i", args.input]
    if args.crf is not None:
        cmd += ["-crf", str(args.crf), "-preset", args.preset]
    cmd += ["-c:v", args.vcodec, "-c:a", args.acodec, args.output]

    rc = subprocess.run(cmd).returncode
    if rc == 0:
        d, w, h = probe(args.output)
        result(args.output, d, w, h)
    sys.exit(rc)


if __name__ == "__main__":
    main()
