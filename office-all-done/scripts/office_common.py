#!/usr/bin/env python3
"""Shared helpers for the Office 三件套全搞定 skill.

- Locates the isolated venv created by bootstrap.py.
- Picks the Python interpreter that can actually import the needed library
  (current interpreter, else the venv).
- Finds LibreOffice / soffice on the system.
- Resolves user-supplied paths against the caller's cwd (the dispatcher runs
  scripts with cwd=ROOT, so a relative path would otherwise resolve inside the
  skill folder).
"""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Maps a dependency tag in actions.json to its importable module + pip package.
DEP_MAP = {
    "docx": ("docx", "python-docx"),
    "xlsx": ("openpyxl", "openpyxl"),
    "pptx": ("pptx", "python-pptx"),
}

DEFAULT_VENV = Path.home() / ".workbuddy" / "office-all-done-env"
REQUIREMENTS = ["python-docx>=1.1,<2", "openpyxl>=3.1,<4", "python-pptx>=0.6,<1"]


def venv_path():
    return Path(os.environ.get("OFFICE_WORKSHOP_VENV", str(DEFAULT_VENV))).resolve()


def venv_python(root):
    if os.name == "nt":
        return root / "Scripts" / "python.exe"
    return root / "bin" / "python"


def importable(module):
    return importlib.util.find_spec(module) is not None


def venv_has_lib(root, module):
    py = venv_python(root)
    if not py.exists():
        return False
    proc = subprocess.run(
        [str(py), "-c", "import %s" % module],
        capture_output=True, text=True,
    )
    return proc.returncode == 0


def choose_python(dep_tags):
    """Return the interpreter that can import every library in dep_tags.

    Falls back to sys.executable when nothing qualifies (the script will then
    emit a clear install hint rather than a stack trace).
    """
    modules = [DEP_MAP[t][0] for t in dep_tags if t in DEP_MAP]
    if not modules:
        return sys.executable
    if all(importable(m) for m in modules):
        return sys.executable
    root = venv_path()
    if all(venv_has_lib(root, m) for m in modules):
        return str(venv_python(root))
    return sys.executable


def find_soffice():
    explicit = os.environ.get("SOFFICE")
    if explicit and Path(explicit).exists():
        return explicit
    found = shutil.which("soffice") or shutil.which("libreoffice")
    if found:
        return found
    if os.name == "nt":
        candidates = [
            Path(os.environ.get("ProgramFiles", "C:/Program Files"))
            / "LibreOffice" / "program" / "soffice.exe",
            Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)"))
            / "LibreOffice" / "program" / "soffice.exe",
        ]
        for c in candidates:
            if c.exists():
                return str(c)
    return None


def soffice_convert(input_path, output_path, registry=None, action=None):
    """Convert a document to PDF via LibreOffice headless.

    soffice only lets us choose an output directory, not the file name, so we
    convert into a temp dir and then move the result to output_path. Returns the
    output path on success; exits with a clear message + online link when
    LibreOffice is unavailable.
    """
    import shutil
    import tempfile

    soffice = find_soffice()
    if not soffice:
        msg = "本机未安装 LibreOffice（soffice），无法转 PDF。"
        if registry is not None and action is not None:
            msg += "\n在线替代：%s" % online_url(registry, action)
        else:
            msg += "\n本技能不提供第三方在线替代方案，请按本机安装指引补齐依赖。"
        sys.exit(msg)
    src = Path(input_path).resolve()
    out = Path(output_path).resolve()
    tmp = Path(tempfile.mkdtemp(prefix="office2pdf_"))
    profile = tmp / "profile"
    cmd = [
        soffice, "--headless", "--norestore",
        "-env:UserInstallation=file://%s" % str(profile).replace("\\", "/"),
        "--convert-to", "pdf", "--outdir", str(tmp), str(src),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                          errors="replace")
    produced = tmp / (src.stem + ".pdf")
    if proc.returncode != 0 or not produced.exists():
        sys.exit("soffice 转换失败（exit=%d）：%s" %
                 (proc.returncode, (proc.stderr or proc.stdout)[-800:]))
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(produced), str(out))
    shutil.rmtree(str(tmp), ignore_errors=True)
    return str(out)


def resolve(path):
    """Resolve a user path against the caller's cwd, not the skill folder."""
    return str(Path(path).resolve())


def check_dependencies(tags):
    missing = []
    for tag in tags:
        if tag in DEP_MAP:
            mod, pip = DEP_MAP[tag]
            if not (importable(mod) or venv_has_lib(venv_path(), mod)):
                missing.append("%s (%s)" % (tag, pip))
        elif tag == "soffice":
            if not find_soffice():
                missing.append("soffice (LibreOffice)")
    return missing


def online_url(registry, action):
    # 显式 null = 该站确实没有对应工具，不要回落到站点首页冒充替代方案
    if "online" in action and not action.get("online"):
        return "无（roroto.com 无对应工具）"
    return action.get("online") or registry.get("online_root", "https://roroto.com")


def main():
    # Simple self-check for `python scripts/office_common.py`
    info = {
        "venv": str(venv_path()),
        "python-docx": importable("docx") or venv_has_lib(venv_path(), "docx"),
        "openpyxl": importable("openpyxl") or venv_has_lib(venv_path(), "openpyxl"),
        "python-pptx": importable("pptx") or venv_has_lib(venv_path(), "pptx"),
        "soffice": bool(find_soffice()),
    }
    print(json.dumps(info, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
