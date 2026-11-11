#!/usr/bin/env python3
"""Convert a .docx file to PDF via LibreOffice (soffice).

Requires LibreOffice on PATH or SOFFICE env var; otherwise exits with an online
fallback link. See office_common.soffice_convert for details.
"""

import argparse
import json
import sys
from pathlib import Path

import office_common as oc

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "assets" / "actions.json"


def main():
    p = argparse.ArgumentParser(description="Convert .docx to PDF")
    p.add_argument("input")
    p.add_argument("-o", "--output", required=True)
    ns = p.parse_args()

    reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
    action = next(a for a in reg["actions"] if a["id"] == "docx-to-pdf")
    out = oc.soffice_convert(ns.input, ns.output, reg, action)
    print("done: %s" % out)
    print("bytes=%d" % Path(out).stat().st_size)
    return 0


if __name__ == "__main__":
    sys.exit(main())
