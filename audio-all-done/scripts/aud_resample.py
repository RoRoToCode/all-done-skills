"""aud-resample：采样率 / 声道 / 位深转换。"""
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
    ap.add_argument("--sample-rate", type=int, default=None, help="目标采样率，如 16000 / 44100 / 48000")
    ap.add_argument("--channels", type=int, default=None, choices=[1, 2], help="目标声道数")
    ap.add_argument("--bit-depth", default=None, help="WAV/AIFF 位深：16 / 24 / 32 / float")
    ap.add_argument("--bitrate", default="192k", help="有损输出码率")
    args = ap.parse_args()

    if not any([args.sample_rate, args.channels, args.bit_depth]):
        fail("至少指定 --sample-rate / --channels / --bit-depth 之一。", 2)

    ffmpeg = need_ffmpeg()
    require_input(args.input)
    no_overwrite(args.input, args.output)
    ensure_parent(args.output)

    cmd = [ffmpeg, "-y", "-i", args.input, "-map", "0:a:0"]
    cmd += audio_encode_args(args.output, bitrate=args.bitrate,
                             sample_rate=args.sample_rate,
                             channels=args.channels, bit_depth=args.bit_depth)
    cmd += [args.output]

    rc = run(cmd)
    if rc != 0:
        fail("重采样失败（ffmpeg 退出码 %d）。" % rc)
    info = probe(args.output)
    result(args.output, info.get("duration"), info.get("sample_rate"),
           info.get("channels"))


if __name__ == "__main__":
    main()
