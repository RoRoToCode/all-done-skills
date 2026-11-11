#!/usr/bin/env python3
"""OCR Workshop action registry: list, inspect, check, run, engines, online.

The registry lives in assets/actions.json and is the single source of truth.

Usage:
  python scripts/actions.py list [--json] [--group NAME]
  python scripts/actions.py describe <action-id>
  python scripts/actions.py check
  python scripts/actions.py engines [--json]
  python scripts/actions.py run <action-id> --input a.png [--output outdir]
                                [--pages 3-5] [--password PWD] [--dry-run]
  python scripts/actions.py online [action-id]
"""

import argparse
import importlib.util
import json
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


def _has_module(*names):
    return any(importlib.util.find_spec(name) is not None for name in names)


def check_dependencies(names):
    missing = []
    for name in names:
        if name == "rapidocr":
            if not _has_module("rapidocr_onnxruntime"):
                missing.append("rapidocr (python scripts/bootstrap.py install --ocr)")
        elif name == "tesseract":
            if not shutil.which("tesseract"):
                missing.append("tesseract (binary + language packs)")
        elif name == "ocr":
            # 任一引擎可用即可
            if not (_has_module("rapidocr_onnxruntime") or shutil.which("tesseract")):
                missing.append("ocr engine (python scripts/bootstrap.py install --ocr)")
        elif name == "pymupdf":
            if not _has_module("pymupdf", "fitz"):
                missing.append("pymupdf (python scripts/bootstrap.py install --pdf)")
    return missing


def build_values(action, ns):
    # Steps run with cwd=ROOT, so resolve user paths against the caller's cwd
    # first; otherwise a relative "a.png" resolves inside the skill folder.
    raw_primary = ns.input
    stem = Path(raw_primary).stem if raw_primary else "output"
    raw_output = ns.output or action["default_output"].replace("{{stem}}", stem)
    return {
        "input": str(Path(raw_primary).resolve()) if raw_primary else None,
        "output": str(Path(raw_output).resolve()),
        "stem": stem,
        "dpi": str(getattr(ns, "dpi", None) or 200),
        "pages": getattr(ns, "pages", None),
        "password": ns.password,
        "extra": list(getattr(ns, "extra", None) or []),
    }


def render_step(step, values):
    argv = []
    for token in step:
        if token == "{{extra}}":
            argv.extend(str(v) for v in values["extra"])
            continue
        out = token
        for key, val in values.items():
            if val is None:
                continue
            out = out.replace("{{%s}}" % key, str(val))
        if "{{" in out:
            raise SystemExit("missing value for placeholder: %s" % out)
        argv.append(sys.executable if out == "python" else out)
    return argv


def safe_display(argv):
    hidden, shown = False, []
    for item in argv:
        shown.append("***" if hidden else item)
        hidden = item in ("--password", "-p")
    return " ".join(shown)


def cmd_run(reg, ns):
    action = find_action(reg, ns.id)
    values = build_values(action, ns)
    if values["input"] is None:
        raise SystemExit("this action needs --input")
    missing = check_dependencies(action["depends"])
    if missing and not ns.force and not ns.dry_run:
        raise SystemExit("missing dependencies: %s (use --force to try anyway)\n"
                         "online alternative: %s" %
                         (", ".join(missing), online_url(reg, action)))
    argv = render_step(action["steps"][0], values)
    print("action: %s | %s" % (action["id"], action["label"]))
    if missing:
        print("warning: %s" % ", ".join(missing))
        print("online alternative: %s" % online_url(reg, action))
    print("$ %s" % safe_display(argv))
    if ns.dry_run:
        print("dry-run: nothing executed")
        return 0
    proc = subprocess.run(argv, cwd=str(ROOT))
    if proc.returncode != 0:
        print("step failed with exit code %d" % proc.returncode, file=sys.stderr)
        print("online alternative: %s" % online_url(reg, action), file=sys.stderr)
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
                          "actions": items}, ensure_ascii=False, indent=2))
        return 0
    print("%-16s %-18s %-10s %-14s %s" %
          ("ID", "LABEL", "GROUP", "DEPENDS", "ONLINE"))
    for a in items:
        print("%-16s %-18s %-10s %-14s %s" %
              (a["id"], a["label"], a["group"], ",".join(a["depends"]),
               online_url(reg, a)))
    print("total: %d actions | online: %s" % (len(items), online_root(reg)))
    return 0


def cmd_describe(reg, ns):
    print(json.dumps(find_action(reg, ns.id), ensure_ascii=False, indent=2))
    return 0


def cmd_check(reg, ns):
    print("解释器: %s (Python %s)" % (sys.executable, sys.version.split()[0]))
    broken = 0
    for action in reg["actions"]:
        missing = check_dependencies(action["depends"])
        print("%-16s %s" % (action["id"],
                            "OK" if not missing else "MISSING: " + ", ".join(missing)))
        if missing:
            broken += 1
            print("%-16s 修复: %s scripts/bootstrap.py install --ocr --pdf"
                  % ("", sys.executable))
    print("共 %d 个动作，%d 个依赖未满足" % (len(reg["actions"]), broken))
    return 0


def cmd_engines(reg, ns):
    sys.path.insert(0, str(ROOT / "scripts"))
    import ocr_core
    status = ocr_core.engine_status()
    if ns.json:
        print(json.dumps(status, ensure_ascii=False, indent=2))
        return 0
    for name in ("rapidocr", "tesseract"):
        item = status[name]
        line = "%-10s %s" % (name, "OK" if item["available"] else "MISSING")
        detail = item.get("detail") or ""
        if item.get("languages"):
            detail = "languages: " + ",".join(item["languages"])
        if item.get("binary"):
            detail = item["binary"] + (" | " + detail if detail else "")
        print(line + ("  " + detail if detail else ""))
    print("preferred: %s" % (status["preferred"] or "无（先 bootstrap.py install --ocr）"))
    return 0


def cmd_online(reg, ns):
    if ns.id:
        action = find_action(reg, ns.id)
        print("%s | %s\n%s" % (action["id"], action["label"],
                               online_url(reg, action)))
        return 0
    print("%s\n%s\n" % (online_root(reg), reg.get("online_note", "")))
    for action in reg["actions"]:
        print("%-16s %s" % (action["id"], online_url(reg, action)))
    return 0


def main():
    p = argparse.ArgumentParser(description="OCR Workshop actions")
    sub = p.add_subparsers(dest="cmd", required=True)

    l = sub.add_parser("list")
    l.add_argument("--json", action="store_true")
    l.add_argument("--group")

    d = sub.add_parser("describe")
    d.add_argument("id")

    sub.add_parser("check")

    e = sub.add_parser("engines")
    e.add_argument("--json", action="store_true")

    o = sub.add_parser("online")
    o.add_argument("id", nargs="?")

    r = sub.add_parser("run")
    r.add_argument("id")
    r.add_argument("--input")
    r.add_argument("--output")
    r.add_argument("--pages", help="1-based page spec, e.g. 3-5 or 1,3-5")
    r.add_argument("--dpi", type=int)
    r.add_argument("--password")
    r.add_argument("--extra", nargs=argparse.REMAINDER,
                   help="追加到动作命令末尾的参数（放在最后）")
    r.add_argument("--dry-run", action="store_true")
    r.add_argument("--force", action="store_true")

    ns = p.parse_args()
    reg = load()
    return {"list": cmd_list, "describe": cmd_describe, "check": cmd_check,
            "engines": cmd_engines, "online": cmd_online,
            "run": cmd_run}[ns.cmd](reg, ns)


if __name__ == "__main__":
    sys.exit(main())
