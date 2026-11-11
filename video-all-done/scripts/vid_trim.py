"""vid-trim：按时间截取片段。"""
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
    ap.add_argument("--start", default="0", help="开始时间，如 00:00:05 或 5 / 5.0")
    ap.add_argument("--end", default=None, help="结束时间")
    ap.add_argument("--duration", default=None, help="截取时长（与 --end 二选一）")
    ap.add_argument("--reencode", action="store_true", help="重编码（非关键帧也精准）")
    args = ap.parse_args()

    ffmpeg = need_ffmpeg()
    no_overwrite(args.input, args.output)
    ensure_parent(args.output)

    cmd = [ffmpeg, "-y", "-ss", str(args.start)]
    if args.end:
        cmd += ["-to", str(args.end)]
    elif args.duration:
        cmd += ["-t", str(args.duration)]
    cmd += ["-i", args.input]
    if args.reencode:
        cmd += ["-c:v", "libx264", "-c:a", "aac"]
    else:
        cmd += ["-c", "copy"]
    cmd += [args.output]

    rc = subprocess.run(cmd).returncode
    if rc == 0:
        d, w, h = probe(args.output)
        result(args.output, d, w, h)
    sys.exit(rc)


if __name__ == "__main__":
    main()
