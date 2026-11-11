#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""技能与动作清单 · 扫描技能根目录，列出全部已安装技能、版本与动作，支持表格或 JSON

由家族生成器按统一模式生成；业务逻辑集中在 pipe_common.py。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipe_common as C  # noqa: E402

C.main_guard()


def main():
    p = argparse.ArgumentParser(description="扫描技能根目录，列出全部已安装技能、版本与动作，支持表格或 JSON")
    p.add_argument("--skills-root", help="技能根目录，默认 ~/.workbuddy/skills")
    p.add_argument("-o", "--output", help="结果文件，省略则打印到 stdout")
    p.add_argument("--format", choices=["table", "json"], default="table", help="输出格式")
    ns = p.parse_args()
    return C.run_pipe_list(ns)


if __name__ == "__main__":
    sys.exit(main())
