"""vid-textcard：文字卡片 -> 视频（真·文字生成视频），支持转场与配乐。"""
import argparse
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vid_common import (need_ffmpeg, need_pillow, no_overwrite, ensure_parent,
                        result, probe, render_text_card, assemble)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True)
    ap.add_argument("--cards", default=None, help="JSON 文件：[{title,body,bg,fg,accent}]")
    ap.add_argument("--title", default=None, help="单卡片标题")
    ap.add_argument("--body", default=None, help="单卡片正文")
    ap.add_argument("--bg", default="#10142b")
    ap.add_argument("--fg", default="#ffffff")
    ap.add_argument("--accent", default="#5b8cff")
    ap.add_argument("--duration", type=float, default=4.0)
    ap.add_argument("--transition", default="fade", choices=["fade", "none"])
    ap.add_argument("--fade-dur", type=float, default=0.6)
    ap.add_argument("--resolution", default="1280x720")
    ap.add_argument("--fps", type=int, default=25)
    ap.add_argument("--audio", default=None)
    ap.add_argument("--kenburns", action="store_true", help="缓慢推近")
    args = ap.parse_args()

    need_pillow()
    ffmpeg = need_ffmpeg()
    if args.audio:
        no_overwrite(args.audio, args.output)
    ensure_parent(args.output)

    cards = []
    if args.cards:
        if not os.path.exists(args.cards):
            sys.stderr.write("卡片 JSON 不存在：%s\n" % args.cards)
            sys.exit(3)
        with open(args.cards, encoding="utf-8") as f:
            cards = json.load(f)
        if isinstance(cards, dict):
            cards = [cards]
    elif args.title or args.body:
        cards = [{"title": args.title or "", "body": args.body or "",
                  "bg": args.bg, "fg": args.fg, "accent": args.accent}]
    else:
        sys.stderr.write("请通过 --cards 或 --title/--body 提供内容。\n")
        sys.exit(2)

    try:
        W, H = (int(x) for x in args.resolution.lower().split("x"))
    except Exception:
        sys.stderr.write("分辨率格式应为 宽x高，如 1280x720。\n")
        sys.exit(2)

    tmp = tempfile.mkdtemp(prefix="vidcard_")
    try:
        pngs = []
        for i, c in enumerate(cards):
            img = render_text_card(
                W, H, c.get("title", ""), c.get("body", ""),
                c.get("bg", args.bg), c.get("fg", args.fg),
                c.get("accent", args.accent))
            dst = os.path.join(tmp, "c_%03d.png" % i)
            img.save(dst)
            pngs.append(dst)
        assemble(pngs, args.output, args.duration, args.transition,
                 args.fade_dur, args.fps, args.audio, args.kenburns, W, H, ffmpeg)
    finally:
        for f in os.listdir(tmp):
            try:
                os.unlink(os.path.join(tmp, f))
            except Exception:
                pass
        try:
            os.rmdir(tmp)
        except Exception:
            pass

    if os.path.exists(args.output):
        d, w, h = probe(args.output)
        result(args.output, d, w, h)
    sys.exit(0)


if __name__ == "__main__":
    main()
