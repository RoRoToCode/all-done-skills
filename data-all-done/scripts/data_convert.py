#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""格式互转 · 在 CSV/TSV/JSON/NDJSON/XML/YAML/TOML/Markdown 表格之间转换，格式可显式指定或按扩展名推断

由家族生成器按统一模式生成；业务逻辑集中在 data_common.py。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import data_common as C  # noqa: E402

C.main_guard()


def main():
    p = argparse.ArgumentParser(description="在 CSV/TSV/JSON/NDJSON/XML/YAML/TOML/Markdown 表格之间转换，格式可显式指定或按扩展名推断")
    p.add_argument("input", help="源文件")
    p.add_argument("-o", "--output", help="目标文件")
    p.add_argument("--from", dest="source_format", help="源格式，默认按扩展名推断")
    p.add_argument("--to", dest="target_format", help="目标格式，默认按扩展名推断")
    p.add_argument("--encoding", default="utf-8", help="文本编码")
    ns = p.parse_args()
    return C.run_data_convert(ns)


if __name__ == "__main__":
    sys.exit(main())
