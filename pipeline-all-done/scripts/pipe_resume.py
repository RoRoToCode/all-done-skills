#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""断点续跑 · 读取运行目录的 state.json，从第一个未完成步骤继续执行

由家族生成器按统一模式生成；业务逻辑集中在 pipe_common.py。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipe_common as C  # noqa: E402

C.main_guard()


def main():
    p = argparse.ArgumentParser(description="读取运行目录的 state.json，从第一个未完成步骤继续执行")
    p.add_argument("input", help="运行目录或其中的 state.json")
    p.add_argument("--skills-root", help="技能根目录")
    p.add_argument("--timeout", type=int, default=1800, help="单步超时秒数")
    ns = p.parse_args()
    return C.run_pipe_resume(ns)


if __name__ == "__main__":
    sys.exit(main())
