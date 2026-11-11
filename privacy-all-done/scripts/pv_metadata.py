#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""元数据读取 · 读取 JPEG EXIF、PNG 文本块、OOXML core/app 属性与 PDF 常见文档信息键

由家族生成器按统一模式生成；业务逻辑集中在 pv_common.py。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pv_common as C  # noqa: E402

C.main_guard()


def main():
    p = argparse.ArgumentParser(description="读取 JPEG EXIF、PNG 文本块、OOXML core/app 属性与 PDF 常见文档信息键")
    p.add_argument("input", nargs="+", help="文件，可给多个")
    p.add_argument("-o", "--output", help="结果文件，省略则打印到 stdout")
    ns = p.parse_args()
    return C.run_pv_metadata(ns)


if __name__ == "__main__":
    sys.exit(main())
