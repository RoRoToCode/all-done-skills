#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""推断 Schema · 从记录列表推断字段类型与必填性，生成 JSON Schema draft-07 草案

由家族生成器按统一模式生成；业务逻辑集中在 data_common.py。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import data_common as C  # noqa: E402

C.main_guard()


def main():
    p = argparse.ArgumentParser(description="从记录列表推断字段类型与必填性，生成 JSON Schema draft-07 草案")
    p.add_argument("input", help="源文件")
    p.add_argument("-o", "--output", help="输出文件，省略则打印到 stdout")
    p.add_argument("--from", dest="source_format", help="强制指定格式")
    p.add_argument("--title", default="Records", help="schema 标题")
    ns = p.parse_args()
    return C.run_data_schema(ns)


if __name__ == "__main__":
    sys.exit(main())
