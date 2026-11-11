#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""体积报告 · 大文件 Top N、空文件、按扩展名聚合与总占用统计

由家族生成器按统一模式生成；业务逻辑集中在 file_common.py。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import file_common as C  # noqa: E402

C.main_guard()


def main():
    p = argparse.ArgumentParser(description="大文件 Top N、空文件、按扩展名聚合与总占用统计")
    p.add_argument("input", help="要扫描的目录")
    p.add_argument("-o", "--output", help="报告文件，省略则打印到 stdout")
    p.add_argument("--top", type=int, default=20, help="大文件条数")
    p.add_argument("--min-mb", type=float, default=0.0, help="只统计大于该体积（MB）的文件")
    p.add_argument("--empty-only", action="store_true", help="只列空文件")
    p.add_argument("--recursive", action="store_true", help="递归子目录")
    ns = p.parse_args()
    return C.run_file_size(ns)


if __name__ == "__main__":
    sys.exit(main())
