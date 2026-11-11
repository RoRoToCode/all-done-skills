#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""复核校验和 · 按 JSON 清单或 sha256sum 文本重新计算，逐条给出 ok / mismatch / missing

由家族生成器按统一模式生成；业务逻辑集中在 file_common.py。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import file_common as C  # noqa: E402

C.main_guard()


def main():
    p = argparse.ArgumentParser(description="按 JSON 清单或 sha256sum 文本重新计算，逐条给出 ok / mismatch / missing")
    p.add_argument("input", help="校验清单（JSON 或 sha256sum 文本）")
    p.add_argument("-o", "--output", help="结果文件，省略则打印到 stdout")
    p.add_argument("--algo", choices=["sha256", "md5", "blake2b"], default="sha256", help="哈希算法")
    p.add_argument("--root", help="相对路径的基准目录，默认清单所在目录")
    ns = p.parse_args()
    return C.run_file_verify(ns)


if __name__ == "__main__":
    sys.exit(main())
