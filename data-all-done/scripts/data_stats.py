#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""字段画像 · 统计每字段的记录数、空值率、唯一值、推断类型、极值或高频值 Top N

由家族生成器按统一模式生成；业务逻辑集中在 data_common.py。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import data_common as C  # noqa: E402

C.main_guard()


def main():
    p = argparse.ArgumentParser(description="统计每字段的记录数、空值率、唯一值、推断类型、极值或高频值 Top N")
    p.add_argument("input", help="源文件")
    p.add_argument("-o", "--output", help="报告文件，省略则打印到 stdout")
    p.add_argument("--from", dest="source_format", help="强制指定格式")
    p.add_argument("--top", type=int, default=10, help="高频值条数")
    ns = p.parse_args()
    return C.run_data_stats(ns)


if __name__ == "__main__":
    sys.exit(main())
