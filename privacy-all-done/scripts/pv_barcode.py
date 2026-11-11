#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Code128 条形码 · 纯标准库生成 Code128-B 条形码 SVG，含校验位计算

由家族生成器按统一模式生成；业务逻辑集中在 pv_common.py。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pv_common as C  # noqa: E402

C.main_guard()


def main():
    p = argparse.ArgumentParser(description="纯标准库生成 Code128-B 条形码 SVG，含校验位计算")
    p.add_argument("text", help="要编码的文本（ASCII 可打印字符）")
    p.add_argument("-o", "--output", help="SVG 文件，省略则打印到 stdout")
    p.add_argument("--height", type=int, default=60, help="条高（px）")
    p.add_argument("--scale", type=int, default=2, help="模块宽度（px）")
    ns = p.parse_args()
    return C.run_pv_barcode(ns)


if __name__ == "__main__":
    sys.exit(main())
