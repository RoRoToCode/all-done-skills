#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""压缩包全搞定 · 统一入口。

动作清单的唯一数据源是 assets/actions.json；run 把其余参数原样透传给
scripts/<动作 id 下划线形式>.py。
"""
import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arc_common as ac

HERE = os.path.dirname(os.path.abspath(__file__))
REGISTRY = os.path.join(HERE, "..", "assets", "actions.json")


def load():
    with open(REGISTRY, encoding="utf-8") as f:
        return json.load(f)


def find(data, action_id):
    for a in data["actions"]:
        if a["id"] == action_id:
            return a
    return None


def cmd_list(args):
    data = load()
    if args.json:
        print(json.dumps({"version": data["version"],
                          "actions": data["actions"]},
                         ensure_ascii=False, indent=2))
        return 0
    print("压缩包全搞定 — %d 个动作（v%s，纯本地）："
          % (len(data["actions"]), data["version"]))
    for a in data["actions"]:
        print("  %-14s %-16s %s" % (a["id"], a["name"], a["desc"]))
    return 0


def cmd_describe(args):
    data = load()
    a = find(data, args.id)
    if not a:
        print("未知动作 id: %s（用 list 查看）" % args.id, file=sys.stderr)
        return ac.EXIT_USAGE
    print("%s — %s" % (a["id"], a["name"]))
    print("  说明: %s" % a["desc"])
    print("  分组: %s" % a["group"])
    print("  依赖: %s" % ", ".join(a["deps"]))
    if a.get("optional"):
        print("  可选: %s" % ", ".join(a["optional"]))
    if a.get("notes"):
        print("  备注: %s" % a["notes"])
    print("  在线兜底: 无（压缩包不上传第三方）")
    return 0


def cmd_check(_args):
    data = load()
    rc = ac.check_deps()
    print("\n动作清单共 %d 项，全部可在纯标准库下运行。"
          % len(data["actions"]))
    return rc


def cmd_run(args):
    data = load()
    if not find(data, args.id):
        print("未知动作 id: %s（用 list 查看）" % args.id, file=sys.stderr)
        return ac.EXIT_USAGE
    script = os.path.join(HERE, args.id.replace("-", "_") + ".py")
    if not os.path.exists(script):
        print("动作脚本未找到：%s" % script, file=sys.stderr)
        return ac.EXIT_IO
    try:
        return subprocess.run([sys.executable, script] + args.rest).returncode
    except KeyboardInterrupt:
        return 130


def main():
    p = argparse.ArgumentParser(prog="actions", description="压缩包全搞定 统一入口")
    sub = p.add_subparsers(dest="cmd", required=True)

    l = sub.add_parser("list", help="列出全部动作")
    l.add_argument("--json", action="store_true", help="输出 JSON")

    d = sub.add_parser("describe", help="查看动作详情")
    d.add_argument("id", help="动作 id")

    sub.add_parser("check", help="检查本机依赖")

    r = sub.add_parser("run", help="运行动作（参数透传给 scripts/<id>.py）")
    r.add_argument("id", help="动作 id")
    r.add_argument("rest", nargs=argparse.REMAINDER, help="传给动作脚本的参数")

    args = p.parse_args()
    try:
        return {"list": cmd_list, "describe": cmd_describe,
                "check": cmd_check, "run": cmd_run}[args.cmd](args)
    except ac.ArchiveError as exc:
        print("错误：%s" % exc, file=sys.stderr)
        return exc.code


if __name__ == "__main__":
    sys.exit(main())
