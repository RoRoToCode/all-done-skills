#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""arc-add：向已有包追加条目，产出新包（原包只读）。"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arc_common as ac


def main():
    ap = argparse.ArgumentParser(description="向压缩包追加文件/目录")
    ap.add_argument("--input", required=True, help="原压缩包（只读）")
    ap.add_argument("--inputs", nargs="+", required=True, help="要追加的文件/目录")
    ap.add_argument("--output", required=True, help="新包路径")
    ap.add_argument("--password", help="原包密码")
    ap.add_argument("--keep-password", action="store_true",
                    help="用原密码把新包也加密（默认输出为无密码包）")
    ap.add_argument("--format", help="输出格式，默认按输出扩展名")
    ap.add_argument("--level", type=int, default=6)
    args = ap.parse_args()

    try:
        ac.need_exists(args.input)
        ac.no_overwrite(args.input, args.output)
        in_fmt = ac.detect_format(args.input)
        out_fmt = ac.normalize_fmt(args.format) if args.format else ac.detect_format(args.output)
        existing = list(ac.read_members(args.input, in_fmt, args.password))
        names = {e.name for e, _ in existing}
        items = ac.collect_paths(args.inputs)
        added = 0
        for name, path, is_dir in items:
            final = name
            i = 2
            while final in names:
                stem, ext = os.path.splitext(name)
                final = "%s (%d)%s" % (stem, i, ext)
                i += 1
            names.add(final)
            for e, data in ac.files_to_members([(final, path, is_dir)]):
                existing.append((e, data))
            added += 1
        pwd = args.password if args.keep_password else None
        ac.write_members(args.output, existing, fmt=out_fmt, level=args.level,
                         password=pwd, force_fmt=out_fmt)
        ac.result(args.output, 格式=out_fmt.upper(), 新增条目=added,
                  总条目=len(existing))
        if args.password and not args.keep_password:
            print("提示：原包加密，输出包未加密（加 --keep-password 可保留密码）")
        return 0
    except ac.ArchiveError as exc:
        print("错误：%s" % exc, file=sys.stderr)
        return exc.code


if __name__ == "__main__":
    sys.exit(main())
