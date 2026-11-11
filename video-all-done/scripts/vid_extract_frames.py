"""vid-extract-frames：抽帧 / 截图。"""
import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vid_common import need_ffmpeg, no_overwrite, ensure_parent, result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True, help="单帧路径(out.png)或序列(out_%%04d.png)")
    ap.add_argument("--at", default=None, help="单帧时间点，如 00:00:03")
    ap.add_argument("--every", type=float, default=None, help="每隔 N 秒抽一帧")
    ap.add_argument("--fps", type=float, default=None, help="按帧率抽帧")
    ap.add_argument("--width", type=int, default=None, help="输出帧宽度（保持比例）")
    args = ap.parse_args()

    ffmpeg = need_ffmpeg()

    # --output 给目录（或以路径分隔符结尾、没有扩展名）时，自动补序列模板。
    # ffmpeg 不认目录当输出目标，会报 "Unable to choose an output format"。
    out = args.output
    if os.path.isdir(out) or not os.path.splitext(out)[1]:
        os.makedirs(out, exist_ok=True)
        out = os.path.join(out, "frame_%04d.png")

    no_overwrite(args.input, out)
    ensure_parent(out)

    cmd = [ffmpeg, "-y"]
    vf = []
    if args.width:
        vf.append("scale=%d:-2" % args.width)
    if args.at is not None:
        cmd += ["-ss", str(args.at)]
    if args.every is not None:
        vf.append("fps=1/%f" % args.every)
    elif args.fps is not None:
        vf.append("fps=%s" % args.fps)
    cmd += ["-i", args.input]
    if vf:
        cmd += ["-vf", ",".join(vf)]
    if args.at is not None and not (args.every or args.fps):
        cmd += ["-frames:v", "1"]
    cmd += [out]

    rc = subprocess.run(cmd).returncode
    if rc == 0:
        if os.path.exists(out):
            result(out)
        else:
            print("已抽帧至 %s 所在目录。" % os.path.dirname(out))
    sys.exit(rc)


if __name__ == "__main__":
    main()
