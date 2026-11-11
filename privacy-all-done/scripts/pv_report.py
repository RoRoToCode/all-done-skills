#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""扫描报告 · 把扫描结果汇总成 Markdown / HTML / JSON 报告，含按类型统计与文件分布

由家族生成器按统一模式生成；业务逻辑集中在 pv_common.py。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pv_common as C  # noqa: E402

C.main_guard()


def main():
    p = argparse.ArgumentParser(description="把扫描结果汇总成 Markdown / HTML / JSON 报告，含按类型统计与文件分布")
    p.add_argument("input", help="扫描结果 JSON")
    p.add_argument("-o", "--output", help="报告文件，省略则打印到 stdout")
    p.add_argument("--format", choices=["md", "html", "json"], default="md", help="报告格式")
    ns = p.parse_args()
    return C.run_pv_report(ns)


if __name__ == "__main__":
    sys.exit(main())
