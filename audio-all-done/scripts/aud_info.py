"""aud-info：读取音频元数据（时长/编码/采样率/声道/码率/位深/标签）。"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aud_common import (need_ffprobe, no_overwrite, require_input,
                        ensure_parent, probe, hms)


def summary(info, inp):
    bits = info.get("bits_per_sample")
    rate = info.get("bit_rate")
    lines = [
        "文件      : %s" % os.path.abspath(inp),
        "封装      : %s" % (info.get("format_name") or "?"),
        "音频编码  : %s" % (info.get("codec") or "?"),
        "时长      : %s (%.2f 秒)" % (hms(info.get("duration")),
                                    info.get("duration") or 0),
        "采样率    : %s Hz" % (info.get("sample_rate") or "?"),
        "声道      : %s (%s)" % (info.get("channels") or "?",
                                info.get("channel_layout") or "?"),
        "码率      : %s" % ("%d kbps" % int(rate / 1000) if rate else "?"),
        "位深      : %s" % (bits if bits not in (None, 0, "0") else "?"),
        "流数量    : %d" % len(info.get("streams") or []),
    ]
    tags = info.get("tags") or {}
    if tags:
        lines.append("标签      :")
        for k in ("title", "artist", "album", "date", "genre"):
            if tags.get(k):
                lines.append("  %-8s: %s" % (k, tags[k]))
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", default=None, help="可选：把完整信息写成 JSON 文件")
    ap.add_argument("--format", choices=["text", "json"], default="text")
    args = ap.parse_args()

    need_ffprobe()
    require_input(args.input)
    info = probe(args.input)
    if not info:
        sys.stderr.write("无法读取音频信息：%s（ffprobe 解析失败或文件无音频流）。\n"
                         % args.input)
        sys.exit(5)

    if args.output:
        no_overwrite(args.input, args.output)
        ensure_parent(args.output)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=2)
            f.write("\n")

    if args.format == "json":
        print(json.dumps(info, ensure_ascii=False, indent=2))
    else:
        print(summary(info, args.input))
        if args.output:
            print("已写出 JSON: %s" % os.path.abspath(args.output))


if __name__ == "__main__":
    main()
