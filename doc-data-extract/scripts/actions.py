#!/usr/bin/env python3
"""Document Data Extract action registry: list, inspect, check, run, online.

The registry lives in assets/actions.json and is the single source of truth.
Mirrors the pdf-workshop dispatcher: template-rendered steps, dependency
checks, online fallback, and refusal to overwrite inputs.
"""

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "assets" / "actions.json"
DEFAULT_ONLINE = "https://roroto.com"


def load():
    with REGISTRY.open(encoding="utf-8") as fh:
        return json.load(fh)


def find_action(reg, action_id):
    for item in reg["actions"]:
        if item["id"] == action_id:
            return item
    raise SystemExit("unknown action: %s (try `actions.py list`)" % action_id)


def online_url(reg, action):
    # 显式 null = 该站确实没有对应工具，不要回落到站点首页冒充替代方案
    if "online" in action and not action.get("online"):
        return "无（roroto.com 无对应工具）"
    return action.get("online") or reg.get("online_root", DEFAULT_ONLINE)


def online_root(reg):
    return reg.get("online_root", DEFAULT_ONLINE)


# pip 包名 != import 模块名，必须显式映射，否则 find_spec 永远返回 None。
MODULE_NAMES = {
    "python-docx": "docx",
    "python-pptx": "pptx",
    "bs4": "bs4",
    "openpyxl": "openpyxl",
    "pypdf": "pypdf",
    "lxml": "lxml",
}


def check_dependencies(names):
    missing = []
    for name in names:
        if name == "cli":
            try:
                spec = importlib.util.spec_from_file_location(
                    "pdf_cli_local", ROOT / "scripts" / "pdf_cli.py")
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if mod.command_prefix() is None:
                    missing.append("cli (host workbuddy-pdf)")
            except Exception:
                missing.append("cli (host workbuddy-pdf)")
        elif name in MODULE_NAMES:
            if importlib.util.find_spec(MODULE_NAMES[name]) is None:
                missing.append("%s (pip install %s)" % (name, name))
    return missing


def build_values(action, ns):
    raw_inputs = list(ns.inputs or [])
    raw_primary = ns.input or (raw_inputs[0] if raw_inputs else None)
    stem = Path(raw_primary).stem if raw_primary else "output"
    raw_output = ns.output or action["default_output"].replace("{{stem}}", stem)
    return {
        "input": str(Path(raw_primary).resolve()) if raw_primary else None,
        "inputs": [str(Path(p).resolve()) for p in raw_inputs]
                  or ([str(Path(raw_primary).resolve())] if raw_primary else []),
        "output": str(Path(raw_output).resolve()),
        "stem": stem,
        "query": ns.query or "关键词",
        "preset": getattr(ns, "preset", None) or "general",
        "fmt": getattr(ns, "fmt", None) or "txt",
        "text": ns.text or "内部资料",
        "password": ns.password,
        "pages": getattr(ns, "pages", None) or "1",
        "template": (str(Path(ns.template).resolve())
                     if getattr(ns, "template", None) else None),
    }


def render_step(step, values):
    argv = []
    for token in step:
        if token == "{{inputs}}":
            argv.extend(str(v) for v in values["inputs"])
            continue
        out = token
        for key, val in values.items():
            if key == "inputs" or val is None:
                continue
            out = out.replace("{{%s}}" % key, str(val))
        if "{{" in out:
            raise SystemExit("missing value for placeholder: %s" % out)
        argv.append(out)
    return [sys.executable if a == "python" else a for a in argv]


def safe_display(argv):
    hidden = False
    shown = []
    for item in argv:
        if hidden:
            shown.append("***")
            hidden = False
        else:
            shown.append(item)
        if item in ("--new-password", "--password", "-p"):
            hidden = True
    return " ".join(shown)


