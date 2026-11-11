#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""记录去重 · 按全部字段或指定字段去重，保留首条或末条

由家族生成器按统一模式生成；业务逻辑集中在 data_common.py。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import data_common as C  # noqa: E402

C.main_guard()


def main():
    p = argparse.ArgumentParser(description="按全部字段或指定字段去重，保留首条或末条")
    p.add_argument("input", help="源文件")
    p.add_argument("-o", "--output", help="输出文件")
    p.add_argument("--by", help="判重字段，逗号分隔，不给则比较整条记录")
    p.add_argument("--keep", choices=["first", "last"], default="first", help="保留哪一条")
    p.add_argument("--to", dest="target_format", help="目标格式，默认按扩展名推断")
    p.add_argument("--from", dest="source_format", help="强制指定源格式")
    ns = p.parse_args()
    return C.run_data_dedupe(ns)


if __name__ == "__main__":
    sys.exit(main())
