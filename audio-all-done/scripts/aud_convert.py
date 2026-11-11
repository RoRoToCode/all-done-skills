"""aud-convert：音频格式互转（mp3 / wav / flac / m4a / aac / ogg / opus / wma）。"""
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
    ap.add_argument("--codec", default=None, help="显式指定编码器，如 libmp3lame / aac / flac / pcm_s16le")
    ap.add_argument("--bitrate", default="192k", help="有损编码码率，默认 192k")
    ap.add_argument("--sample-rate", type=int, default=None, help="重采样，如 44100 / 48000 / 16000")
    ap.add_argument("--channels", type=int, default=None, help="声道数，1=单声道 2=立体声")
    ap.add_argument("--bit-depth", default=None, help="WAV/AIFF 位深：16 / 24 / 32 / float")
    ap.add_argument("--quality", type=float, default=None, help="OGG Vorbis 质量 0-10（与 --bitrate 二选一）")
    args = ap.parse_args()

    ffmpeg = need_ffmpeg()
    require_input(args.input)
    no_overwrite(args.input, args.output)
    ensure_parent(args.output)

    ext = os.path.splitext(args.output)[1].lower()
    if not ext:
        fail("输出缺少扩展名，无法确定编码格式：%s" % args.output, 3)

    br = None if args.quality is not None else args.bitrate
    cmd = [ffmpeg, "-y", "-i", args.input, "-map", "0:a:0"]
    cmd += audio_encode_args(args.output, codec=args.codec, bitrate=br,
                             sample_rate=args.sample_rate,
                             channels=args.channels, bit_depth=args.bit_depth)
    if args.quality is not None:
        cmd += ["-q:a", "%.6g" % args.quality]
    cmd += [args.output]

    rc = run(cmd)
    if rc != 0:
        fail("格式转换失败（ffmpeg 退出码 %d）；本机 ffmpeg 可能未编译该编码器，"
             "可换 --codec 或改输出扩展名。" % rc)
    info = probe(args.output)
    result(args.output, info.get("duration"), info.get("sample_rate"),
           info.get("channels"))


if __name__ == "__main__":
    main()
