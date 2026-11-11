#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""多表合并 · 按行拼接多个数据文件，或按指定键做左连接

由家族生成器按统一模式生成；业务逻辑集中在 data_common.py。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import data_common as C  # noqa: E402

C.main_guard()


def main():
    p = argparse.ArgumentParser(description="按行拼接多个数据文件，或按指定键做左连接")
    p.add_argument("--inputs", nargs="+", required=True, help="多个源文件")
    p.add_argument("-o", "--output", help="输出文件")
    p.add_argument("--to", dest="target_format", help="目标格式，默认按扩展名推断")
    p.add_argument("--by", help="连接键字段名，不给则按行拼接")
    p.add_argument("--how", choices=["concat", "left"], default="concat", help="合并方式")
    ns = p.parse_args()
    return C.run_data_merge(ns)


if __name__ == "__main__":
    sys.exit(main())
