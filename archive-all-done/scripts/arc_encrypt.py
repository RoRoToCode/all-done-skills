#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""arc-encrypt：带密码打包；pyzipper 可用→AES-256，否则标准库 ZipCrypto。"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arc_common as ac


def main():
    ap = argparse.ArgumentParser(description="加密压缩")
    ap.add_argument("--input")
    ap.add_argument("--inputs", nargs="+", help="要打包的文件/目录")
    ap.add_argument("--output", required=True)
    ap.add_argument("--password", required=True, help="密码（不回显、不写日志）")
    ap.add_argument("--format", default="zip", help="zip（默认）或 7z（需 py7zr）")
    ap.add_argument("--level", type=int, default=6)
    ap.add_argument("--base")
    ap.add_argument("--exclude", action="append", default=[])
    args = ap.parse_args()

    try:
        inputs = args.inputs or ([args.input] if args.input else [])
        if not inputs:
            ac.fail("需要 --input 或 --inputs", ac.EXIT_USAGE)
        if not args.password:
            ac.fail("密码不能为空", ac.EXIT_USAGE)
        for p in inputs:
            ac.no_overwrite(p, args.output)
        fmt = ac.normalize_fmt(args.format)
        if fmt not in ("zip", "7z"):
            ac.fail("加密只支持 zip / 7z，其余格式请先打包再加密", ac.EXIT_IO)
        items = ac.collect_paths(inputs, args.base, args.exclude)
        ac.write_members(args.output, ac.files_to_members(items), fmt=fmt,
                         level=args.level, password=args.password, force_fmt=fmt)
        if fmt == "7z":
            algo = "7z AES-256（py7zr）"
        elif ac.dep_available("pyzipper"):
            algo = "AES-256（pyzipper）"
        else:
            algo = "ZipCrypto 传统弱加密（仅防误看，建议 pip install pyzipper）"
        info = ac.archive_info(args.output, fmt, args.password)
        ac.result(args.output, 格式=fmt.upper(), 加密算法=algo,
                  条目数=info["entries"])
        return 0
    except ac.ArchiveError as exc:
        print("错误：%s" % exc, file=sys.stderr)
        return exc.code


if __name__ == "__main__":
    sys.exit(main())
