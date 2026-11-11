#!/usr/bin/env python3
"""av-burn-subs：把 SRT/VTT 字幕硬烧录（内嵌）进视频画面。

用 ffmpeg subtitles 过滤器。为避免绝对路径/中文/空格在过滤器里的转义坑，
先把字幕复制到临时工作目录、以简单文件名引用，并以该目录为 cwd 运行 ffmpeg。
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from av_common import ffmpeg_path, need_ffmpeg, no_overwrite, ensure_parent, result, probe

# ASS 颜色是 &HBBGGRR& 顺序，这里把 RRGGBB 转成 &HBBGGRR&
def ass_color(rrggbb):
    h = rrggbb.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = h[0:2], h[2:4], h[4:6]
    return "&H%s%s%s&" % (b, g, r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="视频文件")
    ap.add_argument("--subtitle", required=True, help="SRT 或 VTT 字幕")
    ap.add_argument("--output", required=True, help="输出视频")
    ap.add_argument("--font-size", type=int, default=24, help="字号")
    ap.add_argument("--font-color", default="FFFFFF", help="字体颜色 RRGGBB")
    ap.add_argument("--position", default="bottom", help="bottom/center/top")
    ap.add_argument("--outline", type=int, default=2, help="描边宽度")
    args = ap.parse_args()

    ffmpeg = need_ffmpeg()
    no_overwrite(args.input, args.output)
    ensure_parent(args.output)

    work = tempfile.mkdtemp(prefix="avsub_")
    ext = os.path.splitext(args.subtitle)[1].lower()
    sub_name = "sub" + (ext if ext in (".srt", ".vtt", ".ass") else ".srt")
    sub_dst = os.path.join(work, sub_name)
    shutil.copy(args.subtitle, sub_dst)

    align = {"bottom": "2", "center": "5", "top": "8"}.get(args.position, "2")
    style = ("FontSize=%d,PrimaryColour=%s,OutlineColour=&H000000&,"
             "BackColour=&H80000000&,Outline=%d,Shadow=1,Alignment=%s"
             % (args.font_size, ass_color(args.font_color), args.outline, align))
    vf = "subtitles=%s:force_style='%s'" % (sub_name, style)

    rc = subprocess.run([ffmpeg, "-y", "-i", args.input, "-vf", vf,
                         "-c:a", "copy", args.output], cwd=work).returncode
    try:
        os.unlink(sub_dst)
        os.rmdir(work)
    except Exception:
        pass
    if rc != 0:
        sys.stderr.write("字幕烧录失败（ffmpeg 退出码 %d）。检查字幕编码（建议 UTF-8）与路径。\n" % rc)
        sys.exit(5)

    dur, w, h = probe(args.output)
    result(args.output, duration=dur, w=w, h=h)


if __name__ == "__main__":
    main()
