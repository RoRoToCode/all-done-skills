#!/usr/bin/env python3
"""av-extract-audio：从视频/音频抽取音轨，为转写做准备。"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from av_common import ffmpeg_path, need_ffmpeg, no_overwrite, ensure_parent, result, run


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="视频或音频文件")
    ap.add_argument("--output", required=True, help="输出音频，扩展名决定封装/编码")
    ap.add_argument("--codec", default=None, help="显式指定编码器，如 libmp3lame / aac / pcm_s16le")
    ap.add_argument("--sample-rate", type=int, default=None, help="采样率，如 16000")
    ap.add_argument("--mono", action="store_true", help="转单声道")
    ap.add_argument("--bitrate", default="192k", help="有损编码码率，默认 192k")
    args = ap.parse_args()

    ffmpeg = need_ffmpeg()
    no_overwrite(args.input, args.output)
    ensure_parent(args.output)

    ext = os.path.splitext(args.output)[1].lower()
    cmd = [ffmpeg, "-y", "-i", args.input, "-vn"]
    if args.mono:
        cmd += ["-ac", "1"]
    if args.sample_rate:
        cmd += ["-ar", str(args.sample_rate)]
    if args.codec:
        cmd += ["-acodec", args.codec]
    elif ext == ".mp3":
        cmd += ["-acodec", "libmp3lame", "-ab", args.bitrate]
    elif ext == ".m4a":
        cmd += ["-acodec", "aac", "-ab", args.bitrate]
    elif ext == ".aac":
        cmd += ["-acodec", "aac", "-ab", args.bitrate]
    elif ext == ".wav":
        cmd += ["-acodec", "pcm_s16le"]
    else:
        # 未知扩展名：交给 ffmpeg 按封装自行选择
        pass
    cmd += [args.output]

    rc = run(cmd)
    if rc != 0:
        sys.stderr.write("提取音频失败（ffmpeg 退出码 %d）。\n" % rc)
        sys.exit(5)
    result(args.output)


if __name__ == "__main__":
    main()
