#!/usr/bin/env python3
"""doc-convert: convert between md/txt/csv and extract any doc to plain text.

Office/PDF -> text uses ingest; md/txt/csv interconvert directly. PDF/Office
to PDF needs a browser/Office engine and is intentionally left to the online
alternative or pdf-workshop to avoid silent failures.
"""
import argparse
import csv
import importlib.util
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ingest  # noqa: E402


def _xlsx_first_sheet(path):
    """Real CSV needs cells, not the pipe-joined text ingest produces."""
    if importlib.util.find_spec("openpyxl") is None:
        return None
    import openpyxl
    wb = openpyxl.load_workbook(str(path), data_only=True, read_only=True)
    if not wb.worksheets:
        return []
    ws = wb.worksheets[0]
    return [["" if c is None else c for c in row]
            for row in ws.iter_rows(values_only=True)]


def _text_rows(text):
    rows = []
    for line in text.splitlines():
        if not line.strip():
            continue
        if "|" in line:
            rows.append([c.strip() for c in line.split("|")])
        elif "\t" in line:
            rows.append([c.strip() for c in line.split("\t")])
        else:
            rows.append([line.strip()])
    return rows


def main():
    p = argparse.ArgumentParser(description="Document format conversion")
    p.add_argument("input")
    p.add_argument("-o", "--output", required=True)
    p.add_argument("--to", default="txt", choices=["md", "txt", "csv", "pdf"])
    ns = p.parse_args()
    res = ingest.extract(ns.input)
    out = Path(ns.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    text = res["text"]
    warnings = list(res["warnings"])

    if ns.to == "pdf":
        print(json.dumps({"status": "error",
                          "message": "转 PDF 需本机浏览器/Office，建议先用 doc-to-text 抽取，"
                                     "再用 pdf-workshop 生成，或选在线替代"}, ensure_ascii=False))
        return 1
    if ns.to == "csv":
        rows = None
        if res["format"] in ("xlsx", "xlsm"):
            rows = _xlsx_first_sheet(ns.input)
            if rows is not None:
                warnings.append("CSV 仅导出首个工作表；多表请用 extract-tables")
        if rows is None:
            rows = _text_rows(text)
        with open(out, "w", newline="", encoding="utf-8-sig") as fh:
            csv.writer(fh).writerows(rows)
    else:
        out.write_text(text, encoding="utf-8")
    print(json.dumps({"output": str(out), "to": ns.to,
                      "format": res["format"], "warnings": warnings},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
