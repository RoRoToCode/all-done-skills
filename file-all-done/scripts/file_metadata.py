#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""文件元数据 · 读取体积、创建/修改时间、扩展名、MIME 猜测、权限与链接属性

由家族生成器按统一模式生成；业务逻辑集中在 file_common.py。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import file_common as C  # noqa: E402

C.main_guard()


def main():
    p = argparse.ArgumentParser(description="读取体积、创建/修改时间、扩展名、MIME 猜测、权限与链接属性")
    p.add_argument("input", nargs="+", help="文件或目录，可给多个")
    p.add_argument("-o", "--output", help="结果文件，省略则打印到 stdout")
    ns = p.parse_args()
    return C.run_file_metadata(ns)


if __name__ == "__main__":
    sys.exit(main())
