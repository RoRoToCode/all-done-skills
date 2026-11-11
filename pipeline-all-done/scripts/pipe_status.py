#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""运行状态 · 读取 manifest 与 state，输出每步状态、耗时与产物路径摘要

由家族生成器按统一模式生成；业务逻辑集中在 pipe_common.py。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipe_common as C  # noqa: E402

C.main_guard()


def main():
    p = argparse.ArgumentParser(description="读取 manifest 与 state，输出每步状态、耗时与产物路径摘要")
    p.add_argument("input", help="运行目录")
    p.add_argument("-o", "--output", help="结果文件，省略则打印到 stdout")
    ns = p.parse_args()
    return C.run_pipe_status(ns)


if __name__ == "__main__":
    sys.exit(main())
