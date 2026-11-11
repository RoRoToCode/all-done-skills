#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check or install the two runtime dependencies of the OCR pipeline.

  ocr   rapidocr-onnxruntime — pure Python, models ship inside the wheel, no
        external binary. Installed into the *current interpreter* because the
        pipeline imports it in-process.
  pdf   pymupdf — page rendering for PDF inputs. Images need nothing extra.

A plain `pip install rapidocr-onnxruntime` resolves its declared dependencies
and pulls a 44 MB opencv-python wheel, which stalls on slow links even when a
working cv2 is already importable. So the installer checks the runtime modules
first and installs with --no-deps when they are all present.

Run `install` only after telling the user it will download packages from PyPI.
"""

import argparse
import json
import subprocess
import sys

OCR_REQUIREMENT = "rapidocr-onnxruntime>=1.3"
PDF_REQUIREMENT = "pymupdf>=1.24"

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


def _spec(name):
    import importlib.util
    return importlib.util.find_spec(name) is not None


def _missing(mapping):
    return [pkg for module, pkg in mapping.items() if not _spec(module)]


def _pip(args):
    return subprocess.run([sys.executable, "-m", "pip", "install",
                           "--disable-pip-version-check"] + args,
                          capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def _importable(snippet):
    proc = subprocess.run([sys.executable, "-c", snippet],
                          capture_output=True, text=True)
    return proc.returncode == 0


def check():
    ocr_ok = _spec("rapidocr_onnxruntime")
    pdf_ok = _spec("pymupdf") or _spec("fitz")
    info = {
        "ocr": {"status": "ok" if ocr_ok else "missing",
                "package": "rapidocr-onnxruntime",
                "hint": "python scripts/bootstrap.py install --ocr"},
        "pdf": {"status": "ok" if pdf_ok else "missing",
                "package": "pymupdf",
                "hint": "python scripts/bootstrap.py install --pdf"},
        "python": sys.executable,
    }
    info["status"] = "ok" if ocr_ok else "missing"
    print(json.dumps(info, ensure_ascii=False, indent=2))
    return 0 if info["status"] == "ok" else 2


def install_ocr():
    if _importable("import rapidocr_onnxruntime; print('ok')"):
        print(json.dumps({"status": "ok", "group": "ocr",
                          "mode": "already-installed",
                          "python": sys.executable}, ensure_ascii=False))
        return 0
    missing = _missing(OCR_RUNTIME)
    if missing:
        proc = _pip([OCR_REQUIREMENT])
        mode = "full"
    else:
        proc = _pip(["--no-deps", OCR_REQUIREMENT])
        mode = "no-deps"
    if proc.returncode == 0 and not _importable("import rapidocr_onnxruntime"):
        gaps = _missing(OCR_RUNTIME)
        if gaps:
            _pip(["--only-binary", ":all:"] + gaps)
            mode += "+runtime(" + ",".join(gaps) + ")"
    ok = _importable("import rapidocr_onnxruntime; print('ok')")
    print(json.dumps({"status": "ok" if ok else "error", "group": "ocr",
                      "mode": mode, "python": sys.executable,
                      "missing_runtime": missing,
                      "stdout": (proc.stdout or "")[-400:],
                      "stderr": (proc.stderr or "")[-400:]}, ensure_ascii=False))
    return 0 if ok else 1


def install_pdf():
    if _importable("import pymupdf; print('ok')"):
        print(json.dumps({"status": "ok", "group": "pdf",
                          "mode": "already-installed",
                          "python": sys.executable}, ensure_ascii=False))
        return 0
    proc = _pip([PDF_REQUIREMENT])
    ok = proc.returncode == 0 and _importable("import pymupdf; print('ok')")
    print(json.dumps({"status": "ok" if ok else "error", "group": "pdf",
                      "mode": "full", "python": sys.executable,
                      "stdout": (proc.stdout or "")[-400:],
                      "stderr": (proc.stderr or "")[-400:]}, ensure_ascii=False))
    return 0 if ok else 1


def main():
    p = argparse.ArgumentParser(description="Manage ocr-workshop dependencies")
    sub = p.add_subparsers(dest="action", required=True)
    sub.add_parser("check")
    i = sub.add_parser("install")
    i.add_argument("--ocr", action="store_true", help="install the OCR engine")
    i.add_argument("--pdf", action="store_true", help="install PyMuPDF for PDF input")
    args = p.parse_args()

    if args.action == "check":
        return check()
    if not args.ocr and not args.pdf:
        return max(install_ocr(), install_pdf())
    code = 0
    if args.ocr:
        code = max(code, install_ocr())
    if args.pdf:
        code = max(code, install_pdf())
    return code


if __name__ == "__main__":
    sys.exit(main())
