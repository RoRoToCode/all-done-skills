#!/usr/bin/env python3
"""Office 三件套全搞定 action registry: list, inspect, check, run, online.

The registry lives in assets/actions.json and is the single source of truth.

Usage:
  python scripts/actions.py list [--json] [--group NAME]
  python scripts/actions.py describe <action-id>
  python scripts/actions.py check
  python scripts/actions.py run <action-id> --input a.docx [--output out.md]
                                [--inputs a.docx b.docx] [--data data.json]
                                [--format csv|json|md] [--dry-run]
  python scripts/actions.py online [action-id]
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

import office_common as oc

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "assets" / "actions.json"


def load():
    with REGISTRY.open(encoding="utf-8") as fh:
        return json.load(fh)


def find_action(reg, action_id):
    for item in reg["actions"]:
        if item["id"] == action_id:
            return item
    raise SystemExit("unknown action: %s (try `actions.py list`)" % action_id)


def build_values(action, ns):
    # Steps run with cwd=ROOT (the skill directory), so every user-supplied
    # path must be resolved against the caller's cwd first.
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
        "text": ns.text or "",
        "query": ns.query or "",
        "password": ns.password,
        "pages": getattr(ns, "pages", None) or "1",
        "data": ns.data or "",
        "sheet": ns.sheet or "",
        "fmt": (ns.format or "csv").lower(),
    }


def render_step(step, values, exe):
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
        if out == "python":
            out = exe
        argv.append(out)
    return argv


def cmd_run(reg, ns):
    action = find_action(reg, ns.id)
    values = build_values(action, ns)
    if values["input"] is None and action["id"] not in _multi_only():
        raise SystemExit("this action needs --input (or --inputs)")
    if not values["inputs"]:
        raise SystemExit("this action needs at least one input file")
    if values["output"] in values["inputs"]:
        raise SystemExit("refusing to overwrite an input file")
    exe = oc.choose_python(action["depends"])
    missing = oc.check_dependencies(action["depends"])
    if missing and not ns.force and not ns.dry_run:
        raise SystemExit("missing dependencies: %s (use --force to try anyway)\n"
                         "online alternative: %s" %
                         (", ".join(missing), oc.online_url(reg, action)))
    commands = [render_step(step, values, exe) for step in action["steps"]]
    if ns.page_break and action["id"] == "docx-merge":
        commands[0].append("--page-break")
    print("action: %s | %s" % (action["id"], action["label"]))
    if missing:
        print("warning: %s" % ", ".join(missing))
        print("online alternative: %s" % oc.online_url(reg, action))
    for argv in commands:
        print("$ %s" % " ".join(argv))
    if ns.dry_run:
        print("dry-run: nothing executed")
        return 0
    for argv in commands:
        proc = subprocess.run(argv, cwd=str(ROOT))
        if proc.returncode != 0:
            print("step failed with exit code %d" % proc.returncode, file=sys.stderr)
            print("online alternative: %s" % oc.online_url(reg, action), file=sys.stderr)
            return proc.returncode
    print("done: %s" % values["output"])
    return 0


def _multi_only():
    # Actions that only need --inputs (no single --input).
    return {"docx-merge", "xlsx-merge", "pptx-merge"}


def cmd_list(reg, ns):
    items = reg["actions"]
    if ns.group:
        items = [a for a in items if a["group"] == ns.group]
    if ns.json:
        print(json.dumps({"version": reg["version"],
                          "online_root": reg.get("online_root"),
                          "online_note": reg.get("online_note", ""),
                          "actions": items},
                         ensure_ascii=False, indent=2))
        return 0
    print("%-14s %-16s %-10s %-12s %s" %
          ("ID", "LABEL", "GROUP", "DEPENDS", "ONLINE"))
    for a in items:
        print("%-14s %-16s %-10s %-12s %s" %
              (a["id"], a["label"], a["group"], ",".join(a["depends"]),
               oc.online_url(reg, a)))
    print("total: %d actions | online: %s" % (len(items), reg.get("online_root")))
    return 0


def cmd_describe(reg, ns):
    a = find_action(reg, ns.id)
    print(json.dumps(a, ensure_ascii=False, indent=2))
    return 0


def cmd_check(reg, ns):
    print("解释器: %s (Python %s)" % (sys.executable, sys.version.split()[0]))
    broken = 0
    for a in reg["actions"]:
        missing = oc.check_dependencies(a["depends"])
        state = "OK" if not missing else "MISSING: " + ", ".join(missing)
        line = "%-14s %s" % (a["id"], state)
        if missing:
            broken += 1
            if any("soffice" in m for m in missing):
                hint = ("装 LibreOffice：winget install TheDocumentFoundation.LibreOffice"
                        "（或设 SOFFICE 指向 soffice.exe）")
            else:
                hint = "%s -m pip install <包名>" % sys.executable
            line += "\n%-14s 修复: %s" % ("", hint)
        print(line)
    print("共 %d 个动作，%d 个依赖未满足" % (len(reg["actions"]), broken))
    return 0


def cmd_online(reg, ns):
    if ns.id:
        a = find_action(reg, ns.id)
        print("%s | %s\n%s" % (a["id"], a["label"], oc.online_url(reg, a)))
        return 0
    print("%s\n%s\n" % (reg.get("online_root"), reg.get("online_note", "")))
    for a in reg["actions"]:
        print("%-14s %s" % (a["id"], oc.online_url(reg, a)))
    return 0


def main():
    p = argparse.ArgumentParser(description="Office 三件套全搞定 actions")
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
    r.add_argument("--data", help="JSON file path or inline JSON for docx-fill")
    r.add_argument("--sheet", help="target sheet name (optional)")
    r.add_argument("--format", choices=("csv", "json", "md"), help="xlsx-extract format")
    r.add_argument("--text")
    r.add_argument("--query")
    r.add_argument("--password")
    r.add_argument("--pages", help="1-based page spec, e.g. 3-5 or 1,3-5")
    r.add_argument("--dry-run", action="store_true")
    r.add_argument("--force", action="store_true")
    r.add_argument("--page-break", action="store_true",
                   help="docx-merge: start each source on a new page")

    ns = p.parse_args()
    reg = load()
    return {"list": cmd_list, "describe": cmd_describe,
            "check": cmd_check, "online": cmd_online,
            "run": cmd_run}[ns.cmd](reg, ns)


if __name__ == "__main__":
    sys.exit(main())
