#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""arc-extract：安全解压（zip-slip / tar-slip 防护 + 重名自动避让）。"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arc_common as ac


def main():
    ap = argparse.ArgumentParser(description="解压压缩包")
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True, help="输出目录（自动创建）")
    ap.add_argument("--password", help="加密包密码")
    ap.add_argument("--format", help="强制指定输入格式，默认按扩展名识别")
    ap.add_argument("--members", action="append", default=[],
                    help="只解出匹配的 glob 条目，可多次")
    ap.add_argument("--strip-components", type=int, default=0,
                    help="剥离前 N 层目录")
    ap.add_argument("--on-conflict", choices=("rename", "overwrite", "skip"),
                    default="rename", help="重名策略，默认自动改名放行")
    ap.add_argument("--allow-links", action="store_true",
                    help="tar 链接条目：默认跳过并告警，此项仅静默跳过")
    args = ap.parse_args()

    try:
        ac.need_exists(args.input)
        if os.path.abspath(args.input) == os.path.abspath(args.output):
            ac.fail("输出目录不得等于输入包", ac.EXIT_IO)
        fmt = ac.normalize_fmt(args.format) if args.format else ac.detect_format(args.input)
        written, skipped = ac.extract_archive(
            args.input, args.output, fmt=fmt, password=args.password,
            members=args.members, strip=args.strip_components,
            on_conflict=args.on_conflict, allow_links=args.allow_links)
        ac.result(args.output, 格式=fmt.upper(), 解出文件=written,
                  跳过=skipped, 重名策略=args.on_conflict)
        return 0
    except ac.ArchiveError as exc:
        print("错误：%s" % exc, file=sys.stderr)
        return exc.code
    except (OSError, EOFError) as exc:
        print("错误：包体损坏或读取失败：%s" % exc, file=sys.stderr)
        return ac.EXIT_CORRUPT


if __name__ == "__main__":
    sys.exit(main())
