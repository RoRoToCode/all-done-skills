#!/usr/bin/env python3
"""Locate and invoke the host-provided workbuddy-pdf CLI.

Copied from the pdf-workshop skill so this skill can reuse the host component
without downloading a substitute binary. Exit 69 means "component not ready
yet" and is retriable; exit 127 means the CLI is genuinely absent.
"""

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

NOT_READY = 69
NO_CLI = 127


def _candidate_run_scripts():
    roots = []
    if os.name == "nt":
        for var in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
            value = os.environ.get(var)
            if value:
                roots.append(value)
        roots.append(str(Path.home() / "AppData" / "Local" / "Programs"))
    else:
        roots.extend(["/Applications", "/opt", "/usr/local/share",
                      str(Path.home() / ".local" / "share")])

    override = os.environ.get("WORKBUDDY_PDF_SKILL_DIR")
    if override:
        scripts = Path(override) / "scripts"
        for name in ("run.ps1", "run.sh"):
            candidate = scripts / name
            if candidate.exists():
                return candidate

    patterns = [
        "WorkBuddy/resources/app.asar.unpacked/resources/plugins/*/skills/workbuddy-pdf/scripts/run.ps1",
        "WorkBuddy/resources/app.asar.unpacked/resources/plugins/*/skills/workbuddy-pdf/scripts/run.sh",
        "WorkBuddy.app/Contents/Resources/app.asar.unpacked/resources/plugins/*/skills/workbuddy-pdf/scripts/run.sh",
        "*/resources/app.asar.unpacked/resources/plugins/*/skills/workbuddy-pdf/scripts/run.sh",
    ]
    found = []
    for root in roots:
        for pattern in patterns:
            found.extend(glob.glob(os.path.join(root, pattern)))
    if not found:
        return None
    if os.name == "nt":
        ps1 = [p for p in found if p.endswith(".ps1")]
        if ps1:
            return Path(ps1[0])
    return Path(sorted(found)[0])


def _downloaded_binary():
    dirs = []
    override = os.environ.get("WORKBUDDY_PDF_CLI_DIR")
    if override:
        dirs.append(Path(override))
    dirs.append(Path.home() / ".workbuddy" / "external-packages" / "pdf-cli")
    names = ("workbuddy-pdf.exe", "workbuddy-pdf") if os.name == "nt" else ("workbuddy-pdf",)
    for directory in dirs:
        for name in names:
            candidate = directory / name
            if candidate.is_file():
                return candidate
    return None


def command_prefix():
    override = os.environ.get("WORKBUDDY_PDF")
    if override and Path(override).exists():
        return [str(Path(override).resolve())]
    on_path = shutil.which("workbuddy-pdf")
    if on_path:
        return [on_path]
    downloaded = _downloaded_binary()
    if downloaded is not None:
        return [str(downloaded.resolve())]
    launcher = _candidate_run_scripts()
    if launcher is None:
        return None
    if launcher.suffix == ".ps1":
        return ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                "-File", str(launcher)]
    return ["sh", str(launcher)]


def run_cli(args, retries=3):
    prefix = command_prefix()
    if prefix is None:
        print(json.dumps({"status": "error", "code": "cli_not_found",
                          "message": "workbuddy-pdf CLI not found."},
                         ensure_ascii=False))
        return NO_CLI
    cmd = prefix + list(args)
    for attempt in range(retries):
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
        if proc.returncode == NOT_READY and attempt < retries - 1:
            time.sleep(3)
            continue
        if proc.stdout:
            sys.stdout.write(proc.stdout)
        if proc.stderr:
            sys.stderr.write(proc.stderr)
        return proc.returncode
    return NOT_READY


def build_parser():
    p = argparse.ArgumentParser(description="Wrapper for the workbuddy-pdf CLI")
    sub = p.add_subparsers(dest="action", required=True)
    r = sub.add_parser("read")
    r.add_argument("input")
    r.add_argument("-o", "--output", required=True)
    r.add_argument("-f", "--format", default="md",
                   choices=["md", "md-plain", "txt", "structure", "table"])
    r.add_argument("--image-dir")
    r.add_argument("--table-format", default="json", choices=["json", "csv"])
    r.add_argument("-p", "--password")
    return p


def to_args(ns):
    out = [ns.input, "-o", ns.output, "-f", ns.format]
    if ns.image_dir:
        out += ["--image-dir", ns.image_dir]
    if ns.format == "table":
        out += ["--table-format", ns.table_format]
    if ns.password:
        out += ["-p", ns.password]
    return out


def run_action(argv):
    ns = build_parser().parse_args([str(x) for x in argv])
    return run_cli(to_args(ns))


if __name__ == "__main__":
    sys.exit(run_action(sys.argv[1:]))
