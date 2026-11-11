#!/usr/bin/env python3
"""Locate and invoke the host-provided workbuddy-pdf CLI.

The binary is downloaded on demand by WorkBuddy and placed on PATH. Never
download a substitute binary. Exit 69 means "component not ready yet" and is
retriable; exit 127 means the CLI is genuinely absent on this machine.
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
    # Prefer the PowerShell launcher on Windows and the shell launcher elsewhere.
    if os.name == "nt":
        ps1 = [p for p in found if p.endswith(".ps1")]
        if ps1:
            return Path(ps1[0])
    return Path(sorted(found)[0])


def _downloaded_binary():
    """WorkBuddy downloads the CLI into ~/.workbuddy/external-packages/pdf-cli.

    The bundled run.ps1 launcher looks for bin/windows-x86_64/workbuddy-pdf.exe
    inside the installed plugin instead, which is absent on some machines. Call
    the real binary directly whenever it exists.
    """
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
                          "message": "workbuddy-pdf CLI not found. Set WORKBUDDY_PDF, "
                                     "WORKBUDDY_PDF_CLI_DIR or WORKBUDDY_PDF_SKILL_DIR, "
                                     "or wait for the host to finish downloading the component "
                                     "into ~/.workbuddy/external-packages/pdf-cli."},
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

    r = sub.add_parser("read", help="extract text, tables or structure")
    r.add_argument("input")
    r.add_argument("-o", "--output", required=True)
    r.add_argument("-f", "--format", default="md",
                   choices=["md", "md-plain", "txt", "structure", "table"])
    r.add_argument("--image-dir")
    r.add_argument("--table-format", default="json", choices=["json", "csv"])
    r.add_argument("-p", "--password")

    m = sub.add_parser("merge", help="join two or more PDFs")
    m.add_argument("inputs", nargs="+")
    m.add_argument("-o", "--output", required=True)

    s = sub.add_parser("split", help="one PDF per page")
    s.add_argument("input")
    s.add_argument("-o", "--output", required=True)

    e = sub.add_parser("encrypt", help="set an opening password")
    e.add_argument("input")
    e.add_argument("-o", "--output", required=True)
    e.add_argument("--new-password", required=True)
    e.add_argument("--owner-password")

    d = sub.add_parser("decrypt", help="remove password protection")
    d.add_argument("input")
    d.add_argument("-o", "--output", required=True)
    d.add_argument("-p", "--password", required=True)

    c = sub.add_parser("convert", help="to docx / pptx / xlsx / dxf")
    c.add_argument("input")
    c.add_argument("-o", "--output", required=True)
    c.add_argument("-f", "--format", required=True,
                   choices=["docx", "pptx", "xlsx", "dxf"])
    c.add_argument("--sheet-split", choices=["continuous", "page", "auto"])

    g = sub.add_parser("render", help="render every page to PNG/JPG")
    g.add_argument("input")
    g.add_argument("-o", "--output", required=True)
    g.add_argument("-f", "--format", default="png", choices=["png", "jpg"])
    g.add_argument("--dpi", type=int, default=150)
    g.add_argument("--jpeg-quality", type=int)

    raw = sub.add_parser("raw", help="forward arbitrary arguments verbatim")
    raw.add_argument("args", nargs=argparse.REMAINDER)
    return p


def to_args(ns):
    a = ns.action
    if a == "read":
        out = [ns.input, "-o", ns.output, "-f", ns.format]
        if ns.image_dir:
            out += ["--image-dir", ns.image_dir]
        if ns.format == "table":
            out += ["--table-format", ns.table_format]
        if ns.password:
            out += ["-p", ns.password]
        return out
    if a == "merge":
        return ns.inputs + ["-f", "merge", "-o", ns.output]
    if a == "split":
        return [ns.input, "-f", "split", "-o", ns.output]
    if a == "encrypt":
        out = [ns.input, "-f", "encrypt", "-o", ns.output,
               "--new-password", ns.new_password]
        if ns.owner_password:
            out += ["--owner-password", ns.owner_password]
        return out
    if a == "decrypt":
        return [ns.input, "-f", "decrypt", "-o", ns.output, "-p", ns.password]
    if a == "convert":
        out = [ns.input, "-f", ns.format, "-o", ns.output]
        if ns.sheet_split:
            out += ["--sheet-split", ns.sheet_split]
        return out
    if a == "render":
        out = [ns.input, "-f", ns.format, "-o", ns.output, "--dpi", str(ns.dpi)]
        if ns.jpeg_quality is not None:
            out += ["--jpeg-quality", str(ns.jpeg_quality)]
        return out
    if a == "raw":
        return [x for x in ns.args if x != "--"]
    raise ValueError(a)


def run_action(argv):
    """Parse a subcommand-style argv and forward the resulting raw CLI args."""
    ns = build_parser().parse_args([str(x) for x in argv])
    return run_cli(to_args(ns))


def main():
    code = run_action(sys.argv[1:])
    if code == NO_CLI:
        print("CLI 不可用：请等待宿主组件下载完成，或设置 WORKBUDDY_PDF 环境变量。",
              file=sys.stderr)
    elif code == NOT_READY:
        print("CLI 组件仍在下载，已重试仍未就绪，请稍后再试。", file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
