#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""eb-convert：经 Calibre ebook-convert 做电子书格式互转（可选外部依赖）。"""
import argparse
import os
import shlex
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eb_common import (Epub, conflict_path, die, ensure_parent, need_calibre, result,
                       setup_stdout, EXIT_FAIL, EXIT_FORMAT, EXIT_USAGE)

OUT_EXT = {".epub", ".mobi", ".azw3", ".azw", ".pdf", ".docx", ".txt",
           ".html", ".htmlz", ".fb2", ".lit", ".pdb", ".rtf", ".odt",
           ".cbz", ".cbr", ".kfx", ".epub3"}


def main():
    setup_stdout()
    ap = argparse.ArgumentParser(description="Calibre 电子书格式互转")
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--to", help="显式指定输出格式（如 epub3 / mobi），默认按扩展名推断")
    ap.add_argument("--extra", default="", help="额外传给 ebook-convert 的参数")
    ap.add_argument("--timeout", type=int, default=600)
    args = ap.parse_args()
    if not os.path.isfile(args.input):
        die("输入文件不存在：%s" % args.input, 3)
    out = args.output
    if args.to:
        ext = args.to.lower().lstrip(".")
        if ext.startswith("epub"):
            ext = "epub"
        out = os.path.splitext(out)[0] + "." + ext
    ext = os.path.splitext(out)[1].lower()
    if ext not in OUT_EXT:
        die("不支持的输出格式 %s（可用：%s）" %
            (ext, ", ".join(sorted(OUT_EXT))), EXIT_USAGE)
    if os.path.abspath(args.input) == os.path.abspath(out):
        die("输出不得等于输入", 3)
    if args.input.lower().endswith(".epub"):
        try:
            ep = Epub(args.input)
            if ep.protected():
                die("输入含 DRM / 加密标记，本技能不处理受保护内容", EXIT_FORMAT)
            ep.close()
        except SystemExit:
            raise
        except Exception:
            pass  # 非标准 EPUB 交给 Calibre 自己判断
    out = conflict_path(out)
    if out is None:
        print("已跳过（输出已存在，EBOOK_ON_CONFLICT=skip）：%s" % args.output)
        return 0
    exe = need_calibre()
    ensure_parent(out)
    extra = shlex.split(args.extra) if args.extra else []
    cmd = [exe, os.path.abspath(args.input), os.path.abspath(out)] + extra
    print("调用 Calibre：%s -> %s" % (os.path.basename(args.input),
                                      os.path.basename(out)))
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              encoding="utf-8", errors="replace",
                              timeout=args.timeout)
    except subprocess.TimeoutExpired:
        die("ebook-convert 超时（%ss）" % args.timeout, EXIT_FAIL)
    if proc.returncode != 0 or not os.path.isfile(out) or os.path.getsize(out) == 0:
        tail = (proc.stderr or proc.stdout or "").strip()[-900:]
        die("ebook-convert 失败（退出码 %s）：%s" % (proc.returncode, tail), EXIT_FAIL)
    result(out, 格式=ext.lstrip("."), 字节=os.path.getsize(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
