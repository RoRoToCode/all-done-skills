#!/usr/bin/env python3
"""统一入口：列出、查看、运行提示词读取动作。

动作脚本命名约定：scripts/<动作 id 的连字符换下划线>.py（id 见 assets/actions.json）。
run 子命令把其余参数原样透传给对应脚本。
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ACTIONS_JSON = os.path.join(HERE, "..", "assets", "actions.json")


def load_actions():
    with open(ACTIONS_JSON, encoding="utf-8") as f:
        return json.load(f)


def cmd_list(_):
    data = load_actions()
    print("%s — %d 个动作：" % (data["display_name"], len(data["actions"])))
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
    print("  依赖: %s" % (", ".join(hit["deps"]) or "无（纯标准库）"))
    return 0


def cmd_check(_):
    data = load_actions()
    print("依赖检查：")
    print("  Python %s" % sys.version.split()[0])
    print("  [就绪] 标准库（png/jpeg/webp 头解析、json、zlib）—— 本技能不需要任何第三方包")
    missing = [d for d in {d for a in data["actions"] for d in a["deps"]} if d]
    print("  第三方依赖: %s" % (", ".join(sorted(missing)) if missing else "无"))
    return 0


def cmd_online(args):
    data = load_actions()
    if args.id:
        hit = next((a for a in data["actions"] if a["id"] == args.id), None)
        if not hit:
            print("未知动作 id: %s" % args.id, file=sys.stderr)
            return 1
        print("%s 在线替代: %s" % (hit["id"], hit.get("online") or
                                   "无（该站无对应工具，请本地处理）"))
        return 0
    for a in data["actions"]:
        print("%-16s %s" % (a["id"], a.get("online") or "无（roroto.com 无对应工具）"))
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
    p = argparse.ArgumentParser(prog="actions", description="AI 提示词取回 统一入口")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="列出全部动作")
    sub.add_parser("check", help="检查本机环境")

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
