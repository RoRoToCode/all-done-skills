#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""arc-info：压缩包信息与体积统计。"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arc_common as ac


def main():
    ap = argparse.ArgumentParser(description="压缩包信息与统计")
    ap.add_argument("--input", required=True)
    ap.add_argument("--password")
    ap.add_argument("--format")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    try:
        fmt = ac.normalize_fmt(args.format) if args.format else None
        info = ac.archive_info(args.input, fmt, args.password)
        info.pop("entries_detail", None)
        if args.json:
            print(json.dumps(info, ensure_ascii=False, indent=2))
        else:
            print("路径      : %s" % info["path"])
            print("格式      : %s" % info["format"].upper())
            print("加密      : %s" % ("是" if info["encrypted"] else "否"))
            print("条目/文件/目录: %d / %d / %d"
                  % (info["entries"], info["files"], info["dirs"]))
            print("原始体积  : %s" % ac.human(info["original"]))
            print("压缩后    : %s" % ac.human(info["packed"]))
            print("压缩率    : %.1f%%" % info["ratio"])
            if info["comment"]:
                print("注释      : %s" % info["comment"])
        return 0
    except ac.ArchiveError as exc:
        print("错误：%s" % exc, file=sys.stderr)
        return exc.code
    except Exception as exc:
        print("错误：无法读取压缩包：%s" % exc, file=sys.stderr)
        return ac.EXIT_CORRUPT


if __name__ == "__main__":
    sys.exit(main())
