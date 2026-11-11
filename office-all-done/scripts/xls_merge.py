#!/usr/bin/env python3
"""Merge all worksheets from multiple .xlsx files into one workbook.

Each source sheet is copied into the target workbook; duplicate sheet titles get
a numeric suffix. Only cell values and number formats are copied (formulas become
their computed values). Install openpyxl via `python scripts/bootstrap.py install`.
"""

import argparse
import sys
from pathlib import Path

try:
    import openpyxl
    from openpyxl.utils import get_column_letter
except ImportError:
    sys.exit("缺少 openpyxl。请先运行：python scripts/bootstrap.py install")


def unique_title(base, used):
    if base not in used:
        used.add(base)
        return base
    i = 2
    while "%s_%d" % (base, i) in used:
        i += 1
    name = "%s_%d" % (base, i)
    used.add(name)
    return name


def copy_sheet(src_ws, target_wb, used):
    title = unique_title(src_ws.title, used)
    dst = target_wb.create_sheet(title=title)
    for row in src_ws.iter_rows():
        for cell in row:
            dst_cell = dst.cell(row=cell.row, column=cell.column)
            dst_cell.value = cell.value
            if cell.number_format and cell.number_format != "General":
                dst_cell.number_format = cell.number_format
    # keep column widths / row heights and merged ranges so the layout survives
    for col, dim in getattr(src_ws, "column_dimensions", {}).items():
        if dim.width:
            dst.column_dimensions[col].width = dim.width
    for idx, dim in getattr(src_ws, "row_dimensions", {}).items():
        if dim.height:
            dst.row_dimensions[idx].height = dim.height
    for rng in list(getattr(src_ws, "merged_cells", []).ranges):
        dst.merge_cells(str(rng))
    if src_ws.freeze_panes:
        dst.freeze_panes = src_ws.freeze_panes
    return title


def main():
    p = argparse.ArgumentParser(description="Merge xlsx workbooks")
    p.add_argument("inputs", nargs="+")
    p.add_argument("-o", "--output", required=True)
    ns = p.parse_args()

    if ns.output in ns.inputs:
        sys.exit("refusing to overwrite an input file")

    target = openpyxl.Workbook()
    target.remove(target.active)
    used = set()
    sheets = 0
    for src_path in ns.inputs:
        # not read_only: column widths / merged ranges / freeze panes are only
        # available on a fully loaded worksheet
        src = openpyxl.load_workbook(src_path, data_only=True)
        for ws in src.worksheets:
            copy_sheet(ws, target, used)
            sheets += 1
        src.close()

    out = Path(ns.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    target.save(str(out))
    print("done: %s" % out)
    print("sources=%d sheets=%d" % (len(ns.inputs), sheets))
    return 0


if __name__ == "__main__":
    sys.exit(main())
