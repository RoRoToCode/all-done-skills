#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""目录树 · 输出文本树形结构，可限制深度与条目数，超限时标记截断

由家族生成器按统一模式生成；业务逻辑集中在 file_common.py。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import file_common as C  # noqa: E402

C.main_guard()


def main():
    p = argparse.ArgumentParser(description="输出文本树形结构，可限制深度与条目数，超限时标记截断")
    p.add_argument("input", help="要扫描的目录")
    p.add_argument("-o", "--output", help="结果文件，省略则打印到 stdout")
    p.add_argument("--depth", type=int, default=3, help="最大递归深度")
    p.add_argument("--max-entries", type=int, default=500, help="最多输出条目数")
    p.add_argument("--include-hidden", action="store_true", help="包含隐藏文件")
    ns = p.parse_args()
    return C.run_file_tree(ns)


if __name__ == "__main__":
    sys.exit(main())
