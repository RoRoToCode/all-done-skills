#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量重命名 · 按前缀/后缀/序号/正则批量生成新名，默认只预览计划，--apply 才落盘并写 rename-map.json

由家族生成器按统一模式生成；业务逻辑集中在 file_common.py。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import file_common as C  # noqa: E402

C.main_guard()


def main():
    p = argparse.ArgumentParser(description="按前缀/后缀/序号/正则批量生成新名，默认只预览计划，--apply 才落盘并写 rename-map.json")
    p.add_argument("input", help="要处理的目录")
    p.add_argument("-o", "--output", help="计划文件路径，默认打印到 stdout")
    p.add_argument("--prefix", default="", help="统一前缀")
    p.add_argument("--suffix", default="", help="统一后缀（加在扩展名前）")
    p.add_argument("--replace", help="对主文件名做正则替换的表达式")
    p.add_argument("--with", dest="replacement", default="", help="正则替换的目标文本")
    p.add_argument("--seq", action="store_true", help="附加递增序号")
    p.add_argument("--start", type=int, default=1, help="序号起始值")
    p.add_argument("--pattern", default="*", help="文件名 glob 过滤")
    p.add_argument("--recursive", action="store_true", help="递归子目录")
    p.add_argument("--apply", action="store_true", help="真正执行重命名（默认只预览）")
    ns = p.parse_args()
    return C.run_file_rename(ns)


if __name__ == "__main__":
    sys.exit(main())
