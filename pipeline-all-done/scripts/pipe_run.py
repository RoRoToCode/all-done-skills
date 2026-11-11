#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""执行流水线 · 按定义逐步调用各技能统一入口，每步独立输出目录并写 manifest 与 state

由家族生成器按统一模式生成；业务逻辑集中在 pipe_common.py。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipe_common as C  # noqa: E402

C.main_guard()


def main():
    p = argparse.ArgumentParser(description="按定义逐步调用各技能统一入口，每步独立输出目录并写 manifest 与 state")
    p.add_argument("input", help="流水线定义 JSON")
    p.add_argument("--input", dest="pipeline_input", help="{{input}} 的实际路径")
    p.add_argument("--skills-root", help="技能根目录")
    p.add_argument("--workdir", help="运行父目录，默认 ./pipeline-runs")
    p.add_argument("--on-error", choices=["stop", "continue"], default="stop", help="失败策略")
    p.add_argument("--timeout", type=int, default=1800, help="单步超时秒数")
    p.add_argument("--dry-run", action="store_true", help="只打印将执行的命令，不落盘")
    ns = p.parse_args()
    return C.run_pipe_run(ns)


if __name__ == "__main__":
    sys.exit(main())
