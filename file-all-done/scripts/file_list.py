#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""目录清单 · 扫描目录生成文件清单（路径/体积/时间/扩展名/类型），支持 glob 过滤、排序、JSON/CSV/Markdown 输出与汇总统计

由家族生成器按统一模式生成；业务逻辑集中在 file_common.py。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import file_common as C  # noqa: E402

C.main_guard()


def main():
    p = argparse.ArgumentParser(description="扫描目录生成文件清单（路径/体积/时间/扩展名/类型），支持 glob 过滤、排序、JSON/CSV/Markdown 输出与汇总统计")
    p.add_argument("input", help="要扫描的目录")
    p.add_argument("-o", "--output", help="结果文件，省略则打印到 stdout")
    p.add_argument("--format", choices=["json", "csv", "md"], default="json", help="输出格式")
    p.add_argument("--recursive", action="store_true", help="递归子目录")
    p.add_argument("--pattern", default="*", help="文件名 glob 过滤")
    p.add_argument("--sort", choices=["name", "size", "mtime"], default="name", help="排序键")
    p.add_argument("--limit", type=int, default=0, help="最多列出条数，0 表示不限")
    p.add_argument("--include-hidden", action="store_true", help="包含隐藏文件")
    ns = p.parse_args()
    return C.run_file_list(ns)


if __name__ == "__main__":
    sys.exit(main())
