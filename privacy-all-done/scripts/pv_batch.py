#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""目录批量 · 批量扫描或脱敏目录下匹配的文件，单份失败不中断，输出汇总报告

由家族生成器按统一模式生成；业务逻辑集中在 pv_common.py。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pv_common as C  # noqa: E402

C.main_guard()


def main():
    p = argparse.ArgumentParser(description="批量扫描或脱敏目录下匹配的文件，单份失败不中断，输出汇总报告")
    p.add_argument("input", help="源目录")
    p.add_argument("-o", "--output", help="输出目录")
    p.add_argument("--mode", choices=["scan", "redact"], default="scan", help="批量模式")
    p.add_argument("--types", help="只启用指定规则，逗号分隔")
    p.add_argument("--rules", help="自定义规则 JSON")
    p.add_argument("--pattern", default="*.txt", help="文件名 glob 过滤")
    p.add_argument("--recursive", action="store_true", help="递归子目录")
    p.add_argument("--apply", action="store_true", help="redact 模式真正写文件（默认预览）")
    ns = p.parse_args()
    return C.run_pv_batch(ns)


if __name__ == "__main__":
    sys.exit(main())
