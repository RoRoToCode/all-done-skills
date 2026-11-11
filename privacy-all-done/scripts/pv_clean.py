#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""元数据清理 · 生成清掉 EXIF/文本块/文档属性的新副本，无法安全处理的格式标记 skipped

由家族生成器按统一模式生成；业务逻辑集中在 pv_common.py。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pv_common as C  # noqa: E402

C.main_guard()


def main():
    p = argparse.ArgumentParser(description="生成清掉 EXIF/文本块/文档属性的新副本，无法安全处理的格式标记 skipped")
    p.add_argument("input", help="源文件")
    p.add_argument("-o", "--output", help="输出文件")
    p.add_argument("--kinds", help="只清理指定类型，逗号分隔")
    p.add_argument("--dry-run", action="store_true", help="只预览，不写文件")
    ns = p.parse_args()
    return C.run_pv_clean(ns)


if __name__ == "__main__":
    sys.exit(main())
