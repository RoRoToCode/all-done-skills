#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""目录比对 · 按相对路径比较两个目录，输出仅左有/仅右有/内容不同/完全一致四类

由家族生成器按统一模式生成；业务逻辑集中在 file_common.py。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import file_common as C  # noqa: E402

C.main_guard()


def main():
    p = argparse.ArgumentParser(description="按相对路径比较两个目录，输出仅左有/仅右有/内容不同/完全一致四类")
    p.add_argument("left", help="左侧目录")
    p.add_argument("right", help="右侧目录")
    p.add_argument("-o", "--output", help="结果文件，省略则打印到 stdout")
    p.add_argument("--hash", action="store_true", help="同路径同体积时再比较内容哈希")
    p.add_argument("--recursive", action="store_true", help="递归子目录")
    ns = p.parse_args()
    return C.run_file_compare(ns)


if __name__ == "__main__":
    sys.exit(main())
