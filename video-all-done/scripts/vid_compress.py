"""vid-compress：压缩视频体积（CRF 或目标体积）。"""
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
    ap.add_argument("--crf", type=int, default=28, help="质量 0-51，越大越小（默认 28）")
    ap.add_argument("--target-mb", type=float, default=None, help="目标体积(MB)，自动算码率")
    ap.add_argument("--preset", default="medium")
    args = ap.parse_args()

    ffmpeg = need_ffmpeg()
    no_overwrite(args.input, args.output)
    ensure_parent(args.output)

    cmd = [ffmpeg, "-y", "-i", args.input]
    if args.target_mb:
        dur, _, _ = probe(args.input)
        if not dur:
            sys.stderr.write("无法探测时长，请改用 --crf。\n")
            sys.exit(5)
        # 视频约占 90%，其余留给音频
        video_kbit = int((args.target_mb * 1024 * 8 * 0.9) / dur / 1000)
        video_kbit = max(video_kbit, 50)
        cmd += ["-b:v", "%dk" % video_kbit,
                "-maxrate", "%dk" % int(video_kbit * 1.5),
                "-bufsize", "%dk" % (video_kbit * 2)]
    else:
        cmd += ["-crf", str(args.crf), "-preset", args.preset]
    cmd += ["-c:v", "libx264", "-c:a", "aac", args.output]

    rc = subprocess.run(cmd).returncode
    if rc == 0:
        d, w, h = probe(args.output)
        result(args.output, d, w, h)
    sys.exit(rc)


if __name__ == "__main__":
    main()
