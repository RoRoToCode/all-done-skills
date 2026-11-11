#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""web-capture action registry: list / describe / check / browser / run / online.

The registry in assets/actions.json is the single source of truth. `--extra`
passes any remaining arguments straight through to the action script, e.g.

  python scripts/actions.py run web-diff --input cfg.json -o out/ \
      --extra --old https://a/ --new https://b/
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from web_common import browser_status, stem_for, VERSION

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
    # Explicit null means that site genuinely has no equivalent tool.
    if "online" in action and not action.get("online"):
        return "无（roroto.com 无对应工具）"
    return action.get("online") or reg.get("online_root", DEFAULT_ONLINE)


def online_root(reg):
    return reg.get("online_root", DEFAULT_ONLINE)


def check_dependencies(names):
    missing = []
    for name in names:
        if name in ("stdlib", "python"):
            continue                      # standard library, always available
        if name == "browser":
            if not browser_status()["available"]:
                missing.append("browser (设置 WEB_CAPTURE_BROWSER 或安装 Edge/Chrome)")
        elif name == "bs4":
            missing.append("bs4 (本技能不依赖，仅可选增强)")
    return missing


def build_values(action, ns):
    raw = getattr(ns, "url", None) or ns.input or ""
    stem = stem_for(raw) if raw else "page"
    output = ns.output or action["default_output"].replace("{{stem}}", stem)
    return {
        "input": str(Path(raw).resolve()) if (raw and not raw.lower().startswith(
            ("http://", "https://", "file://"))) else raw,
        "output": str(Path(output).expanduser().resolve()),
        "stem": stem,
        "width": str(getattr(ns, "width", None) or 1440),
        "depth": str(getattr(ns, "depth", None) or 1),
        "max_pages": str(getattr(ns, "max_pages", None) or 20),
        "kind": getattr(ns, "kind", None) or "all",
    }


def render_step(step, values):
    argv = []
    for token in step:
        out = token
        for key, val in values.items():
            if val is None:
                continue
            out = out.replace("{{%s}}" % key, str(val))
        if "{{" in out:
            raise SystemExit("missing value for placeholder: %s" % out)
        argv.append(sys.executable if out == "python" else out)
    return argv


# Flags that take a value. If the same flag comes both from a registry step and
# from --extra, keep only the last one (argparse would do the same) so the
# printed command stays honest and unambiguous.
VALUE_FLAGS = {"--width", "--height", "--depth", "--max-pages", "--kind",
               "--timeout", "--browser", "--wait", "--delay", "--limit",
               "--max-assets", "--max-asset-bytes", "--format", "--include",
               "--exclude", "--ua"}


def dedupe_flags(argv):
    positions = {}
    for i, token in enumerate(argv[:-1]):
        if token in VALUE_FLAGS and not argv[i + 1].startswith("--"):
            positions.setdefault(token, []).append(i)
    drop = set()
    for spots in positions.values():
        for i in spots[:-1]:
            drop.update((i, i + 1))
    return [v for i, v in enumerate(argv) if i not in drop]


def cmd_run(reg, ns):
    action = find_action(reg, ns.id)
    values = build_values(action, ns)
    if not values["input"] and ns.id != "web-diff":
        raise SystemExit("this action needs --input (URL or local file)")
    missing = check_dependencies(action["depends"])
    if missing and not ns.force and not ns.dry_run:
        raise SystemExit("missing dependencies: %s (use --force to try anyway)\n"
                         "online alternative: %s" %
                         (", ".join(missing), online_url(reg, action)))
    argv = render_step(action["steps"][0], values)
    if ns.no_robots:
        argv.append("--no-robots")
    if ns.browser:
        argv += ["--browser", ns.browser]
    if ns.timeout:
        argv += ["--timeout", str(ns.timeout)]
    argv += list(ns.extra or [])
    argv = dedupe_flags(argv)
    print("action: %s | %s" % (action["id"], action["label"]))
    if missing:
        print("warning: %s" % ", ".join(missing))
    print("$ " + " ".join(argv))
    if ns.dry_run:
        print("dry-run: nothing executed")
        return 0
    proc = subprocess.run(argv, cwd=str(ROOT))
    if proc.returncode not in (0, 2):
        print("step failed with exit code %d" % proc.returncode, file=sys.stderr)
        print("online alternative: %s" % online_url(reg, action), file=sys.stderr)
    return proc.returncode


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
    print("%-16s %-16s %-12s %-12s %s" %
          ("ID", "LABEL", "GROUP", "DEPENDS", "ONLINE"))
    for a in items:
        print("%-16s %-16s %-12s %-12s %s" %
              (a["id"], a["label"], a["group"], ",".join(a["depends"]),
               online_url(reg, a)))
    print("total: %d actions | version: %s | online: %s" %
          (len(items), reg["version"], online_root(reg)))
    return 0


def cmd_describe(reg, ns):
    print(json.dumps(find_action(reg, ns.id), ensure_ascii=False, indent=2))
    return 0


def cmd_check(reg, ns):
    print("runtime: Python %s | web-capture %s" %
          (sys.version.split()[0], VERSION))
    for action in reg["actions"]:
        missing = check_dependencies(action["depends"])
        print("%-16s %s" % (action["id"],
                            "OK" if not missing else "MISSING: " + ", ".join(missing)))
        if missing:
            print("%-16s online: %s" % ("", online_url(reg, action)))
    return 0


def cmd_browser(reg, ns):
    print(json.dumps(browser_status(), ensure_ascii=False, indent=2))
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
    p = argparse.ArgumentParser(description="Web Capture actions")
    sub = p.add_subparsers(dest="cmd", required=True)

    l = sub.add_parser("list")
    l.add_argument("--json", action="store_true")
    l.add_argument("--group")

    d = sub.add_parser("describe")
    d.add_argument("id")

    sub.add_parser("check")
    sub.add_parser("browser")

    o = sub.add_parser("online")
    o.add_argument("id", nargs="?")

    r = sub.add_parser("run")
    r.add_argument("id")
    r.add_argument("--input", help="URL / local file / URL-list file")
    r.add_argument("--url", help="alias of --input")
    r.add_argument("--output", "-o")
    r.add_argument("--width", type=int)
    r.add_argument("--depth", type=int)
    r.add_argument("--max-pages", type=int)
    r.add_argument("--kind")
    r.add_argument("--timeout", type=float)
    r.add_argument("--browser", help="explicit browser path")
    r.add_argument("--no-robots", action="store_true")
    r.add_argument("--dry-run", action="store_true")
    r.add_argument("--force", action="store_true")
    r.add_argument("--extra", nargs=argparse.REMAINDER,
                   help="remaining args are passed to the action script; put last")

    ns = p.parse_args()
    reg = load()
    return {"list": cmd_list, "describe": cmd_describe, "check": cmd_check,
            "browser": cmd_browser, "online": cmd_online,
            "run": cmd_run}[ns.cmd](reg, ns)


if __name__ == "__main__":
    raise SystemExit(main())
