#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""嵌套扁平化 · 把嵌套 dict/list 展开成点路径字段，便于再转 CSV 或 Markdown 表格

由家族生成器按统一模式生成；业务逻辑集中在 data_common.py。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import data_common as C  # noqa: E402

C.main_guard()


def main():
    p = argparse.ArgumentParser(description="把嵌套 dict/list 展开成点路径字段，便于再转 CSV 或 Markdown 表格")
    p.add_argument("input", help="JSON 源文件")
    p.add_argument("-o", "--output", help="输出文件")
    p.add_argument("--to", dest="target_format", help="目标格式，默认按扩展名推断")
    p.add_argument("--sep", default=".", help="路径分隔符")
    ns = p.parse_args()
    return C.run_data_flatten(ns)


if __name__ == "__main__":
    sys.exit(main())
