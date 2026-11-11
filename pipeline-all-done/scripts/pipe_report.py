#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成报告 · 把一次运行汇总为 Markdown / HTML / JSON 报告，含失败清单与产物索引

由家族生成器按统一模式生成；业务逻辑集中在 pipe_common.py。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipe_common as C  # noqa: E402

C.main_guard()


def main():
    p = argparse.ArgumentParser(description="把一次运行汇总为 Markdown / HTML / JSON 报告，含失败清单与产物索引")
    p.add_argument("input", help="运行目录")
    p.add_argument("-o", "--output", help="报告文件，省略则打印到 stdout")
    p.add_argument("--format", choices=["md", "html", "json"], default="md", help="报告格式")
    ns = p.parse_args()
    return C.run_pipe_report(ns)


if __name__ == "__main__":
    sys.exit(main())
