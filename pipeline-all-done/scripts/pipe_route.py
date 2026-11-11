#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""请求路由 · 把一句自然语言请求按关键词打分，推荐最合适的技能与动作，只给建议不自动执行

由家族生成器按统一模式生成；业务逻辑集中在 pipe_common.py。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipe_common as C  # noqa: E402

C.main_guard()


def main():
    p = argparse.ArgumentParser(description="把一句自然语言请求按关键词打分，推荐最合适的技能与动作，只给建议不自动执行")
    p.add_argument("text", help="自然语言请求")
    p.add_argument("--skills-root", help="技能根目录")
    p.add_argument("--top", type=int, default=3, help="返回前 N 个候选")
    p.add_argument("-o", "--output", help="结果文件，省略则打印到 stdout")
    ns = p.parse_args()
    return C.run_pipe_route(ns)


if __name__ == "__main__":
    sys.exit(main())
