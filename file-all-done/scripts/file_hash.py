#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""计算校验和 · 对文件或目录计算 sha256/md5/blake2b，输出可作为校验清单的 JSON

由家族生成器按统一模式生成；业务逻辑集中在 file_common.py。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import file_common as C  # noqa: E402

C.main_guard()


def main():
    p = argparse.ArgumentParser(description="对文件或目录计算 sha256/md5/blake2b，输出可作为校验清单的 JSON")
    p.add_argument("input", nargs="+", help="文件或目录，可给多个")
    p.add_argument("-o", "--output", help="校验清单文件，省略则打印到 stdout")
    p.add_argument("--algo", choices=["sha256", "md5", "blake2b"], default="sha256", help="哈希算法")
    p.add_argument("--pattern", default="*", help="文件名 glob 过滤")
    p.add_argument("--recursive", action="store_true", help="目录递归")
    ns = p.parse_args()
    return C.run_file_hash(ns)


if __name__ == "__main__":
    sys.exit(main())
