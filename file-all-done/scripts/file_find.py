#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""条件查找 · 按名称 glob、扩展名、体积区间、最近修改天数组合查找文件

由家族生成器按统一模式生成；业务逻辑集中在 file_common.py。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import file_common as C  # noqa: E402

C.main_guard()


def main():
    p = argparse.ArgumentParser(description="按名称 glob、扩展名、体积区间、最近修改天数组合查找文件")
    p.add_argument("input", help="要扫描的目录")
    p.add_argument("-o", "--output", help="结果文件，省略则打印到 stdout")
    p.add_argument("--name", help="文件名 glob，如 *.pdf")
    p.add_argument("--ext", help="扩展名，多个用逗号分隔，如 pdf,docx")
    p.add_argument("--min-size", type=int, default=0, help="最小体积（KB）")
    p.add_argument("--max-size", type=int, default=0, help="最大体积（KB），0 表示不限")
    p.add_argument("--days", type=int, default=0, help="只收最近 N 天修改过的文件")
    p.add_argument("--recursive", action="store_true", help="递归子目录")
    p.add_argument("--limit", type=int, default=0, help="最多返回条数")
    ns = p.parse_args()
    return C.run_file_find(ns)


if __name__ == "__main__":
    sys.exit(main())
