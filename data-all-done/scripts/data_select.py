#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""字段映射 · 选择、排除与重命名字段，输出精简后的记录表

由家族生成器按统一模式生成；业务逻辑集中在 data_common.py。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import data_common as C  # noqa: E402

C.main_guard()


def main():
    p = argparse.ArgumentParser(description="选择、排除与重命名字段，输出精简后的记录表")
    p.add_argument("input", help="源文件")
    p.add_argument("-o", "--output", help="输出文件")
    p.add_argument("--fields", help="保留字段，逗号分隔")
    p.add_argument("--exclude", help="排除字段，逗号分隔")
    p.add_argument("--rename", action="append", default=[], help="重命名 old:new，可重复")
    p.add_argument("--to", dest="target_format", help="目标格式，默认按扩展名推断")
    p.add_argument("--from", dest="source_format", help="强制指定源格式")
    ns = p.parse_args()
    return C.run_data_select(ns)


if __name__ == "__main__":
    sys.exit(main())
