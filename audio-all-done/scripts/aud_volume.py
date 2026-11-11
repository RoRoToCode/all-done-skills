"""aud-volume：音量增益（dB 或倍数），可选限幅器防削波。"""
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
    ap.add_argument("--gain-db", type=float, default=None, help="按分贝增减，如 +6 / -3")
    ap.add_argument("--gain", type=float, default=None, help="按倍数增减，如 1.5 / 0.5")
    ap.add_argument("--limiter", action="store_true", help="叠加 alimiter 限幅，防止放大后削波")
    ap.add_argument("--bitrate", default="192k")
    args = ap.parse_args()

    if args.gain_db is not None and args.gain is not None:
        fail("--gain-db 与 --gain 只能给一个。", 2)
    if args.gain_db is None and args.gain is None:
        fail("请指定 --gain-db 或 --gain。", 2)
    if args.gain is not None and args.gain <= 0:
        fail("--gain 必须大于 0（想静音请用 0.0001）。", 2)

    if args.gain_db is not None:
        flt = "volume=%.3fdB" % args.gain_db
        label = "%+.1f dB" % args.gain_db
    else:
        flt = "volume=%.6f" % args.gain
        label = "x%.3f" % args.gain
    if args.limiter:
        flt += ",alimiter=limit=1"

    ffmpeg = need_ffmpeg()
    require_input(args.input)
    no_overwrite(args.input, args.output)
    ensure_parent(args.output)

    cmd = [ffmpeg, "-y", "-i", args.input, "-map", "0:a:0", "-af", flt]
    cmd += audio_encode_args(args.output, bitrate=args.bitrate)
    cmd += [args.output]

    rc = run(cmd)
    if rc != 0:
        fail("音量调整失败（ffmpeg 退出码 %d）。" % rc)
    info = probe(args.output)
    result(args.output, info.get("duration"), info.get("sample_rate"),
           info.get("channels"), "增益=%s%s" % (label, " + 限幅" if args.limiter else ""))


if __name__ == "__main__":
    main()
