#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""文本脱敏 · 把命中内容按掩码、占位符或直接删除处理，另存新文件；不给 -o 只打印计划

由家族生成器按统一模式生成；业务逻辑集中在 pv_common.py。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pv_common as C  # noqa: E402

C.main_guard()


def main():
    p = argparse.ArgumentParser(description="把命中内容按掩码、占位符或直接删除处理，另存新文件；不给 -o 只打印计划")
    p.add_argument("input", help="文本文件")
    p.add_argument("-o", "--output", help="输出文件，省略则只预览")
    p.add_argument("--types", help="只启用指定规则，逗号分隔")
    p.add_argument("--rules", help="自定义规则 JSON")
    p.add_argument("--mode", choices=["mask", "placeholder", "remove"], default="mask", help="脱敏方式")
    p.add_argument("--encoding", help="强制指定编码，默认自动嗅探")
    p.add_argument("--dry-run", action="store_true", help="只预览，不写文件")
    ns = p.parse_args()
    return C.run_pv_redact(ns)


if __name__ == "__main__":
    sys.exit(main())
