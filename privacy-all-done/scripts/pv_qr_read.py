#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""二维码识别 · 用可选依赖 pyzbar 或 opencv-python 识别图片里的二维码，缺依赖时给本地安装指引

由家族生成器按统一模式生成；业务逻辑集中在 pv_common.py。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pv_common as C  # noqa: E402

C.main_guard()


def main():
    p = argparse.ArgumentParser(description="用可选依赖 pyzbar 或 opencv-python 识别图片里的二维码，缺依赖时给本地安装指引")
    p.add_argument("input", nargs="+", help="图片文件，可给多个")
    p.add_argument("-o", "--output", help="结果文件，省略则打印到 stdout")
    ns = p.parse_args()
    return C.run_pv_qr_read(ns)


if __name__ == "__main__":
    sys.exit(main())
