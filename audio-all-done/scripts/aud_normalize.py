"""aud-normalize：EBU R128 响度归一化（loudnorm），单遍或精确两遍。"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aud_common import (need_ffmpeg, no_overwrite, require_input, ensure_parent,
                        run, result, probe, audio_encode_args)


def measure(ffmpeg, inp, base):
    """返回 loudnorm 第一遍的测量值 dict；解析失败返回 None。"""
    cmd = [ffmpeg, "-hide_banner", "-i", inp, "-map", "0:a:0",
           "-af", base + ":print_format=json", "-f", "null", "-"]
    rc, _, err = run(cmd, capture=True)
    if rc != 0:
        return None
    m = re.search(r"\{\s*\"input_i\".*?\}", err, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--target-lufs", type=float, default=-16.0,
                    help="目标综合响度 LUFS，播客常 -16，流媒体常 -14（默认 -16）")
    ap.add_argument("--tp", type=float, default=-1.5, help="真峰值上限 dBTP（默认 -1.5）")
    ap.add_argument("--lra", type=float, default=11.0, help="响度范围 LRA（默认 11）")
    ap.add_argument("--two-pass", action="store_true", help="先测量再修正，结果更精确（耗时约 2 倍）")
    ap.add_argument("--bitrate", default="192k")
    args = ap.parse_args()

    ffmpeg = need_ffmpeg()
    require_input(args.input)
    no_overwrite(args.input, args.output)
    ensure_parent(args.output)

    base = "loudnorm=I=%.1f:TP=%.1f:LRA=%.1f" % (
        args.target_lufs, args.tp, args.lra)
    flt = base + ":linear=true"
    note = "目标=%.1f LUFS（单遍动态）" % args.target_lufs

    if args.two_pass:
        m = measure(ffmpeg, args.input, base)
        if m:
            flt = ("%s:measured_I=%.2f:measured_TP=%.2f:measured_LRA=%.2f:"
                   "measured_thresh=%.2f:offset=%.2f:linear=true:print_format=summary"
                   % (base, float(m["input_i"]), float(m["input_tp"]),
                      float(m["input_lra"]), float(m["input_thresh"]),
                      float(m["target_offset"])))
            note = "目标=%.1f LUFS（两遍精确）" % args.target_lufs
        else:
            sys.stderr.write("提示：两遍测量未能解析 loudnorm JSON，已降级为单遍动态归一化。\n")

    cmd = [ffmpeg, "-y", "-i", args.input, "-map", "0:a:0", "-af", flt]
    cmd += audio_encode_args(args.output, bitrate=args.bitrate)
    cmd += [args.output]

    rc = run(cmd)
    if rc != 0:
        sys.stderr.write("响度归一化失败（ffmpeg 退出码 %d）；"
                         "请确认本机 ffmpeg 编译了 loudnorm 滤镜。\n" % rc)
        sys.exit(5)
    info = probe(args.output)
    result(args.output, info.get("duration"), info.get("sample_rate"),
           info.get("channels"), note)


if __name__ == "__main__":
    main()
