"""aud-compress：压缩音频体积（目标码率或目标体积）。"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aud_common import (need_ffmpeg, need_ffprobe, no_overwrite, require_input,
                        ensure_parent, run, fail, result, probe,
                        audio_encode_args, DEFAULT_CODEC, LOSSY_EXTS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True, help="须指向有损格式（mp3 / m4a / ogg / opus）")
    ap.add_argument("--bitrate", default="128k", help="目标码率，默认 128k")
    ap.add_argument("--target-mb", type=float, default=None, help="目标体积(MB)，按输入时长自动算码率")
    ap.add_argument("--codec", default=None, help="显式指定编码器")
    args = ap.parse_args()

    ffmpeg = need_ffmpeg()
    require_input(args.input)
    no_overwrite(args.input, args.output)
    ensure_parent(args.output)

    ext = os.path.splitext(args.output)[1].lower()
    if ext not in LOSSY_EXTS:
        fail("压缩目标须为有损格式（mp3 / m4a / aac / ogg / opus / wma），"
             "当前为 %s；无损格式请用 aud-convert。" % (ext or "无扩展名"), 3)

    bitrate = args.bitrate
    extra = None
    if args.target_mb is not None:
        need_ffprobe()
        dur = probe(args.input).get("duration")
        if not dur:
            fail("无法探测输入时长，无法按目标体积计算码率；请改用 --bitrate。")
        kbit = int(args.target_mb * 1024 * 8 * 0.95 / dur)
        kbit = max(kbit, 32)
        bitrate = "%dk" % kbit
        extra = "目标=%.2fMB → 码率=%s" % (args.target_mb, bitrate)

    cmd = [ffmpeg, "-y", "-i", args.input, "-map", "0:a:0"]
    cmd += audio_encode_args(args.output, codec=args.codec, bitrate=bitrate)
    cmd += [args.output]

    rc = run(cmd)
    if rc != 0:
        fail("压缩失败（ffmpeg 退出码 %d）；本机 ffmpeg 可能未编译 %s 编码器。"
             % (rc, args.codec or DEFAULT_CODEC.get(ext, "对应")), 5)
    info = probe(args.output)
    result(args.output, info.get("duration"), info.get("sample_rate"),
           info.get("channels"), extra)


if __name__ == "__main__":
    main()
