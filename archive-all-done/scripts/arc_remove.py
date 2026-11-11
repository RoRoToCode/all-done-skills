#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""arc-remove：按 glob 从包内剔除条目，产出新包。"""
import argparse
import fnmatch
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arc_common as ac


def main():
    ap = argparse.ArgumentParser(description="删除压缩包内条目")
    ap.add_argument("--input", required=True, help="原压缩包（只读）")
    ap.add_argument("--output", required=True, help="新包路径")
    ap.add_argument("--members", nargs="+", required=True,
                    help="要删除的 glob，如 '*.txt' 'temp/*'")
    ap.add_argument("--password", help="原包密码")
    ap.add_argument("--format", help="输出格式，默认按输出扩展名")
    ap.add_argument("--level", type=int, default=6)
    args = ap.parse_args()

    try:
        ac.need_exists(args.input)
        ac.no_overwrite(args.input, args.output)
        in_fmt = ac.detect_format(args.input)
        out_fmt = ac.normalize_fmt(args.format) if args.format else ac.detect_format(args.output)
        kept, removed = [], []
        for e, data in ac.read_members(args.input, in_fmt, args.password):
            if any(fnmatch.fnmatch(e.name, p) or
                   fnmatch.fnmatch(os.path.basename(e.name.rstrip("/")), p)
                   for p in args.members):
                removed.append(e.name)
            else:
                kept.append((e, data))
        if not kept:
            ac.fail("删除后包内没有任何条目，已放弃写出（原包未改动）", ac.EXIT_IO)
        ac.write_members(args.output, kept, fmt=out_fmt, level=args.level,
                         force_fmt=out_fmt)
        ac.result(args.output, 格式=out_fmt.upper(), 删除条目=len(removed),
                  保留条目=len(kept))
        if removed:
            print("已删除：" + ", ".join(removed[:8])
                  + (" ..." if len(removed) > 8 else ""))
        return 0
    except ac.ArchiveError as exc:
        print("错误：%s" % exc, file=sys.stderr)
        return exc.code


if __name__ == "__main__":
    sys.exit(main())
