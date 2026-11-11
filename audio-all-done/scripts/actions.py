#!/usr/bin/env python3
"""统一入口：列出、查看、检查依赖、运行音频处理动作。

动作脚本命名约定：scripts/<动作 id>.py（id 见 assets/actions.json）。
run 子命令把其余参数原样透传给对应脚本。

依赖分两类：
  - Python 模块：用 import 探测；
  - 外部二进制（ffmpeg / ffprobe）：用 shutil.which 探测。
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ACTIONS_JSON = os.path.join(HERE, "..", "assets", "actions.json")

BINARY_DEPS = {"ffmpeg", "ffprobe"}
COMMON_MODULE = "aud_common"


def load_actions():
    with open(ACTIONS_JSON, encoding="utf-8") as f:
        return json.load(f)


def cmd_list(_):
    data = load_actions()
    print("音频全搞定 — %d 个动作：" % len(data["actions"]))
    for a in data["actions"]:
        print("  %-16s %s  ·  %s" % (a["id"], a["name"], a["desc"]))


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


def _check_dep(dep):
    if dep in BINARY_DEPS:
        try:
            common = __import__(COMMON_MODULE)
            return (common.ffmpeg_path() if dep == "ffmpeg"
                    else common.ffprobe_path())
        except Exception:
            return shutil.which(dep) or shutil.which(dep + ".exe")
    try:
        __import__(dep)
        return "module"
    except Exception:
        return None


def cmd_check(_):
    data = load_actions()
    import platform
    print("解释器: %s (Python %s)" % (sys.executable, platform.python_version()))
    print("依赖检查：")
    needed = []
    for a in data["actions"]:
        for d in a["deps"]:
            if d not in needed:
                needed.append(d)
    for d in needed:
        if d in BINARY_DEPS:
            path = _check_dep(d)
            if path:
                print("  [已装] %s  (%s)" % (d, path))
            elif d == "ffprobe":
                print("  [可选] ffprobe  缺失（已用 ffmpeg 解析兜底，"
                      "只影响元信息精度）")
            else:
                print("  [缺失] %s  （需加入 PATH 或放到 ~/.workbuddy/bin）" % d)
        else:
            ok = _check_dep(d)
            print("  [%s] %s" % ("已装" if ok else "缺失", d))
    if not _check_dep("ffmpeg"):
        print("提示：python -m pip install imageio-ffmpeg（自带 ffmpeg 二进制）"
              "，或 winget install Gyan.FFmpeg")
    return 0


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
    # 动作 id 用连字符（aud-convert），脚本文件用下划线（aud_convert.py）
    script = os.path.join(HERE, args.id.replace("-", "_") + ".py")
    if not os.path.exists(script):
        print("动作脚本未实现或未找到：%s" % args.id, file=sys.stderr)
        print("可用: python scripts/actions.py list", file=sys.stderr)
        return 1
    cmd = [sys.executable, script] + args.rest
    return subprocess.run(cmd).returncode


def main():
    p = argparse.ArgumentParser(prog="actions", description="音频全搞定 统一入口")
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
