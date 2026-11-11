#!/usr/bin/env python3
"""Check or install the optional dependencies used by the Office skill.

Default target is an isolated venv outside the skill folder, so packaging the
skill never bundles a virtual environment. Only python-docx, openpyxl and
python-pptx are required; they are pure Python. Run `install` only after
telling the user it will download packages from PyPI.
"""

import argparse
import json
import os
import subprocess
import sys
import venv
from pathlib import Path

DEFAULT_VENV = Path.home() / ".workbuddy" / "office-all-done-env"
REQUIREMENTS = ["python-docx>=1.1,<2", "openpyxl>=3.1,<4", "python-pptx>=0.6,<1"]


def venv_path():
    return Path(os.environ.get("OFFICE_WORKSHOP_VENV", str(DEFAULT_VENV))).resolve()


def venv_python(root):
    if os.name == "nt":
        return root / "Scripts" / "python.exe"
    return root / "bin" / "python"


def _lib_ok(python, module):
    proc = subprocess.run([str(python), "-c", "import %s" % module],
                          capture_output=True, text=True)
    return proc.returncode == 0


def check():
    mods = {"docx": "python-docx", "openpyxl": "openpyxl", "pptx": "python-pptx"}
    results = {}
    all_ok = True
    for mod in mods:
        ok = _lib_ok(sys.executable, mod)
        src = "current interpreter"
        if not ok:
            root = venv_path()
            if venv_python(root).exists() and _lib_ok(venv_python(root), mod):
                ok = True
                src = "isolated venv"
        results[mod] = {"status": "ok" if ok else "missing", "source": src}
        all_ok = all_ok and ok
    info = {"status": "ok" if all_ok else "missing",
            "python": sys.executable, "libs": results}
    print(json.dumps(info, ensure_ascii=False))
    return 0 if all_ok else 2


def install(args):
    if args.system:
        cmd = [sys.executable, "-m", "pip", "install", "--user"] + REQUIREMENTS
        python = sys.executable
    else:
        root = venv_path()
        root.parent.mkdir(parents=True, exist_ok=True)
        if not venv_python(root).exists():
            venv.EnvBuilder(with_pip=True).create(str(root))
        python = str(venv_python(root))
        cmd = [python, "-m", "pip", "install", "--disable-pip-version-check"] + REQUIREMENTS
    proc = subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    ok = proc.returncode == 0
    print(json.dumps({"status": "ok" if ok else "error", "python": python,
                      "stdout": proc.stdout[-1200:], "stderr": proc.stderr[-1200:]},
                     ensure_ascii=False))
    if ok and not args.system:
        print("后续请用该解释器运行本技能脚本：%s" % python, file=sys.stderr)
    return 0 if ok else 1


def main():
    p = argparse.ArgumentParser(description="Manage Office skill dependencies")
    sub = p.add_subparsers(dest="action", required=True)
    sub.add_parser("check")
    i = sub.add_parser("install")
    i.add_argument("--system", action="store_true",
                   help="install into the current interpreter instead of a venv")
    args = p.parse_args()
    return check() if args.action == "check" else install(args)


if __name__ == "__main__":
    sys.exit(main())
