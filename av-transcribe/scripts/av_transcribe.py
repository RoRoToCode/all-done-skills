#!/usr/bin/env python3
"""av-transcribe：音视频转写（语音识别 / ASR），基于本地 Whisper 模型。

流程：用 ffmpeg 抽 16kHz 单声道 wav -> 交给 Whisper 识别 -> 写出带时间戳字幕。
优先用 openai-whisper，缺失时回退 faster-whisper。
"""
import argparse
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from av_common import ffmpeg_path, need_ffmpeg, ensure_parent, result, run


# ----------------------------------------------------------------------------
# 时间戳格式化
# ----------------------------------------------------------------------------
def _norm(ts):
    """把浮点秒规整为 (h, m, s, ms)，ms 取 0-999。"""
    h = int(ts // 3600)
    m = int((ts % 3600) // 60)
    s = int(ts % 60)
    ms = int(round((ts - int(ts)) * 1000))
    if ms >= 1000:
        ms = 999
    return h, m, s, ms


def fmt_srt(ts):
    h, m, s, ms = _norm(ts)
    return "%02d:%02d:%02d,%03d" % (h, m, s, ms)


def fmt_vtt(ts):
    h, m, s, ms = _norm(ts)
    return "%02d:%02d:%02d.%03d" % (h, m, s, ms)


def fmt_lrc(ts):
    m = int(ts // 60)
    s = ts % 60
    return "[%02d:%05.2f]" % (m, s)


def fmt_ass(ts):
    h, m, s, ms = _norm(ts)
    cs = ms // 10
    return "%d:%02d:%02d.%02d" % (h, m, s, cs)


# ----------------------------------------------------------------------------
# 写出各格式
# ----------------------------------------------------------------------------
def write_srt(segs, path):
    with open(path, "w", encoding="utf-8") as f:
        for i, s in enumerate(segs, 1):
            f.write("%d\n%s --> %s\n%s\n\n" % (i, fmt_srt(s["start"]), fmt_srt(s["end"]), s["text"].strip()))


def write_vtt(segs, path):
    with open(path, "w", encoding="utf-8") as f:
        f.write("WEBVTT\n\n")
        for s in segs:
            f.write("%s --> %s\n%s\n\n" % (fmt_vtt(s["start"]), fmt_vtt(s["end"]), s["text"].strip()))


def write_txt(segs, path):
    with open(path, "w", encoding="utf-8") as f:
        for s in segs:
            f.write(s["text"].strip() + "\n")


def write_lrc(segs, path):
    with open(path, "w", encoding="utf-8") as f:
        for s in segs:
            f.write("%s%s\n" % (fmt_lrc(s["start"]), s["text"].strip()))


def write_ass(segs, path):
    with open(path, "w", encoding="utf-8") as f:
        f.write("[Script Info]\nScriptType: v4.00+\n\n")
        f.write("[V4+ Styles]\n")
        f.write("Format: Name, Fontname, Fontsize, PrimaryColour, BackColour, Bold, Italic, Underline, "
                "StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, "
                "MarginL, MarginR, MarginV, Encoding\n")
        f.write("Style: Default,Arial,24,&H00FFFFFF,&H00000000,0,0,0,0,100,100,0,0,1,2,2,20,20,20,1\n\n")
        f.write("[Events]\n")
        f.write("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
        for s in segs:
            text = s["text"].strip().replace("\n", "\\N")
            f.write("Dialogue: 0,%s,%s,Default,,0,0,0,,%s\n" % (fmt_ass(s["start"]), fmt_ass(s["end"]), text))


# ----------------------------------------------------------------------------
# 后端加载与识别
# ----------------------------------------------------------------------------
def load_backend():
    try:
        import whisper
        return ("whisper", whisper)
    except Exception:
        pass
    try:
        from faster_whisper import WhisperModel
        return ("faster_whisper", WhisperModel)
    except Exception:
        pass
    sys.stderr.write(
        "缺少依赖 whisper：请先安装本地语音识别引擎。\n"
        "  pip install openai-whisper        # 官方 Whisper（推荐）\n"
        "  pip install faster-whisper        # 更快的替代实现\n"
        "首次运行会下载模型权重，请保证联网；模型默认保存在 ~/.cache/whisper。\n")
    sys.exit(2)


def transcribe(audio, model_size, language, device, backend, mod):
    if backend == "whisper":
        model = mod.load_model(model_size, device=device)
        res = model.transcribe(audio, language=language or None, task="transcribe", verbose=False)
        segs = [{"start": s["start"], "end": s["end"], "text": s["text"]} for s in res["segments"]]
        return res, segs
    # faster_whisper
    compute = "int8" if device == "cpu" else "float16"
    model = mod(model_size, device=device, compute_type=compute)
    gen, info = model.transcribe(audio, language=language or None, beam_size=5)
    segs = []
    for s in gen:
        segs.append({"start": s.start, "end": s.end, "text": s.text})
    res = {"text": " ".join(x["text"] for x in segs),
           "language": getattr(info, "language", language)}
    return res, segs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="音频或视频文件")
    ap.add_argument("--output-dir", default=None, help="输出目录，默认与输入同目录")
    ap.add_argument("--model", default="base",
                    help="模型大小：tiny/base/small/medium/large（越大越准越慢）")
    ap.add_argument("--language", default=None, help="语言代码：zh/en/... 留空自动检测")
    ap.add_argument("--device", default="cpu", help="cpu 或 cuda")
    ap.add_argument("--format", default="all",
                    help="输出格式：all/srt/vtt/txt/json/lrc/ass（可逗号分隔多项）")
    args = ap.parse_args()

    ffmpeg = need_ffmpeg()
    out_dir = args.output_dir or os.path.dirname(os.path.abspath(args.input))
    ensure_parent(os.path.join(out_dir, "x"))
    stem = os.path.splitext(os.path.basename(args.input))[0]

    tmp = tempfile.mkdtemp(prefix="avtr_")
    wav = os.path.join(tmp, stem + ".wav")
    rc = run([ffmpeg, "-y", "-i", args.input, "-vn", "-ac", "1", "-ar", "16000",
              "-f", "wav", wav])
    if rc != 0:
        sys.stderr.write("提取音频失败（ffmpeg 退出码 %d）。\n" % rc)
        sys.exit(5)

    backend, mod = load_backend()
    res, segs = transcribe(wav, args.model, args.language, args.device, backend, mod)

    wanted = set(x.strip().lower() for x in args.format.split(","))
    if "all" in wanted:
        wanted = {"srt", "vtt", "txt", "json", "lrc"}

    writers = {
        "srt": (write_srt, ".srt"),
        "vtt": (write_vtt, ".vtt"),
        "txt": (write_txt, ".txt"),
        "json": (None, ".json"),
        "lrc": (write_lrc, ".lrc"),
        "ass": (write_ass, ".ass"),
    }
    written = []
    for fmt in wanted:
        if fmt not in writers:
            sys.stderr.write("不支持的格式：%s（忽略）\n" % fmt)
            continue
        fn, ext = writers[fmt]
        p = os.path.join(out_dir, stem + ext)
        if fn is None:
            with open(p, "w", encoding="utf-8") as f:
                json.dump({"language": res.get("language"), "text": res.get("text", ""),
                           "segments": segs}, f, ensure_ascii=False, indent=2)
        else:
            fn(segs, p)
        written.append(p)

    print("转写完成：引擎=%s，语言=%s，段数=%d" % (backend, res.get("language"), len(segs)))
    for p in written:
        result(p)

    try:
        os.unlink(wav)
        os.rmdir(tmp)
    except Exception:
        pass


if __name__ == "__main__":
    main()
