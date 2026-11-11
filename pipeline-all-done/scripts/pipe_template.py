#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成模板 · 生成内置流水线定义模板：scan2md / web2ebook / office2pdf / tidy2pdf

由家族生成器按统一模式生成；业务逻辑集中在 pipe_common.py。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipe_common as C  # noqa: E402

C.main_guard()


def main():
    p = argparse.ArgumentParser(description="生成内置流水线定义模板：scan2md / web2ebook / office2pdf / tidy2pdf")
    p.add_argument("name", choices=["scan2md", "web2ebook", "office2pdf", "tidy2pdf", "all"], help="模板名")
    p.add_argument("-o", "--output", help="输出文件，省略则打印到 stdout")
    p.add_argument("--skills-root", help="技能根目录（用于校验步骤可用性）")
    ns = p.parse_args()
    return C.run_pipe_template(ns)


if __name__ == "__main__":
    sys.exit(main())
