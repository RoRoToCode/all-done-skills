#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""定义校验 · 校验流水线 JSON：技能/动作是否存在、变量引用是否合法、有无循环或超限

由家族生成器按统一模式生成；业务逻辑集中在 pipe_common.py。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipe_common as C  # noqa: E402

C.main_guard()


def main():
    p = argparse.ArgumentParser(description="校验流水线 JSON：技能/动作是否存在、变量引用是否合法、有无循环或超限")
    p.add_argument("input", help="流水线定义 JSON")
    p.add_argument("--skills-root", help="技能根目录")
    p.add_argument("-o", "--output", help="校验报告，省略则打印到 stdout")
    ns = p.parse_args()
    return C.run_pipe_validate(ns)


if __name__ == "__main__":
    sys.exit(main())
