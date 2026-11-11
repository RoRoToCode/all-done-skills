"""aud-denoise：轻量降噪（afftdn 谱降噪 + 可选高通/低通）。

注意：这是滤波器级降噪，不是 AI 人声分离或音频修复；
能压低稳态底噪与低频嗡声，无法去掉人声、回声或严重失真。
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aud_common import (need_ffmpeg, no_overwrite, require_input, ensure_parent,
                        run, fail, result, probe, audio_encode_args)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--strength", type=int, default=50,
                    help="降噪强度 0-100（默认 50；过大易损人声细节）")
    ap.add_argument("--highpass", type=int, default=80,
                    help="高通截止 Hz，压掉低频嗡声；0 = 关闭（默认 80）")
    ap.add_argument("--lowpass", type=int, default=0,
                    help="低通截止 Hz，压掉高频嘶声；0 = 关闭")
    ap.add_argument("--bitrate", default="192k")
    args = ap.parse_args()

    if not 0 <= args.strength <= 100:
        fail("--strength 须在 0-100。", 2)

    ffmpeg = need_ffmpeg()
    require_input(args.input)
    no_overwrite(args.input, args.output)
    ensure_parent(args.output)

    nf = -20.0 - args.strength * 0.30      # 0 -> -20, 50 -> -35, 100 -> -50
    parts = []
    if args.highpass > 0:
        parts.append("highpass=f=%d" % args.highpass)
    parts.append("afftdn=nf=%.1f" % nf)
    if args.lowpass > 0:
        parts.append("lowpass=f=%d" % args.lowpass)
    flt = ",".join(parts)

    cmd = [ffmpeg, "-y", "-i", args.input, "-map", "0:a:0", "-af", flt]
    cmd += audio_encode_args(args.output, bitrate=args.bitrate)
    cmd += [args.output]

    rc = run(cmd)
    if rc != 0:
        fail("降噪失败（ffmpeg 退出码 %d）；请确认本机 ffmpeg 编译了 afftdn 滤镜。" % rc)
    info = probe(args.output)
    result(args.output, info.get("duration"), info.get("sample_rate"),
           info.get("channels"), "强度=%d 高通=%dHz" % (args.strength, args.highpass))


if __name__ == "__main__":
    main()
