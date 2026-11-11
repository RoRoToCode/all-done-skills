"""aud-trim：按开始/结束时间截取音频片段。"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aud_common import (need_ffmpeg, no_overwrite, require_input, ensure_parent,
                        run, fail, result, probe, parse_time, audio_encode_args)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--start", default="0", help="开始时间，如 00:00:05 或 5 / 5.0")
    ap.add_argument("--end", default=None, help="结束时间（绝对位置，如 00:00:15）")
    ap.add_argument("--duration", default=None, help="截取时长（与 --end 二选一）")
    ap.add_argument("--copy", action="store_true", help="流拷贝不重编码（最快，但 MP3 可能有毫秒级偏移）")
    ap.add_argument("--accurate", action="store_true", help="输出侧定位，非关键帧也精准（稍慢）")
    ap.add_argument("--bitrate", default="192k")
    args = ap.parse_args()

    start = parse_time(args.start)
    if start is None or start < 0:
        fail("--start 时间格式无效：%s" % args.start, 2)
    if args.end and args.duration:
        fail("--end 与 --duration 只能给一个。", 2)
    seg = None
    if args.end:
        end = parse_time(args.end)
        if end is None or end <= start:
            fail("--end 必须大于 --start，且格式有效。", 2)
        seg = end - start
    elif args.duration:
        seg = parse_time(args.duration)
        if seg is None or seg <= 0:
            fail("--duration 必须为正数。", 2)

    ffmpeg = need_ffmpeg()
    require_input(args.input)
    no_overwrite(args.input, args.output)
    ensure_parent(args.output)

    if args.accurate:
        cmd = [ffmpeg, "-y", "-i", args.input, "-ss", "%.6g" % start]
    else:
        cmd = [ffmpeg, "-y", "-ss", "%.6g" % start, "-i", args.input]
    cmd += ["-map", "0:a:0"]
    if seg is not None:
        cmd += ["-t", "%.6g" % seg]
    if args.copy:
        cmd += ["-c", "copy"]
    else:
        cmd += audio_encode_args(args.output, bitrate=args.bitrate)
    cmd += [args.output]

    rc = run(cmd)
    if rc != 0:
        fail("截取失败（ffmpeg 退出码 %d）。" % rc)
    info = probe(args.output)
    result(args.output, info.get("duration"), info.get("sample_rate"),
           info.get("channels"))


if __name__ == "__main__":
    main()