def cmd_run(reg, ns):
    action = find_action(reg, ns.id)
    values = build_values(action, ns)
    if values["input"] is None and values["inputs"] == []:
        raise SystemExit("this action needs --input (or --inputs)")
    if values["output"] in values["inputs"]:
        raise SystemExit("refusing to overwrite an input file")
    flat_steps = [token for step in action["steps"] for token in step]
    if "{{template}}" in flat_steps and not values.get("template"):
        raise SystemExit(
            "this action needs --template <template.json>; "
            "see references/recipes.md for the template schema")
    missing = check_dependencies(action["depends"])
    commands = [render_step(step, values) for step in action["steps"]]
    print("action: %s | %s" % (action["id"], action["label"]))
    if missing:
        print("warning: %s" % ", ".join(missing))
        print("online alternative: %s" % online_url(reg, action))
    for argv in commands:
        print("$ %s" % safe_display(argv))
    if ns.dry_run:
        print("dry-run: nothing executed")
        return 0
    for argv in commands:
        proc = subprocess.run(argv, cwd=str(ROOT))
        if proc.returncode != 0:
            print("step failed with exit code %d" % proc.returncode,
                  file=sys.stderr)
            print("online alternative: %s" % online_url(reg, action),
                  file=sys.stderr)
            return proc.returncode
    print("done: %s" % values["output"])
    print("online: %s" % online_root(reg))
    return 0


def cmd_list(reg, ns):
    items = reg["actions"]
    if ns.group:
        items = [a for a in items if a["group"] == ns.group]
    if ns.json:
        print(json.dumps({"version": reg["version"],
                          "online_root": online_root(reg),
                          "online_note": reg.get("online_note", ""),
                          "actions": items},
                         ensure_ascii=False, indent=2))
        return 0
    print("%-16s %-12s %-10s %-22s %s" %
          ("ID", "LABEL", "GROUP", "DEPENDS", "ONLINE"))
    for a in items:
        print("%-16s %-12s %-10s %-22s %s" %
              (a["id"], a["label"], a["group"], ",".join(a["depends"]),
               online_url(reg, a)))
    print("total: %d actions | online: %s" % (len(items), online_root(reg)))
    return 0


def cmd_describe(reg, ns):
    a = find_action(reg, ns.id)
    print(json.dumps(a, ensure_ascii=False, indent=2))
    return 0


def cmd_check(reg, ns):
    print("解释器: %s (Python %s)" % (sys.executable, sys.version.split()[0]))
    broken = 0
    for a in reg["actions"]:
        missing = check_dependencies(a["depends"])
        state = "OK" if not missing else "MISSING: " + ", ".join(missing)
        line = "%-16s %s" % (a["id"], state)
        if missing:
            broken += 1
            line += "\n%-16s 修复: %s -m pip install <包名>" % ("", sys.executable)
        print(line)
    print("共 %d 个动作，%d 个依赖未满足" % (len(reg["actions"]), broken))
    return 0


def cmd_online(reg, ns):
    if ns.id:
        a = find_action(reg, ns.id)
        print("%s | %s\n%s" % (a["id"], a["label"], online_url(reg, a)))
        return 0
    print("%s\n%s\n" % (online_root(reg), reg.get("online_note", "")))
    for a in reg["actions"]:
        print("%-16s %s" % (a["id"], online_url(reg, a)))
    return 0


def main():
    p = argparse.ArgumentParser(description="Document Data Extract actions")
    sub = p.add_subparsers(dest="cmd", required=True)

    l = sub.add_parser("list")
    l.add_argument("--json", action="store_true")
    l.add_argument("--group")

    d = sub.add_parser("describe")
    d.add_argument("id")

    sub.add_parser("check")

    o = sub.add_parser("online")
    o.add_argument("id", nargs="?")

    r = sub.add_parser("run")
    r.add_argument("id")
    r.add_argument("--input")
    r.add_argument("--inputs", nargs="+")
    r.add_argument("--output")
    r.add_argument("--text")
    r.add_argument("--query")
    r.add_argument("--preset", help="field preset: general/contract/finance/invoice")
    r.add_argument("--fmt", help="target format for doc-convert: md/txt/csv/pdf")
    r.add_argument("--password")
    r.add_argument("--pages", help="1-based page spec, e.g. 3-5 or 1,3-5")
    r.add_argument("--template", help="template JSON for template-extract")
    r.add_argument("--dry-run", action="store_true")
    r.add_argument("--force", action="store_true")

    ns = p.parse_args()
    reg = load()
    return {"list": cmd_list, "describe": cmd_describe,
            "check": cmd_check, "online": cmd_online,
            "run": cmd_run}[ns.cmd](reg, ns)


if __name__ == "__main__":
    sys.exit(main())
