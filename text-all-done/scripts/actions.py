#!/usr/bin/env python3
"""统一入口：列出、查看、检查依赖、运行文本处理动作。

动作脚本命名约定：scripts/<动作 id 去掉连字符>.py（id 见 assets/actions.json）。
run 子命令把其余参数原样透传给对应脚本。

check 会先报告**当前解释器**：本技能的依赖全在标准库，真正的坑是「用了另一个
Python 去调」，所以把 sys.executable 打出来比列一堆"已装"更有用。
"""

import argparse
import json
import os
import platform
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ACTIONS_JSON = os.path.join(HERE, "..", "assets", "actions.json")


def load_actions():
    with open(ACTIONS_JSON, encoding="utf-8") as fh:
        return json.load(fh)


def cmd_list(_):
    data = load_actions()
    print("文本全搞定 — %d 个动作：" % len(data["actions"]))
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
    print("  依赖: %s" % (", ".join(hit["deps"]) or "无（仅标准库）"))
    return 0


def cmd_check(_):
    data = load_actions()
    print("解释器: %s (Python %s, %s)" % (sys.executable,
                                          platform.python_version(),
                                          platform.system()))
    print("依赖检查：")
    needed = set()
    for a in data["actions"]:
        needed.update(a["deps"])
    if not needed:
        print("  [就绪] 全部动作仅用标准库，无需安装第三方包")
    for dep in sorted(needed):
        try:
            __import__(dep)
            print("  [已装] %s" % dep)
        except Exception:  # noqa: BLE001 - report any import failure
            print("  [缺失] %s  →  %s -m pip install %s"
                  % (dep, sys.executable, dep))
    print("共 %d 个动作，%d 项第三方依赖" % (len(data["actions"]), len(needed)))
    return 0


def cmd_online(args):
    data = load_actions()
    if args.id:
        hit = next((a for a in data["actions"] if a["id"] == args.id), None)
        if not hit:
            print("未知动作 id: %s" % args.id, file=sys.stderr)
            return 1
        print("%s 在线替代: %s" % (hit["id"], hit.get("online")
                                   or "无（本技能不提供在线替代方案）"))
        return 0
    for a in data["actions"]:
        print("%-16s %s" % (a["id"], a.get("online")
                            or "无（本技能不提供在线替代方案）"))
    return 0


def cmd_run(args):
    script = os.path.join(HERE, args.id.replace("-", "_") + ".py")
    if not os.path.exists(script):
        print("动作脚本未实现或未找到：%s" % args.id, file=sys.stderr)
        print("可用: python scripts/actions.py list", file=sys.stderr)
        return 1
    cmd = [sys.executable, script] + args.rest
    return subprocess.run(cmd).returncode


def main():
    p = argparse.ArgumentParser(prog="actions", description="文本全搞定 统一入口")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="列出全部动作")
    sub.add_parser("check", help="检查本机依赖与解释器")

    d = sub.add_parser("describe", help="查看动作详情")
    d.add_argument("id", help="动作 id")

    o = sub.add_parser("online", help="查看对应的在线工具")
    o.add_argument("id", nargs="?", help="动作 id，省略则列出全部")

    r = sub.add_parser("run", help="运行动作（参数透传给 scripts/<id>.py）")
    r.add_argument("id", help="动作 id")
    r.add_argument("rest", nargs=argparse.REMAINDER, help="传给动作脚本的参数")

    args = p.parse_args()
    fn = {"list": cmd_list, "describe": cmd_describe, "check": cmd_check,
          "online": cmd_online, "run": cmd_run}[args.cmd]
    return fn(args)


if __name__ == "__main__":
    sys.exit(main())
