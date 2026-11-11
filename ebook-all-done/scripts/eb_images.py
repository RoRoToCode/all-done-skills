#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""eb-images：列出 / 导出 EPUB 内的图片、字体、样式资源。"""
import argparse
import os
import posixpath
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eb_common import Epub, conflict_dir, json_dump, result, safe_name, setup_stdout

DIRS = {"image": "images", "font": "fonts", "style": "styles"}


def main():
    setup_stdout()
    ap = argparse.ArgumentParser(description="导出 EPUB 资源")
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", help="输出目录")
    ap.add_argument("--list", action="store_true", help="只列清单，不写文件")
    ap.add_argument("--kind", choices=["image", "font", "style", "all"], default="all")
    args = ap.parse_args()
    if not args.list and not args.output:
        from eb_common import die, EXIT_USAGE
        die("需要 --output（或加 --list 只查看）", EXIT_USAGE)
    if not args.list:
        args.output = conflict_dir(args.output)
        if args.output is None:
            print("已跳过（输出目录已存在，EBOOK_ON_CONFLICT=skip）")
            return 0

    ep = Epub(args.input)
    assets = [a for a in ep.assets() if args.kind == "all" or a["kind"] == args.kind]
    used = {}
    for a in assets:
        base = safe_name(posixpath.basename(a["path"]), 50)
        if base in used:
            used[base] += 1
            stem, ext = posixpath.splitext(base)
            base = "%s-%d%s" % (stem, used[base], ext)
        else:
            used[base] = 1
        a["export"] = DIRS[a["kind"]] + "/" + base
        if not args.list:
            dst = os.path.join(args.output, DIRS[a["kind"]], base)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "wb") as f:
                f.write(ep.read(a["path"]))
    counts = {k: sum(1 for a in assets if a["kind"] == k) for k in DIRS}
    print("资源清单：图片 %d / 字体 %d / 样式 %d" %
          (counts["image"], counts["font"], counts["style"]))
    for a in assets[:10]:
        print("  [%s] %s (%d 字节)" % (a["kind"], a["path"], a["size"]))
    if not args.list:
        payload = {"source": os.path.abspath(ep.path), "total": len(assets),
                   "counts": counts, "assets": assets}
        json_dump(os.path.join(args.output, "assets.json"), payload)
        result(args.output, 资源=len(assets))
    ep.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
