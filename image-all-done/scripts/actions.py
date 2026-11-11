#!/usr/bin/env python3
"""统一入口：列出、查看、检查依赖、运行图片处理动作。

动作脚本命名约定：scripts/<动作 id>.py（id 见 assets/actions.json）。
run 子命令把其余参数原样透传给对应脚本。
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ACTIONS_JSON = os.path.join(HERE, "..", "assets", "actions.json")


def load_actions():
    with open(ACTIONS_JSON, encoding="utf-8") as f:
        return json.load(f)


def cmd_list(_):
    data = load_actions()
    print("图片全搞定 — %d 个动作：" % len(data["actions"]))
    for a in data["actions"]:
        print("  %-14s %s  ·  %s" % (a["id"], a["name"], a["desc"]))


def cmd_describe(args):
    data = load_actions()
    hit = next((a for a in data["actions"] if a["id"] == args.id), None)
    if not hit:
        print("未知动作 id: %s" % args.id, file=sys.stderr)
        return 1
    print("%s — %s" % (hit["id"], hit["name"]))
    print("  说明: %s" % hit["desc"])
    print("  依赖: %s" % ", ".join(hit["deps"]))
    return 0


def cmd_check(_):
    data = load_actions()
    import platform
    print("解释器: %s (Python %s)" % (sys.executable, platform.python_version()))
    print("依赖检查：")
    needed = set()
    for a in data["actions"]:
        needed.update(a["deps"])
    optional = {"rembg", "realesrgan", "pytesseract", "rapidocr_onnxruntime"}
    missing = []
    for d in sorted(needed):
        try:
            __import__(d)
            print("  [已装] %s" % d)
        except Exception:
            if d in optional:
                print("  [可选] %s  未装（只影响对应动作，核心功能不受影响）" % d)
            else:
                missing.append(d)
                print("  [缺失] %s  →  %s -m pip install %s" % (d, sys.executable, d))
    print("  OCR 引擎: tesseract=%s | rapidocr=%s" % (
        shutil.which("tesseract") or "缺",
        "已装" if _has_module("rapidocr_onnxruntime") else "缺"))
    if missing:
        print("提示：用当前解释器安装才可见，换解释器重装无效。")
    return 0


def _has_module(name):
    try:
        __import__(name)
        return True
    except Exception:
        return False


def cmd_online(args):
    data = load_actions()
    if args.id:
        hit = next((a for a in data["actions"] if a["id"] == args.id), None)
        if not hit:
            print("未知动作 id: %s" % args.id, file=sys.stderr)
            return 1
        url = hit.get("online")
        print("%s 在线替代: %s" % (hit["id"], url or
                                   "无（该站无对应工具，请本地处理或安装依赖）"))
        return 0
    for a in data["actions"]:
        print("%-16s %s" % (a["id"], a.get("online") or "无（roroto.com 无对应工具）"))
    return 0


def cmd_run(args):
    # 动作 id 用连字符（img-convert），脚本文件用下划线（img_convert.py）
    script = os.path.join(HERE, args.id.replace("-", "_") + ".py")
    if not os.path.exists(script):
        print("动作脚本未实现或未找到：%s" % args.id, file=sys.stderr)
        print("可用: python scripts/actions.py list", file=sys.stderr)
        return 1
    cmd = [sys.executable, script] + args.rest
    return subprocess.run(cmd).returncode


def main():
    p = argparse.ArgumentParser(prog="actions", description="图片全搞定 统一入口")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="列出全部动作")
    sub.add_parser("check", help="检查本机依赖")

    d = sub.add_parser("describe", help="查看动作详情")
    d.add_argument("id", help="动作 id")

    o = sub.add_parser("online", help="查看对应的在线工具")
    o.add_argument("id", nargs="?", help="动作 id，省略则列出全部")

    r = sub.add_parser("run", help="运行动作（参数透传给 scripts/<id>.py）")
    r.add_argument("id", help="动作 id")
    r.add_argument("rest", nargs=argparse.REMAINDER, help="传给动作脚本的参数")

    args = p.parse_args()
    fn = {
        "list": cmd_list,
        "describe": cmd_describe,
        "check": cmd_check,
        "online": cmd_online,
        "run": cmd_run,
    }[args.cmd]
    return fn(args)


if __name__ == "__main__":
    sys.exit(main())
