#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按类型归类 · 按扩展名/日期/大类把文件复制到子目录，默认预览，--apply 才落盘，绝不移动或删除原文件

由家族生成器按统一模式生成；业务逻辑集中在 file_common.py。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import file_common as C  # noqa: E402

C.main_guard()


def main():
    p = argparse.ArgumentParser(description="按扩展名/日期/大类把文件复制到子目录，默认预览，--apply 才落盘，绝不移动或删除原文件")
    p.add_argument("input", help="源目录")
    p.add_argument("-o", "--output", help="目标目录")
    p.add_argument("--by", choices=["ext", "date", "type"], default="ext", help="归类依据")
    p.add_argument("--date-format", default="%Y-%m", help="按日期归类时的目录名格式")
    p.add_argument("--pattern", default="*", help="文件名 glob 过滤")
    p.add_argument("--recursive", action="store_true", help="递归子目录")
    p.add_argument("--apply", action="store_true", help="真正执行复制（默认只预览）")
    ns = p.parse_args()
    return C.run_file_organize(ns)


if __name__ == "__main__":
    sys.exit(main())
