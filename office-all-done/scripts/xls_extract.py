#!/usr/bin/env python3
"""Export every worksheet of an .xlsx file to CSV / JSON / Markdown.

The -o path is treated as a DIRECTORY; one file per sheet is written there
(<sheet>.<ext>). Empty sheets are skipped with a warning. Install openpyxl via
`python scripts/bootstrap.py install`.
"""

import argparse
import csv
import json
import sys
from pathlib import Path

try:
    import openpyxl
except ImportError:
    sys.exit("缺少 openpyxl。请先运行：python scripts/bootstrap.py install")


def sheet_rows(ws):
    for row in ws.iter_rows(values_only=True):
        yield ["" if v is None else v for v in row]


def export_csv(ws, path):
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh)
        for row in sheet_rows(ws):
            writer.writerow(row)


def export_json(ws, path):
    rows = list(sheet_rows(ws))
    if not rows:
        return False
    header = [str(h) for h in rows[0]]
    objs = []
    for r in rows[1:]:
        objs.append({header[i]: r[i] for i in range(len(header))})
    path.write_text(json.dumps(objs, ensure_ascii=False, indent=2), encoding="utf-8")
    return True


def export_md(ws, path):
    rows = list(sheet_rows(ws))
    if not rows:
        return False
    lines = []
    for i, r in enumerate(rows):
        cells = [" " if c == "" else str(c) for c in r]
        lines.append("| " + " | ".join(cells) + " |")
        if i == 0:
            lines.append("| " + " | ".join(["---"] * len(r)) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True


def main():
    p = argparse.ArgumentParser(description="Export xlsx sheets to data files")
    p.add_argument("input")
    p.add_argument("-o", "--output", required=True)
    p.add_argument("--format", choices=("csv", "json", "md"), default="csv")
    ns = p.parse_args()

    wb = openpyxl.load_workbook(ns.input, data_only=True, read_only=True)
    out_dir = Path(ns.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    writers = {"csv": export_csv, "json": export_json, "md": export_md}
    ext = ns.format
    count = 0
    for ws in wb.worksheets:
        safe = ws.title.replace("/", "_").replace("\\", "_")
        path = out_dir / ("%s.%s" % (safe, ext))
        ok = writers[ns.format](ws, path)
        if ok:
            count += 1
            print("exported: %s (%d rows)" % (path.name, ws.max_row or 0))
        else:
            print("skipped empty sheet: %s" % ws.title)
    wb.close()
    print("done: %s | sheets exported=%d" % (out_dir, count))
    return 0


if __name__ == "__main__":
    sys.exit(main())
