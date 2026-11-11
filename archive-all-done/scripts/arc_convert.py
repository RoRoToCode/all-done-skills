#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""arc-convert：压缩包格式互转（保持包内目录结构）。"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arc_common as ac


def main():
    ap = argparse.ArgumentParser(description="压缩包格式互转")
    ap.add_argument("--input", required=True, help="原压缩包（只读）")
    ap.add_argument("--output", required=True, help="目标包路径")
    ap.add_argument("--format", help="目标格式，默认按输出扩展名")
    ap.add_argument("--password", help="原包密码")
    ap.add_argument("--level", type=int, default=6)
    ap.add_argument("--comment", default="")
    args = ap.parse_args()

    try:
        ac.need_exists(args.input)
        ac.no_overwrite(args.input, args.output)
        in_fmt = ac.detect_format(args.input)
        out_fmt = ac.normalize_fmt(args.format) if args.format else ac.detect_format(args.output)
        members = list(ac.read_members(args.input, in_fmt, args.password))
        if not members:
            ac.fail("原包内没有条目", ac.EXIT_IO)
        ac.write_members(args.output, members, fmt=out_fmt, level=args.level,
                         comment=args.comment, force_fmt=out_fmt)
        info = ac.archive_info(args.output, out_fmt)
        ac.result(args.output, 转换="%s → %s" % (in_fmt.upper(), out_fmt.upper()),
                  条目数=info["entries"], 压缩率="%.1f%%" % info["ratio"])
        return 0
    except ac.ArchiveError as exc:
        print("错误：%s" % exc, file=sys.stderr)
        return exc.code
    except Exception as exc:
        print("错误：转换失败：%s" % exc, file=sys.stderr)
        return ac.EXIT_CORRUPT


if __name__ == "__main__":
    sys.exit(main())
