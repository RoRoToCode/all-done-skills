#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""两表比对 · 按行号或主键比对两个数据文件，输出新增、删除与变更字段

由家族生成器按统一模式生成；业务逻辑集中在 data_common.py。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import data_common as C  # noqa: E402

C.main_guard()


def main():
    p = argparse.ArgumentParser(description="按行号或主键比对两个数据文件，输出新增、删除与变更字段")
    p.add_argument("old", help="旧文件")
    p.add_argument("new", help="新文件")
    p.add_argument("-o", "--output", help="结果文件，省略则打印到 stdout")
    p.add_argument("--key", help="主键字段，不给则按行号")
    p.add_argument("--from", dest="source_format", help="强制指定格式")
    ns = p.parse_args()
    return C.run_data_diff(ns)


if __name__ == "__main__":
    sys.exit(main())
