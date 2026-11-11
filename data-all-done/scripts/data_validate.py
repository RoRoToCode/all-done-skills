#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""格式校验 · 校验一个或多个数据文件的语法、字段一致性、空值与疑似类型问题，输出体检报告

由家族生成器按统一模式生成；业务逻辑集中在 data_common.py。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import data_common as C  # noqa: E402

C.main_guard()


def main():
    p = argparse.ArgumentParser(description="校验一个或多个数据文件的语法、字段一致性、空值与疑似类型问题，输出体检报告")
    p.add_argument("input", nargs="+", help="要校验的文件")
    p.add_argument("-o", "--output", help="报告文件，省略则打印到 stdout")
    p.add_argument("--from", dest="source_format", help="强制指定格式")
    p.add_argument("--strict", action="store_true", help="有问题时返回非零退出码")
    ns = p.parse_args()
    return C.run_data_validate(ns)


if __name__ == "__main__":
    sys.exit(main())
