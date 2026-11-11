#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""arc-create：把文件/目录打成压缩包。"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arc_common as ac


def main():
    ap = argparse.ArgumentParser(description="创建压缩包")
    ap.add_argument("--input", help="单个输入（也可用 --inputs）")
    ap.add_argument("--inputs", nargs="+", help="要打包的文件/目录，可多个")
    ap.add_argument("--output", required=True, help="输出压缩包路径")
    ap.add_argument("--format", help="zip/tar/tgz/tbz2/txz/gz/bz2/xz，默认按输出扩展名")
    ap.add_argument("--level", type=int, default=6, help="压缩级别 1-9，默认 6")
    ap.add_argument("--comment", default="", help="包注释（zip 有效）")
    ap.add_argument("--base", help="归档内路径的相对根目录")
    ap.add_argument("--exclude", action="append", default=[],
                    help="排除规则 glob，可多次，如 '*.tmp' '__pycache__'")
    args = ap.parse_args()

    try:
        inputs = args.inputs or ([args.input] if args.input else [])
        if not inputs:
            ac.fail("需要 --input 或 --inputs 指定要打包的内容", ac.EXIT_USAGE)
        for p in inputs:
            ac.no_overwrite(p, args.output)
        fmt = ac.normalize_fmt(args.format) if args.format else ac.detect_format(args.output)
        items = ac.collect_paths(inputs, args.base, args.exclude)
        ac.write_members(args.output, ac.files_to_members(items),
                         fmt=fmt, level=args.level, comment=args.comment,
                         force_fmt=fmt)
        info = ac.archive_info(args.output, fmt)
        ac.result(args.output, 格式=fmt.upper(), 条目数=info["entries"],
                  压缩率="%.1f%%" % info["ratio"])
        return 0
    except ac.ArchiveError as exc:
        print("错误：%s" % exc, file=sys.stderr)
        return exc.code


if __name__ == "__main__":
    sys.exit(main())
