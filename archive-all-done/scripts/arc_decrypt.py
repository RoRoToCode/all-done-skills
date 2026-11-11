#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""arc-decrypt：带密码解压，可选重打包成无密码新包。"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arc_common as ac


def main():
    ap = argparse.ArgumentParser(description="带密码解压")
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True, help="解出目录")
    ap.add_argument("--password", required=True)
    ap.add_argument("--repack", help="另存为无密码压缩包（如 plain.zip）")
    ap.add_argument("--format", help="输入格式，默认按扩展名")
    ap.add_argument("--members", action="append", default=[])
    ap.add_argument("--strip-components", type=int, default=0)
    ap.add_argument("--on-conflict", choices=("rename", "overwrite", "skip"),
                    default="rename")
    args = ap.parse_args()

    try:
        ac.need_exists(args.input)
        fmt = ac.normalize_fmt(args.format) if args.format else ac.detect_format(args.input)
        written, skipped = ac.extract_archive(
            args.input, args.output, fmt=fmt, password=args.password,
            members=args.members, strip=args.strip_components,
            on_conflict=args.on_conflict)
        ac.result(args.output, 格式=fmt.upper(), 解出文件=written, 跳过=skipped)
        if args.repack:
            ac.no_overwrite(args.input, args.repack)
            members = list(ac.read_members(args.input, fmt, args.password))
            out_fmt = ac.detect_format(args.repack)
            ac.write_members(args.repack, members, fmt=out_fmt, force_fmt=out_fmt)
            ac.result(args.repack, 说明="已去除密码", 条目数=len(members))
        return 0
    except ac.ArchiveError as exc:
        print("错误：%s" % exc, file=sys.stderr)
        return exc.code
    except Exception as exc:
        print("错误：解密或解压失败：%s" % exc, file=sys.stderr)
        return ac.EXIT_CORRUPT


if __name__ == "__main__":
    sys.exit(main())
