#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""规则集管理 · 列出内置规则与样例，或校验并加载自定义规则 JSON

由家族生成器按统一模式生成；业务逻辑集中在 pv_common.py。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pv_common as C  # noqa: E402

C.main_guard()


def main():
    p = argparse.ArgumentParser(description="列出内置规则与样例，或校验并加载自定义规则 JSON")
    p.add_argument("-o", "--output", help="结果文件，省略则打印到 stdout")
    p.add_argument("--rules", help="自定义规则 JSON，给出时会做校验")
    p.add_argument("--type", help="只看某条规则的详情")
    ns = p.parse_args()
    return C.run_pv_rules(ns)


if __name__ == "__main__":
    sys.exit(main())
