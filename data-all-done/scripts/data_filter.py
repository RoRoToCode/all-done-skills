#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""条件筛选 · 用受限的「字段 运算符 值」表达式筛选记录，支持多条件与 any/all 组合

由家族生成器按统一模式生成；业务逻辑集中在 data_common.py。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import data_common as C  # noqa: E402

C.main_guard()


def main():
    p = argparse.ArgumentParser(description="用受限的「字段 运算符 值」表达式筛选记录，支持多条件与 any/all 组合")
    p.add_argument("input", help="源文件")
    p.add_argument("-o", "--output", help="输出文件")
    p.add_argument("--where", action="append", default=[], help='条件，可重复，如 amount >= 100')
    p.add_argument("--match", choices=["all", "any"], default="all", help="多条件组合方式")
    p.add_argument("--to", dest="target_format", help="目标格式，默认按扩展名推断")
    p.add_argument("--from", dest="source_format", help="强制指定源格式")
    p.add_argument("--limit", type=int, default=0, help="最多输出条数")
    ns = p.parse_args()
    return C.run_data_filter(ns)


if __name__ == "__main__":
    sys.exit(main())
