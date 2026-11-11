#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""拆分成多份 · 按固定行数或某字段取值把大表拆成多份，并写 split-manifest.json

由家族生成器按统一模式生成；业务逻辑集中在 data_common.py。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import data_common as C  # noqa: E402

C.main_guard()


def main():
    p = argparse.ArgumentParser(description="按固定行数或某字段取值把大表拆成多份，并写 split-manifest.json")
    p.add_argument("input", help="源文件")
    p.add_argument("-o", "--output", help="输出目录")
    p.add_argument("--by", choices=["rows", "field"], default="rows", help="拆分依据")
    p.add_argument("--size", type=int, default=1000, help="每份行数")
    p.add_argument("--field", help="按字段取值拆分时的字段名")
    p.add_argument("--to", dest="target_format", default="csv", help="每份的输出格式")
    p.add_argument("--from", dest="source_format", help="强制指定源格式")
    ns = p.parse_args()
    return C.run_data_split(ns)


if __name__ == "__main__":
    sys.exit(main())
