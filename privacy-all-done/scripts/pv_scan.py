#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""敏感信息扫描 · 扫描文本里的手机号/身份证/邮箱/银行卡/IP 等，按类型汇总并给出掩码后的命中位置

由家族生成器按统一模式生成；业务逻辑集中在 pv_common.py。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pv_common as C  # noqa: E402

C.main_guard()


def main():
    p = argparse.ArgumentParser(description="扫描文本里的手机号/身份证/邮箱/银行卡/IP 等，按类型汇总并给出掩码后的命中位置")
    p.add_argument("input", help="文本文件")
    p.add_argument("-o", "--output", help="结果文件，省略则打印到 stdout")
    p.add_argument("--types", help="只启用指定规则，逗号分隔")
    p.add_argument("--rules", help="自定义规则 JSON")
    p.add_argument("--context", type=int, default=0, help="附带上下文字符数")
    p.add_argument("--encoding", help="强制指定编码，默认自动嗅探")
    ns = p.parse_args()
    return C.run_pv_scan(ns)


if __name__ == "__main__":
    sys.exit(main())
