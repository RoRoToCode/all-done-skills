#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""统一入口：列出、查看、检查依赖、运行电子书处理动作。

动作脚本命名约定：scripts/<动作 id>.py（id 见 assets/actions.json）。
run 子命令把其余参数原样透传给对应脚本。
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ACTIONS_JSON = os.path.join(HERE, "..", "assets", "actions.json")

from eb_common import find_browser, find_calibre, setup_stdout  # noqa: E402

SPECIAL_DEPS = {"browser": find_browser, "ebook-convert": find_calibre}


def load_actions():
    with open(ACTIONS_JSON, encoding="utf-8") as f:
        return json.load(f)


def dep_path(dep):
    if dep in SPECIAL_DEPS:
        return SPECIAL_DEPS[dep]()
    try:
        __import__(dep)
        return "module"
    except Exception:
        return None


def cmd_list(_):
    data = load_actions()
    print("电子书全搞定 — %d 个动作：" % len(data["actions"]))
    for a in data["actions"]:
        dep = ",".join(a.get("deps") or []) or "标准库"
        print("  %-14s %-16s · %s  [%s]" % (a["id"], a["name"], a["desc"], dep))


def cmd_describe(args):
    data = load_actions()
    hit = next((a for a in data["actions"] if a["id"] == args.id), None)
    if not hit:
        print("未知动作 id: %s" % args.id, file=sys.stderr)
        return 1
    print("%s — %s" % (hit["id"], hit["name"]))
    print("  说明: %s" % hit["desc"])
    print("  必需依赖: %s" % (", ".join(hit.get("deps") or []) or "无（Python 标准库）"))
    print("  可选依赖: %s" % (", ".join(hit.get("optional") or []) or "无"))
    print("  在线替代: %s" % (hit.get("online") or "无（该站无对应工具，请本地处理）"))
    return 0


def cmd_check(_):
    data = load_actions()
    print("依赖检查：")
    needed, optional = [], []
    for a in data["actions"]:
        for d in a.get("deps") or []:
            if d not in needed:
                needed.append(d)
        for d in a.get("optional") or []:
            if d not in optional and d not in needed:
                optional.append(d)
    ok = True
    for d in needed + optional:
        p = dep_path(d)
        kind = "必需" if d in needed else "可选"
        print("  [%s] %-14s %-4s %s" % ("已装" if p else "缺失", d, kind,
                                          p if isinstance(p, str) and p != "module" else ""))
        if not p and d in needed:
            ok = False
    print("  核心 15 项动作只用 Python 标准库，无需安装任何第三方包。")
    print("  总体: %s" % ("必需依赖齐全" if ok else "部分动作缺依赖，详见 references/toolchain.md"))
    return 0


def cmd_online(args):
    data = load_actions()
    note = data.get("online_note", "")
    if args.id:
        hit = next((a for a in data["actions"] if a["id"] == args.id), None)
        if not hit:
            print("未知动作 id: %s" % args.id, file=sys.stderr)
            return 1
        print("%s 在线替代: 无（roroto.com 无电子书类工具，请本地处理）" % hit["id"])
        return 0
    print(note)
    for a in data["actions"]:
        print("%-16s %s" % (a["id"], "无"))
    return 0


def cmd_run(args):
    data = load_actions()
    hit = next((a for a in data["actions"] if a["id"] == args.id), None)
    if not hit:
        print("未知动作 id: %s" % args.id, file=sys.stderr)
        print("可用: python scripts/actions.py list", file=sys.stderr)
        return 1
    script = os.path.join(HERE, args.id.replace("-", "_") + ".py")
    if not os.path.exists(script):
        print("动作脚本未实现或未找到：%s" % args.id, file=sys.stderr)
        return 1
    # 默认无需逐项确认：统一识别 --on-conflict，转成环境变量传给动作脚本，
    # 这样 16 个动作都自动支持 rename / overwrite / skip，无需各自实现。
    rest = list(args.rest)
    env = os.environ.copy()
    if "--on-conflict" in rest:
        i = rest.index("--on-conflict")
        value = rest[i + 1] if i + 1 < len(rest) else ""
        if value not in ("rename", "overwrite", "skip"):
            print("--on-conflict 需要 rename / overwrite / skip", file=sys.stderr)
            return 2
        env["EBOOK_ON_CONFLICT"] = value
        del rest[i:i + 2]
    return subprocess.run([sys.executable, script] + rest, env=env).returncode


def main():
    setup_stdout()
    p = argparse.ArgumentParser(prog="actions", description="电子书全搞定 统一入口")
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
    return {"list": cmd_list, "describe": cmd_describe, "check": cmd_check,
            "online": cmd_online, "run": cmd_run}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
