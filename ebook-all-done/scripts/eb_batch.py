#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""eb-batch：对目录里的全部 EPUB 批量执行 inspect / validate / extract。"""
import argparse
import glob
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eb_common import (conflict_dir, json_dump, result, safe_name,
                       setup_stdout, EXIT_USAGE)

HERE = os.path.dirname(os.path.abspath(__file__))
ACTIONS = {
    "inspect": ("eb_inspect.py", "inspect.json"),
    "validate": ("eb_validate.py", "validate.json"),
    "extract": ("eb_extract.py", "extract"),
}


def main():
    setup_stdout()
    ap = argparse.ArgumentParser(description="批量处理 EPUB")
    ap.add_argument("--input", required=True, help="含 EPUB 的目录")
    ap.add_argument("--output", required=True, help="输出目录")
    ap.add_argument("--action", choices=sorted(ACTIONS), default="inspect")
    ap.add_argument("--pattern", default="*.epub")
    ap.add_argument("--format", choices=["md", "txt"], default="md",
                    help="action=extract 时的正文格式")
    args = ap.parse_args()
    if not os.path.isdir(args.input):
        from eb_common import die
        die("输入目录不存在：%s" % args.input, 3)
    files = sorted(glob.glob(os.path.join(args.input, args.pattern)))
    files = [f for f in files if os.path.isfile(f)]
    if not files:
        from eb_common import die
        die("目录里没有匹配 %s 的文件" % args.pattern, EXIT_USAGE)
    args.output = conflict_dir(args.output)
    if args.output is None:
        print("已跳过（输出目录已存在，EBOOK_ON_CONFLICT=skip）")
        return 0
    os.makedirs(args.output, exist_ok=True)
    script, tail = ACTIONS[args.action]
    rows = []
    for path in files:
        stem = safe_name(os.path.splitext(os.path.basename(path))[0], 50)
        target = os.path.join(args.output, stem, tail)
        cmd = [sys.executable, os.path.join(HERE, script),
               "--input", os.path.abspath(path), "--output", os.path.abspath(target)]
        if args.action == "extract":
            cmd += ["--format", args.format]
        t0 = time.time()
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
        dt = round(time.time() - t0, 2)
        ok = proc.returncode == 0
        rows.append({"file": os.path.abspath(path), "output": os.path.abspath(target),
                     "status": "PASS" if ok else "FAIL", "rc": proc.returncode,
                     "seconds": dt,
                     "tail": (proc.stdout or "").strip().splitlines()[-2:]})
        print("  %-8s %5.2fs %s" % ("PASS" if ok else "FAIL", dt,
                                     os.path.basename(path)))
    passed = sum(1 for r in rows if r["status"] == "PASS")
    payload = {"action": args.action, "input": os.path.abspath(args.input),
               "total": len(rows), "passed": passed, "failed": len(rows) - passed,
               "results": rows}
    json_dump(os.path.join(args.output, "manifest.json"), payload)
    print("汇总：%d 成功 / %d 失败 / 共 %d" %
          (passed, len(rows) - passed, len(rows)))
    result(os.path.join(args.output, "manifest.json"), 成功=passed,
           失败=len(rows) - passed)
    return 0 if passed else 5


if __name__ == "__main__":
    sys.exit(main())
