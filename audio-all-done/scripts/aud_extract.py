"""aud-extract：从视频/音频容器里抽出音轨为独立音频文件。"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aud_common import (need_ffmpeg, no_overwrite, require_input, ensure_parent,
                        run, fail, result, probe, audio_encode_args)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="视频或音频文件")
    ap.add_argument("--output", required=True, help="输出音频，扩展名决定封装/编码")
    ap.add_argument("--codec", default=None, help="显式指定编码器，如 libmp3lame / aac / pcm_s16le")
    ap.add_argument("--bitrate", default="192k", help="有损编码码率")
    ap.add_argument("--sample-rate", type=int, default=None, help="重采样，如 16000（喂 ASR 常用）")
    ap.add_argument("--mono", action="store_true", help="转单声道")
    ap.add_argument("--copy", action="store_true",
                    help="直接流拷贝原音轨（不重编码，最快；输出封装须兼容原编码）")
    args = ap.parse_args()

    ffmpeg = need_ffmpeg()
    require_input(args.input)
    no_overwrite(args.input, args.output)
    ensure_parent(args.output)

    cmd = [ffmpeg, "-y", "-i", args.input, "-map", "0:a:0"]
    if args.copy:
        cmd += ["-c", "copy"]
    else:
        cmd += audio_encode_args(args.output, codec=args.codec,
                                 bitrate=args.bitrate,
                                 sample_rate=args.sample_rate,
                                 channels=1 if args.mono else None)
    cmd += [args.output]

    rc = run(cmd)
    if rc != 0:
        fail("提取音轨失败（ffmpeg 退出码 %d）；用 --copy 时请确认输出封装兼容原编码。"
             % rc)
    info = probe(args.output)
    result(args.output, info.get("duration"), info.get("sample_rate"),
           info.get("channels"))


if __name__ == "__main__":
    main()
