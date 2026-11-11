"""aud-mix：主音轨叠加背景音乐（双轨混音）。"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aud_common import (need_ffmpeg, no_overwrite, require_input, ensure_parent,
                        run, fail, result, probe, audio_encode_args)


def build_filter(v0, v1, normalize, limiter):
    head = ("[0:a]volume=%.4f[a0];[1:a]volume=%.4f[a1];"
            "[a0][a1]amix=inputs=2:duration=first" % (v0, v1))
    if normalize:
        head += ":normalize=0"
    head += "[a]"
    if limiter:
        head += ";[a]alimiter=limit=1[aout]"
        return head, "[aout]"
    return head, "[a]"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="主音轨（决定成品时长）")
    ap.add_argument("--mix", required=True, help="要叠加的第二轨，通常是 BGM")
    ap.add_argument("--output", required=True)
    ap.add_argument("--main-volume", type=float, default=1.0, help="主音轨音量倍数（默认 1.0）")
    ap.add_argument("--mix-volume", type=float, default=0.3, help="第二轨音量倍数（默认 0.3）")
    ap.add_argument("--loop", action="store_true", help="第二轨比主轨短时循环播放")
    ap.add_argument("--no-limiter", action="store_true", help="关闭输出限幅")
    ap.add_argument("--bitrate", default="192k")
    args = ap.parse_args()

    if args.main_volume < 0 or args.mix_volume < 0:
        fail("音量倍数不得为负。", 2)

    ffmpeg = need_ffmpeg()
    require_input(args.input)
    require_input(args.mix)
    no_overwrite(args.input, args.output)
    no_overwrite(args.mix, args.output)
    ensure_parent(args.output)

    cmd = [ffmpeg, "-y", "-i", args.input]
    if args.loop:
        cmd += ["-stream_loop", "-1"]
    cmd += ["-i", args.mix]

    flt, label = build_filter(args.main_volume, args.mix_volume,
                              True, not args.no_limiter)
    cmd += ["-filter_complex", flt, "-map", label]
    cmd += audio_encode_args(args.output, bitrate=args.bitrate)
    cmd += [args.output]

    rc = run(cmd)
    if rc != 0:
        # 旧版 ffmpeg 的 amix 不支持 normalize=0，去掉后重试一次
        sys.stderr.write("提示：混音滤镜首轮失败，尝试兼容旧版 ffmpeg（去掉 normalize=0）。\n")
        flt, label = build_filter(args.main_volume, args.mix_volume,
                                  False, not args.no_limiter)
        cmd = [ffmpeg, "-y", "-i", args.input]
        if args.loop:
            cmd += ["-stream_loop", "-1"]
        cmd += ["-i", args.mix, "-filter_complex", flt, "-map", label]
        cmd += audio_encode_args(args.output, bitrate=args.bitrate)
        cmd += [args.output]
        rc = run(cmd)
    if rc != 0:
        sys.stderr.write("混音失败（ffmpeg 退出码 %d）。\n" % rc)
        sys.exit(5)

    info = probe(args.output)
    result(args.output, info.get("duration"), info.get("sample_rate"),
           info.get("channels"),
           "主轨=x%.2f 叠加=x%.2f%s" % (
               args.main_volume, args.mix_volume, " (循环)" if args.loop else ""))


if __name__ == "__main__":
    main()
