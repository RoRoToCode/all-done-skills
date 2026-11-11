#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据全搞定 · 统一入口。

动作清单的唯一数据源是 assets/actions.json；run 把其余参数原样透传给
scripts/<动作 id 下划线形式>.py。check 第一行打印当前解释器，避免
「包装在 A 解释器、技能被 B 解释器调用」造成的凭空失败。
"""
import argparse
import json
import os
import platform
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REGISTRY = os.path.join(HERE, "..", "assets", "actions.json")
DISPLAY = "数据全搞定"


def load():
    with open(REGISTRY, encoding="utf-8") as fh:
        return json.load(fh)


def find(data, action_id):
    return next((a for a in data["actions"] if a["id"] == action_id), None)


def cmd_list(args):
    data = load()
    if args.json:
        print(json.dumps({"version": data["version"], "actions": data["actions"]},
                         ensure_ascii=False, indent=2))
        return 0
    print("%s — %d 个动作（v%s，纯本地）：" % (DISPLAY, len(data["actions"]), data["version"]))
    for a in data["actions"]:
        print("  %-16s %-14s %s" % (a["id"], a["name"], a["desc"]))
    return 0


def cmd_describe(args):
    data = load()
    a = find(data, args.id)
    if not a:
        print("未知动作 id: %s（用 list 查看）" % args.id, file=sys.stderr)
        return 2
    print("%s — %s" % (a["id"], a["name"]))
    print("  说明: %s" % a["desc"])
    print("  分组: %s" % a.get("group", "-"))
    print("  依赖: %s" % (", ".join(a.get("deps", [])) or "无（仅标准库）"))
    if a.get("optional"):
        print("  可选: %s" % ", ".join(a["optional"]))
    print("  在线替代: 无（本技能不提供在线替代方案）")
    return 0


def cmd_check(_args):
    data = load()
    print("解释器: %s (Python %s, %s)" % (sys.executable,
                                            platform.python_version(),
                                            platform.system()))
    needed = sorted({d for a in data["actions"] for d in a.get("deps", [])})
    optional = sorted({d for a in data["actions"] for d in a.get("optional", [])})
    if not needed:
        print("  [就绪] 全部动作的必需依赖为 Python 标准库，无需安装第三方包")
    for dep in needed:
        try:
            __import__(dep)
            print("  [已装] %s" % dep)
        except Exception:  # noqa: BLE001
            print("  [缺失] %s  →  %s -m pip install %s" % (dep, sys.executable, dep))
    for dep in optional:
        try:
            __import__(dep)
            print("  [可选已装] %s" % dep)
        except Exception:  # noqa: BLE001
            print("  [可选未装] %s → 未安装时该动作会给出本地安装指引，不影响其它动作" % dep)
    print("共 %d 个动作，必需第三方依赖 %d 项，可选 %d 项"
          % (len(data["actions"]), len(needed), len(optional)))
    return 0


def cmd_online(args):
    data = load()
    if args.id and not find(data, args.id):
        print("未知动作 id: %s" % args.id, file=sys.stderr)
        return 2
    print("无（本技能不提供在线替代方案，原始文件不上传任何第三方服务器）")
    return 0


def cmd_run(args):
    data = load()
    if not find(data, args.id):
        print("未知动作 id: %s（用 list 查看）" % args.id, file=sys.stderr)
        return 2
    script = os.path.join(HERE, args.id.replace("-", "_") + ".py")
    if not os.path.exists(script):
        print("动作脚本未找到：%s" % script, file=sys.stderr)
        return 2
    return subprocess.run([sys.executable, script] + args.rest).returncode


def main():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except Exception:  # noqa: BLE001
            pass
    p = argparse.ArgumentParser(prog="actions", description=DISPLAY + " 统一入口")
    sub = p.add_subparsers(dest="cmd", required=True)

    lp = sub.add_parser("list", help="列出全部动作")
    lp.add_argument("--json", action="store_true", help="机器可读清单")
    sub.add_parser("check", help="检查解释器与依赖状态")
    d = sub.add_parser("describe", help="查看动作详情")
    d.add_argument("id")
    o = sub.add_parser("online", help="查看在线替代（本技能一律返回无）")
    o.add_argument("id", nargs="?")
    r = sub.add_parser("run", help="运行动作（参数透传给 scripts/<id>.py）")
    r.add_argument("id")
    r.add_argument("rest", nargs=argparse.REMAINDER)

    args = p.parse_args()
    return {"list": cmd_list, "describe": cmd_describe, "check": cmd_check,
            "online": cmd_online, "run": cmd_run}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
