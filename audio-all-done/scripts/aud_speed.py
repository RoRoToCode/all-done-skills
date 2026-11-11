"""aud-speed：变速（atempo），可选半音升降调且保持时长。"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aud_common import (need_ffmpeg, no_overwrite, require_input, ensure_parent,
                        run, fail, result, probe, atempo_chain,
                        audio_encode_args)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--speed", type=float, default=1.0, help="速度倍率，0.125-8（默认 1.0）")
    ap.add_argument("--pitch", type=float, default=0.0, help="升/降调半音数，如 +2 / -3（默认 0）")
    ap.add_argument("--sample-rate", type=int, default=None,
                    help="变调需要原始采样率；探测不到时用此参数指定")
    ap.add_argument("--bitrate", default="192k")
    args = ap.parse_args()

    if args.speed <= 0:
        fail("--speed 必须大于 0。", 2)
    if args.speed > 8 or args.speed < 0.125:
        fail("--speed 超出 0.125-8 范围。", 2)
    if abs(args.pitch) > 24:
        fail("--pitch 超出 ±24 半音范围。", 2)

    ffmpeg = need_ffmpeg()
    require_input(args.input)
    no_overwrite(args.input, args.output)
    ensure_parent(args.output)

    if args.pitch:
        sr = probe(args.input).get("sample_rate") or args.sample_rate
        if not sr:
            fail("变调需要知道原始采样率，但 ffprobe 未能探测；请加 --sample-rate 44100。")
        ratio = 2 ** (args.pitch / 12.0)
        chain = "asetrate=%.6f,aresample=%d,%s" % (
            sr * ratio, sr, atempo_chain(args.speed / ratio))
    else:
        chain = atempo_chain(args.speed)

    cmd = [ffmpeg, "-y", "-i", args.input, "-map", "0:a:0",
           "-filter:a", chain]
    cmd += audio_encode_args(args.output, bitrate=args.bitrate)
    cmd += [args.output]

    rc = run(cmd)
    if rc != 0:
        fail("变速失败（ffmpeg 退出码 %d）。" % rc)
    info = probe(args.output)
    result(args.output, info.get("duration"), info.get("sample_rate"),
           info.get("channels"), "speed=%.3g pitch=%+.1f" % (args.speed, args.pitch))


if __name__ == "__main__":
    main()
