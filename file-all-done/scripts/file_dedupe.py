#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重复文件查找 · 按体积分组后算内容哈希，输出重复组与可释放体积，只报告不删除

由家族生成器按统一模式生成；业务逻辑集中在 file_common.py。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import file_common as C  # noqa: E402

C.main_guard()


def main():
    p = argparse.ArgumentParser(description="按体积分组后算内容哈希，输出重复组与可释放体积，只报告不删除")
    p.add_argument("input", help="要扫描的目录")
    p.add_argument("-o", "--output", help="报告文件，省略则打印到 stdout")
    p.add_argument("--algo", choices=["sha256", "md5", "blake2b"], default="sha256", help="哈希算法")
    p.add_argument("--min-size", type=int, default=1, help="忽略小于该体积（字节）的文件")
    p.add_argument("--pattern", default="*", help="文件名 glob 过滤")
    p.add_argument("--recursive", action="store_true", help="递归子目录")
    ns = p.parse_args()
    return C.run_file_dedupe(ns)


if __name__ == "__main__":
    sys.exit(main())
