#!/usr/bin/env python3
"""PDF Workshop action registry: list, inspect, check, run, online fallback.

The registry lives in assets/actions.json and is the single source of truth.

Usage:
  python scripts/actions.py list [--json] [--group NAME]
  python scripts/actions.py describe <action-id>
  python scripts/actions.py check
  python scripts/actions.py run <action-id> --input a.pdf [--output out.pdf]
                                [--inputs a.pdf b.pdf] [--text TEXT]
                                [--query TEXT] [--password PWD] [--pages 3-5]
                                [--toc toc.txt] [--per-page 2|4] [--dry-run]
  python scripts/actions.py online [action-id]
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


def check_dependencies(names):
    missing = []
    for name in names:
        if name == "cli":
            spec = importlib.util.spec_from_file_location(
                "wb_pdf_local", ROOT / "scripts" / "wb_pdf.py")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if mod.command_prefix() is None:
                missing.append("cli (workbuddy-pdf)")
        elif name == "pypdf":
            if importlib.util.find_spec("pypdf") is None:
                missing.append("pypdf (run bootstrap.py install)")
        elif name == "browser":
            found = (os.environ.get("PDF_BROWSER") or
                     shutil.which("msedge") or shutil.which("chrome") or
                     shutil.which("chromium"))
            if not found and os.name == "nt":
                found = next((str(p) for p in [
                    Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)"))
                    / "Microsoft/Edge/Application/msedge.exe",
                    Path(os.environ.get("ProgramFiles", "C:/Program Files"))
                    / "Google/Chrome/Application/chrome.exe",
                ] if p.exists()), None)
            if not found:
                missing.append("browser (Edge / Chrome)")
        elif name == "rapidocr":
            if importlib.util.find_spec("rapidocr_onnxruntime") is None:
                missing.append(
                    "rapidocr (python scripts/bootstrap.py install --ocr)")
        elif name == "pymupdf":
            if (importlib.util.find_spec("pymupdf") is None
                    and importlib.util.find_spec("fitz") is None):
                missing.append("pymupdf (python -m pip install pymupdf)")
        elif name == "tesseract":
            if not (os.environ.get("TESSERACT") or shutil.which("tesseract")):
                missing.append("tesseract (OCR fallback, Chinese needs chi_sim)")
    return missing


def build_values(action, ns):
    # Steps run with cwd=ROOT (the skill directory), so every user-supplied
    # path must be resolved against the caller's cwd first. Otherwise a relative
    # "sample.pdf" silently resolves inside the skill folder and the CLI reports
    # "no such file".
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
        "text": ns.text or "内部资料",
        "query": ns.query or "违约金",
        "password": ns.password,
        "pages": getattr(ns, "pages", None) or "1",
        "toc": str(Path(getattr(ns, "toc", None) or "toc.txt").resolve()),
        "per_page": getattr(ns, "per_page", None) or "2",
        "angle": getattr(ns, "angle", None) or "90",
        "extra": list(getattr(ns, "extra", None) or []),
    }


def render_step(step, values):
    argv = []
    for token in step:
        if token == "{{inputs}}":
            argv.extend(str(v) for v in values["inputs"])
            continue
        if token == "{{extra}}":
            argv.extend(str(v) for v in values["extra"])
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
    if values["input"] is None:
        raise SystemExit("this action needs --input (or --inputs)")
    if not values["inputs"]:
        raise SystemExit("this action needs at least one input PDF")
    if values["output"] in values["inputs"]:
        raise SystemExit("refusing to overwrite an input file")
    missing = check_dependencies(action["depends"])
    if missing and not ns.force and not ns.dry_run:
        raise SystemExit("missing dependencies: %s (use --force to try anyway)\n"
                         "online alternative: %s" %
                         (", ".join(missing), online_url(reg, action)))
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
                          "actions": items},
                         ensure_ascii=False, indent=2))
        return 0
    print("%-18s %-16s %-10s %-12s %s" %
          ("ID", "LABEL", "GROUP", "DEPENDS", "ONLINE"))
    for a in items:
        print("%-18s %-16s %-10s %-12s %s" %
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
    print("pypdf: %s | rapidocr: %s" % (
        "OK" if importlib.util.find_spec("pypdf") else "缺失",
        "OK" if importlib.util.find_spec("rapidocr_onnxruntime") else "缺失"))
    missing_actions = 0
    for a in reg["actions"]:
        missing = check_dependencies(a["depends"])
        state = "OK" if not missing else "MISSING: " + ", ".join(missing)
        line = "%-18s %s" % (a["id"], state)
        if missing:
            missing_actions += 1
            line += "\n%-18s 修复: python scripts/bootstrap.py install 或 " \
                    "python -m pip install <包名>" % ""
        print(line)
    print("总计 %d 个动作，%d 个依赖未满足" % (len(reg["actions"]), missing_actions))
    return 0


def cmd_online(reg, ns):
    if ns.id:
        a = find_action(reg, ns.id)
        print("%s | %s\n%s" % (a["id"], a["label"], online_url(reg, a)))
        return 0
    print("%s\n%s\n" % (online_root(reg), reg.get("online_note", "")))
    for a in reg["actions"]:
        print("%-18s %s" % (a["id"], online_url(reg, a)))
    return 0


def main():
    p = argparse.ArgumentParser(description="PDF Workshop actions")
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
    r.add_argument("--password")
    r.add_argument("--pages", help="1-based page spec, e.g. 3-5 or 1,3-5")
    r.add_argument("--toc", help="bookmark spec file (JSON or indented text)")
    r.add_argument("--per-page", choices=("2", "4"), help="N-up sheets")
    r.add_argument("--angle", help="rotation angle for pdf-rotate, default 90")
    r.add_argument("--extra", nargs=argparse.REMAINDER,
                   help="extra tokens appended to the action command (put last)")
    r.add_argument("--dry-run", action="store_true")
    r.add_argument("--force", action="store_true")

    ns = p.parse_args()
    reg = load()
    return {"list": cmd_list, "describe": cmd_describe,
            "check": cmd_check, "online": cmd_online,
            "run": cmd_run}[ns.cmd](reg, ns)


if __name__ == "__main__":
    sys.exit(main())
