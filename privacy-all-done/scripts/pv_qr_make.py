#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""二维码生成 · 用可选依赖 qrcode 生成 PNG/SVG 二维码，缺依赖时给本地安装指引

由家族生成器按统一模式生成；业务逻辑集中在 pv_common.py。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pv_common as C  # noqa: E402

C.main_guard()


def main():
    p = argparse.ArgumentParser(description="用可选依赖 qrcode 生成 PNG/SVG 二维码，缺依赖时给本地安装指引")
    p.add_argument("text", help="二维码内容")
    p.add_argument("-o", "--output", help="输出文件")
    p.add_argument("--size", type=int, default=10, help="box_size")
    p.add_argument("--format", choices=["png", "svg"], default="png", help="输出格式")
    ns = p.parse_args()
    return C.run_pv_qr_make(ns)


if __name__ == "__main__":
    sys.exit(main())
