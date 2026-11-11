"""aud-split：按静音检测或固定时长把音频切成多段，输出到目录。"""
import argparse
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aud_common import (need_ffmpeg, need_ffprobe, require_input, ensure_dir,
                        run, fail, probe, hms, audio_encode_args,
                        DEFAULT_CODEC, unique_path)


def detect_silences(ffmpeg, inp, noise_db, min_silence):
    """返回静音区间 [(start, end), ...]，来自 silencedetect 的 stderr。"""
    af = "silencedetect=noise=%s:d=%s" % (noise_db, min_silence)
    cmd = [ffmpeg, "-hide_banner", "-i", inp, "-map", "0:a:0",
           "-af", af, "-f", "null", "-"]
    rc, _, err = run(cmd, capture=True)
    if rc != 0:
        fail("静音检测失败（ffmpeg 退出码 %d）。" % rc)
    starts = [float(x) for x in re.findall(r"silence_start:\s*([0-9.]+)", err)]
    ends = [float(x) for x in re.findall(r"silence_end:\s*([0-9.]+)", err)]
    return list(zip(starts, ends))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True, help="输出目录（每片一个文件）")
    ap.add_argument("--mode", choices=["silence", "equal"], default="silence")
    ap.add_argument("--noise-db", default="-35dB", help="静音判定阈值，如 -35dB / -40dB")
    ap.add_argument("--min-silence", type=float, default=0.4, help="最短静音时长(秒)")
    ap.add_argument("--min-length", type=float, default=1.0, help="丢弃短于此秒数的片段")
    ap.add_argument("--segment-seconds", type=float, default=10.0, help="equal 模式每段秒数")
    ap.add_argument("--ext", default=None, help="输出扩展名，默认沿用输入（如 .mp3）")
    ap.add_argument("--copy", action="store_true", help="流拷贝不重编码（更快，切点略不精准）")
    ap.add_argument("--bitrate", default="192k")
    args = ap.parse_args()

    ffmpeg = need_ffmpeg()
    need_ffprobe()
    require_input(args.input)
    ensure_dir(args.output)

    in_ext = os.path.splitext(args.input)[1].lower()
    ext = args.ext or (in_ext if in_ext in DEFAULT_CODEC else ".m4a")
    if not ext.startswith("."):
        ext = "." + ext
    if args.copy and ext != in_ext:
        print("提示：--copy 不支持换格式，输出扩展名沿用输入 %s。" % in_ext)
        ext = in_ext

    dur = probe(args.input).get("duration")
    if not dur:
        fail("无法探测输入时长，切分需要时长信息（请确认 ffprobe 可用）。")

    segments = []
    if args.mode == "equal":
        if args.segment_seconds <= 0:
            fail("--segment-seconds 必须为正数。", 2)
        n = int(math.ceil(dur / args.segment_seconds))
        for i in range(n):
            a = i * args.segment_seconds
            b = min((i + 1) * args.segment_seconds, dur)
            segments.append((a, b))
        print("等长切分：每段 %.2f 秒，共 %d 段" % (args.segment_seconds, n))
    else:
        silences = detect_silences(ffmpeg, args.input, args.noise_db,
                                   args.min_silence)
        cuts = sorted((s + e) / 2.0 for s, e in silences)
        bounds = [0.0] + cuts + [dur]
        segments = [(bounds[i], bounds[i + 1]) for i in range(len(bounds) - 1)]
        kept = [(a, b) for a, b in segments if b - a >= args.min_length]
        print("静音检测：命中 %d 处，候选 %d 段，保留 %d 段（最短 %.2f 秒）"
              % (len(silences), len(segments), len(kept), args.min_length))
        segments = kept

    if not segments:
        fail("没有可输出的片段；可降低 --min-length 或放宽 --noise-db 后重试。", 3)

    template = os.path.join(args.output, "part_%%03d%s" % ext)
    written, failed = [], []
    for i, (a, b) in enumerate(segments, 1):
        desired = template % i
        out = unique_path(desired)
        if out != desired:
            print("提示：%s 已存在，改用 %s（不覆盖旧文件）"
                  % (os.path.basename(desired), os.path.basename(out)))
        cmd = [ffmpeg, "-y", "-ss", "%.3f" % a, "-i", args.input,
               "-map", "0:a:0", "-t", "%.3f" % max(b - a, 0.01)]
        if args.copy:
            cmd += ["-c", "copy"]
        else:
            cmd += audio_encode_args(out, bitrate=args.bitrate)
        cmd += [out]
        rc = run(cmd)
        if rc != 0:
            failed.append(i)
            sys.stderr.write("  [跳过] 第 %d 段失败（ffmpeg 退出码 %d），继续处理其余片段。\n"
                             % (i, rc))
            continue
        written.append(out)
        print("  part_%03d%s  %s → %s  (%.2f 秒)"
              % (i, ext, hms(a), hms(b), b - a))

    print("切分完成：成功 %d 段，失败 %d 段，目录：%s"
          % (len(written), len(failed), os.path.abspath(args.output)))
    if failed:
        print("失败段号：%s" % ", ".join(str(i) for i in failed))
        # 全部失败才算动作失败(5)；部分失败用 6，便于调用方区分
        sys.exit(5 if not written else 6)


if __name__ == "__main__":
    main()
