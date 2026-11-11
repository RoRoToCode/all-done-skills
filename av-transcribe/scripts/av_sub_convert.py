#!/usr/bin/env python3
"""av-sub-convert：字幕格式互转（SRT / VTT / LRC / TXT / ASS）。

解析 SRT 与 VTT（二者时间戳语法相同），按输出文件扩展名决定目标格式，
也支持 --to 显式指定。纯本地，零额外依赖。
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from av_common import no_overwrite, ensure_parent, result


def _norm(ts):
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
    return "%d:%02d:%02d.%02d" % (h, m, s, ms // 10)


def to_sec(h, m, s, ms):
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


_TS = re.compile(
    r"(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})\s*-->\s*"
    r"(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})")


def parse(path):
    raw = open(path, encoding="utf-8-sig").read().replace("\r\n", "\n")
    segs = []
    matches = list(_TS.finditer(raw))
    for i, m in enumerate(matches):
        sh, sm, ss, sms, eh, em, es, ems = m.groups()
        sms = (sms + "000")[:3]
        ems = (ems + "000")[:3]
        start = to_sec(sh, sm, ss, sms)
        end = to_sec(eh, em, es, ems)
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
        body = raw[body_start:body_end].strip("\n").strip()
        segs.append({"start": start, "end": end, "text": body})
    return segs


def write_out(segs, path, fmt):
    if fmt == "srt":
        with open(path, "w", encoding="utf-8") as f:
            for i, s in enumerate(segs, 1):
                f.write("%d\n%s --> %s\n%s\n\n" % (i, fmt_srt(s["start"]), fmt_srt(s["end"]), s["text"]))
    elif fmt == "vtt":
        with open(path, "w", encoding="utf-8") as f:
            f.write("WEBVTT\n\n")
            for s in segs:
                f.write("%s --> %s\n%s\n\n" % (fmt_vtt(s["start"]), fmt_vtt(s["end"]), s["text"]))
    elif fmt == "lrc":
        with open(path, "w", encoding="utf-8") as f:
            for s in segs:
                f.write("%s%s\n" % (fmt_lrc(s["start"]), s["text"]))
    elif fmt == "txt":
        with open(path, "w", encoding="utf-8") as f:
            for s in segs:
                f.write(s["text"] + "\n")
    elif fmt == "ass":
        with open(path, "w", encoding="utf-8") as f:
            f.write("[Script Info]\nScriptType: v4.00+\n\n[V4+ Styles]\n")
            f.write("Format: Name, Fontname, Fontsize, PrimaryColour, BackColour, Bold, Italic, "
                    "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
                    "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")
            f.write("Style: Default,Arial,24,&H00FFFFFF,&H00000000,0,0,0,0,100,100,0,0,1,2,2,20,20,20,1\n\n")
            f.write("[Events]\n")
            f.write("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
            for s in segs:
                text = s["text"].strip().replace("\n", "\\N")
                f.write("Dialogue: 0,%s,%s,Default,,0,0,0,,%s\n" % (fmt_ass(s["start"]), fmt_ass(s["end"]), text))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="源字幕（SRT/VTT）")
    ap.add_argument("--output", required=True, help="目标字幕，扩展名决定格式")
    ap.add_argument("--to", default=None, help="显式目标格式：srt/vtt/lrc/txt/ass（默认按扩展名）")
    args = ap.parse_args()

    no_overwrite(args.input, args.output)
    ensure_parent(args.output)

    segs = parse(args.input)
    if not segs:
        sys.stderr.write("未从源文件解析到任何字幕条目，请确认是 SRT/VTT 格式。\n")
        sys.exit(3)

    fmt = (args.to or os.path.splitext(args.output)[1].lower().lstrip(".")).lower()
    if fmt not in ("srt", "vtt", "lrc", "txt", "ass"):
        sys.stderr.write("无法识别的目标格式：%s（用 --to 指定 srt/vtt/lrc/txt/ass）。\n" % fmt)
        sys.exit(3)

    write_out(segs, args.output, fmt)
    result(args.output)
    print("  段数=%d  格式=%s" % (len(segs), fmt))


if __name__ == "__main__":
    main()
