"""aud-fade：片头淡入 / 片尾淡出。"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aud_common import (need_ffmpeg, need_ffprobe, no_overwrite, require_input,
                        ensure_parent, run, fail, result, probe, parse_time,
                        audio_encode_args)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--fade-in", type=float, default=0.0, help="淡入秒数（默认 0）")
    ap.add_argument("--fade-out", type=float, default=0.0, help="淡出秒数（默认 0）")
    ap.add_argument("--curve", default="tri",
                    help="曲线 tri/qsin/hsin/esin/log/par/quad（默认 tri）")
    ap.add_argument("--duration", default=None,
                    help="探测不到时长时手动指定总时长（秒或 00:00:30）")
    ap.add_argument("--bitrate", default="192k")
    args = ap.parse_args()

    if args.fade_in < 0 or args.fade_out < 0:
        fail("淡入/淡出时长不得为负。", 2)
    if args.fade_in == 0 and args.fade_out == 0:
        fail("请至少指定 --fade-in 或 --fade-out 之一。", 2)

    ffmpeg = need_ffmpeg()
    require_input(args.input)
    no_overwrite(args.input, args.output)
    ensure_parent(args.output)

    dur = probe(args.input).get("duration")
    if not dur:
        dur = parse_time(args.duration)
    if args.fade_out > 0 and not dur:
        need_ffprobe()
        fail("淡出需要总时长，但无法探测；请用 --duration 指定。", 5)
    if dur and args.fade_in + args.fade_out > dur:
        fail("淡入 %.2f + 淡出 %.2f 超过音频总时长 %.2f 秒。" %
             (args.fade_in, args.fade_out, dur), 2)

    parts = []
    if args.fade_in > 0:
        parts.append("afade=t=in:st=0:d=%.3f:curve=%s" % (args.fade_in, args.curve))
    if args.fade_out > 0:
        parts.append("afade=t=out:st=%.3f:d=%.3f:curve=%s" %
                     (max(dur - args.fade_out, 0), args.fade_out, args.curve))
    flt = ",".join(parts)

    cmd = [ffmpeg, "-y", "-i", args.input, "-map", "0:a:0", "-af", flt]
    cmd += audio_encode_args(args.output, bitrate=args.bitrate)
    cmd += [args.output]

    rc = run(cmd)
    if rc != 0:
        fail("淡入淡出失败（ffmpeg 退出码 %d）。" % rc)
    info = probe(args.output)
    result(args.output, info.get("duration"), info.get("sample_rate"),
           info.get("channels"),
           "淡入=%.2fs 淡出=%.2fs" % (args.fade_in, args.fade_out))


if __name__ == "__main__":
    main()
