#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""arc-split：按目标体积分卷压缩，每卷独立可解压，并写清单 JSON。"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arc_common as ac


def parse_size(text):
    t = str(text).strip().upper().replace(" ", "")
    units = {"K": 1024, "M": 1024 ** 2, "G": 1024 ** 3}
    mult = 1
    if t and t[-1] in units:
        mult = units[t[-1]]
        t = t[:-1]
    if t.endswith("B"):
        t = t[:-1]
    try:
        val = int(float(t) * mult)
    except ValueError:
        ac.fail("体积格式不合法：%r（示例：500K / 10M / 1G）" % text, ac.EXIT_USAGE)
    if val <= 0:
        ac.fail("体积必须为正数", ac.EXIT_USAGE)
    return val


def main():
    ap = argparse.ArgumentParser(description="分卷压缩")
    ap.add_argument("--input")
    ap.add_argument("--inputs", nargs="+", help="要打包的文件/目录")
    ap.add_argument("--output", required=True,
                    help="输出前缀，如 out/part.zip → out/part.part001.zip")
    ap.add_argument("--size", default="10M", help="每卷原始体积上限，默认 10M")
    ap.add_argument("--format", default="zip", help="分卷格式，默认 zip")
    ap.add_argument("--level", type=int, default=6)
    ap.add_argument("--base")
    ap.add_argument("--exclude", action="append", default=[])
    args = ap.parse_args()

    try:
        limit = parse_size(args.size)
        inputs = args.inputs or ([args.input] if args.input else [])
        if not inputs:
            ac.fail("需要 --input 或 --inputs", ac.EXIT_USAGE)
        fmt = ac.normalize_fmt(args.format)
        items = ac.collect_paths(inputs, args.base, args.exclude)
        stem, ext = os.path.splitext(args.output)
        ext = ext or ac.ext_for(fmt)
        ac.ensure_parent(args.output)

        groups, cur, cur_size = [], [], 0
        for name, path, is_dir in items:
            size = 0 if is_dir else os.path.getsize(path)
            if cur and cur_size + size > limit:
                groups.append(cur)
                cur, cur_size = [], 0
            cur.append((name, path, is_dir))
            cur_size += size
            if size > limit:
                sys.stderr.write("提示：%s 原始体积 %s 超过单卷上限，已单独成卷。\n"
                                 % (name, ac.human(size)))
        if cur:
            groups.append(cur)

        parts = []
        for i, group in enumerate(groups, 1):
            part = "%s.part%03d%s" % (stem, i, ext)
            ac.write_members(part, ac.files_to_members(group), fmt=fmt,
                             level=args.level, force_fmt=fmt)
            parts.append(os.path.basename(part))
        manifest = stem + ".manifest.json"
        with open(manifest, "w", encoding="utf-8") as f:
            json.dump({"format": "archive-all-done/split-v1",
                       "archive_format": fmt, "size_limit": limit,
                       "part_count": len(parts), "parts": parts},
                      f, ensure_ascii=False, indent=2)
        ac.result(stem, 分卷数=len(parts), 单卷上限=ac.human(limit),
                  清单=os.path.basename(manifest))
        for p in parts:
            print("  %-28s %s" % (p, ac.human(os.path.getsize(
                os.path.join(os.path.dirname(os.path.abspath(args.output)), p)))))
        return 0
    except ac.ArchiveError as exc:
        print("错误：%s" % exc, file=sys.stderr)
        return exc.code


if __name__ == "__main__":
    sys.exit(main())
