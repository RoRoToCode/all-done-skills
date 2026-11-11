#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""安全批量复制 · 把多个文件或目录复制到目标目录，重名自动避让，保留相对结构，不改动原件

由家族生成器按统一模式生成；业务逻辑集中在 file_common.py。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import file_common as C  # noqa: E402

C.main_guard()


def main():
    p = argparse.ArgumentParser(description="把多个文件或目录复制到目标目录，重名自动避让，保留相对结构，不改动原件")
    p.add_argument("input", nargs="+", help="源文件或目录")
    p.add_argument("-o", "--output", help="目标目录")
    p.add_argument("--pattern", default="*", help="文件名 glob 过滤")
    p.add_argument("--recursive", action="store_true", help="目录递归")
    ns = p.parse_args()
    return C.run_file_copy(ns)


if __name__ == "__main__":
    sys.exit(main())
