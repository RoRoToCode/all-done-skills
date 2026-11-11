"""aud-visualize：用 ffmpeg 滤镜渲染波形图 / 频谱图 PNG（无需第三方库）。"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aud_common import (need_ffmpeg, require_input, ensure_parent, run, fail,
                        result)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True, help="输出 PNG 路径")
    ap.add_argument("--mode", choices=["waveform", "spectrum"], default="waveform")
    ap.add_argument("--size", default="1600x400", help="图片尺寸 WxH（默认 1600x400）")
    ap.add_argument("--color", default="#5b8cff", help="波形颜色，如 #5b8cff / white")
    ap.add_argument("--split-channels", action="store_true", help="多声道分层显示")
    args = ap.parse_args()

    ext = os.path.splitext(args.output)[1].lower()
    if ext not in (".png", ".jpg", ".jpeg"):
        fail("可视化输出须为 .png / .jpg，当前为 %s" % (ext or "无扩展名"), 3)

    ffmpeg = need_ffmpeg()
    require_input(args.input)
    ensure_parent(args.output)

    if args.mode == "waveform":
        flt = ("[0:a]showwavespic=s=%s:colors=%s:split_channels=%d[v]"
               % (args.size, args.color, 1 if args.split_channels else 0))
    else:
        flt = "[0:a]showspectrumpic=s=%s:legend=disabled[v]" % args.size

    cmd = [ffmpeg, "-y", "-i", args.input, "-filter_complex", flt,
           "-map", "[v]", "-frames:v", "1", args.output]

    rc = run(cmd)
    if rc != 0:
        fail("可视化渲染失败（ffmpeg 退出码 %d）；请确认本机 ffmpeg 编译了 %s 滤镜。"
             % (rc, "showwavespic" if args.mode == "waveform" else "showspectrumpic"))
    result(args.output, extra="模式=%s 尺寸=%s" % (args.mode, args.size))


if __name__ == "__main__":
    main()
