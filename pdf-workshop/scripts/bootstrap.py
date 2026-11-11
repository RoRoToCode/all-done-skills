#!/usr/bin/env python3
"""Check or install the optional dependencies used by pdf_ops.py and ocr_pdf.py.

Two dependency groups:

  pypdf  pure Python, small, only needed for encrypt/decrypt and page edits.
         Installed into an isolated venv outside the skill folder by default,
         so packaging the skill never bundles a virtual environment.

  ocr    rapidocr-onnxruntime, needed only for scanned PDFs. Installed into the
         *current interpreter*, because ocr_pdf.py must import it in the same
         process that runs the pipeline; a separate venv would be invisible.

Run `install` only after telling the user it will download packages from PyPI.
"""

import argparse
import json
import os
import subprocess
import sys
import venv
from pathlib import Path

DEFAULT_VENV = Path.home() / ".workbuddy" / "pdf-workshop-env"
REQUIREMENT = "pypdf>=5,<8"
OCR_REQUIREMENT = "rapidocr-onnxruntime>=1.3"


def venv_path():
    return Path(os.environ.get("PDF_WORKSHOP_VENV", str(DEFAULT_VENV))).resolve()


def venv_python(root):
    if os.name == "nt":
        return root / "Scripts" / "python.exe"
    return root / "bin" / "python"


def _pypdf_status():
    try:
        import pypdf  # noqa: F401
        return {"status": "ok", "source": "current interpreter",
                "python": sys.executable, "version": getattr(pypdf, "__version__", "?")}
    except ImportError:
        root = venv_path()
        python = venv_python(root)
        if python.exists():
            proc = subprocess.run([str(python), "-c", "import pypdf; print(pypdf.__version__)"],
                                  capture_output=True, text=True)
            if proc.returncode == 0:
                return {"status": "ok", "source": "isolated venv",
                        "python": str(python), "version": proc.stdout.strip()}
        return {"status": "missing", "python": str(python),
                "hint": "python scripts/bootstrap.py install"}


def _ocr_status():
    try:
        import rapidocr_onnxruntime  # noqa: F401
        return {"status": "ok", "engine": "rapidocr", "python": sys.executable}
    except ImportError:
        pass
    hint = "python scripts/bootstrap.py install --ocr"
    if not any(_has_binary(name) for name in ("tesseract", "paddleocr")):
        hint += "（或装 Tesseract + chi_sim 让官方 CLI 通道接管）"
    return {"status": "missing", "engine": None, "python": sys.executable,
            "hint": hint}


def _has_binary(name):
    from shutil import which
    return bool(which(name))


def check():
    info = {"pypdf": _pypdf_status(), "ocr": _ocr_status()}
    info["status"] = "ok" if info["pypdf"]["status"] == "ok" else "missing"
    if info["ocr"]["status"] != "ok":
        info["note"] = "缺 OCR 引擎时扫描件无法识别，纯文本 PDF 不受影响。"
    print(json.dumps(info, ensure_ascii=False, indent=2))
    return 0 if info["status"] == "ok" else 2


def _pip(python, args):
    return subprocess.run([python, "-m", "pip", "install",
                           "--disable-pip-version-check"] + args,
                          capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


# rapidocr's runtime imports and the PyPI names that provide them.
OCR_RUNTIME = {
    "cv2": "opencv-python",
    "numpy": "numpy",
    "onnxruntime": "onnxruntime",
    "PIL": "Pillow",
    "yaml": "PyYAML",
    "shapely": "shapely",
    "pyclipper": "pyclipper",
    "six": "six",
}


def _missing_runtime():
    import importlib.util
    return [pkg for module, pkg in OCR_RUNTIME.items()
            if importlib.util.find_spec(module) is None]


def _ocr_importable():
    proc = subprocess.run([sys.executable, "-c",
                           "import rapidocr_onnxruntime as r; print('ok')"],
                          capture_output=True, text=True)
    return proc.returncode == 0 and "ok" in (proc.stdout or "")


def install_ocr():
    """Install rapidocr into the current interpreter.

    A plain `pip install rapidocr-onnxruntime` resolves its declared deps and
    pulls a 44 MB opencv-python wheel, which stalls on slow links even when a
    working `cv2` is already importable. So: if every runtime module the engine
    needs is importable, install with --no-deps and only fetch what is really
    missing; otherwise fall back to a full install.
    """
    if _ocr_importable():
        print(json.dumps({"status": "ok", "group": "ocr", "mode": "already-installed",
                          "python": sys.executable}, ensure_ascii=False))
        return 0

    missing = _missing_runtime()
    if missing:
        proc = _pip(sys.executable, [OCR_REQUIREMENT])
        mode = "full"
    else:
        proc = _pip(sys.executable, ["--no-deps", OCR_REQUIREMENT])
        mode = "no-deps"

    if not _ocr_importable() and proc.returncode == 0:
        # engine installed but still not importable:补齐真正缺的运行时
        gaps = _missing_runtime()
        if gaps:
            _pip(sys.executable, ["--only-binary", ":all:"] + gaps)
            mode += "+runtime(" + ",".join(gaps) + ")"

    ok = _ocr_importable()
    print(json.dumps({"status": "ok" if ok else "error", "group": "ocr",
                      "mode": mode, "python": sys.executable,
                      "missing_runtime": missing,
                      "stdout": (proc.stdout or "")[-400:],
                      "stderr": (proc.stderr or "")[-400:]}, ensure_ascii=False))
    return 0 if ok else 1


def install(args):
    if args.ocr:
        return install_ocr()
    if args.system:
        cmd = [sys.executable, "-m", "pip", "install", "--user", REQUIREMENT]
        python = sys.executable
    else:
        root = venv_path()
        root.parent.mkdir(parents=True, exist_ok=True)
        if not venv_python(root).exists():
            venv.EnvBuilder(with_pip=True).create(str(root))
        python = str(venv_python(root))
        cmd = [python, "-m", "pip", "install", "--disable-pip-version-check",
               REQUIREMENT]
    proc = subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    ok = proc.returncode == 0
    print(json.dumps({"status": "ok" if ok else "error", "group": "pypdf",
                      "python": python, "stdout": proc.stdout[-800:],
                      "stderr": proc.stderr[-800:]}, ensure_ascii=False))
    if ok and not args.system:
        print("后续请用该解释器运行 pdf_ops.py：%s" % python, file=sys.stderr)
    return 0 if ok else 1


def main():
    p = argparse.ArgumentParser(description="Manage pdf-workshop dependencies")
    sub = p.add_subparsers(dest="action", required=True)
    sub.add_parser("check")
    i = sub.add_parser("install")
    i.add_argument("--system", action="store_true",
                   help="install pypdf into the current interpreter instead of a venv")
    i.add_argument("--ocr", action="store_true",
                   help="install the RapidOCR OCR engine into the current interpreter")
    args = p.parse_args()
    return check() if args.action == "check" else install(args)


if __name__ == "__main__":
    sys.exit(main())
