#!/usr/bin/env python3
"""extract-tables: pull tables out of a document into per-table CSV files.

PDF  -> host workbuddy-pdf CLI (-f table)
XLSX -> one CSV per sheet
DOCX -> one CSV per table
PPTX -> one CSV per table shape
HTML -> one CSV per <table>
CSV/TSV/TXT -> copied through
"""
import argparse
import csv
import importlib.util
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ingest  # noqa: E402


def _write_csv(outdir, name, rows):
    f = outdir / name
    with open(f, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        for r in rows:
            w.writerow(["" if c is None else c for c in r])
    return str(f)


def _from_xlsx(path, outdir):
    if importlib.util.find_spec("openpyxl") is None:
        return [], ["缺 openpyxl，无法解析 XLSX 表格"]
    import openpyxl
    wb = openpyxl.load_workbook(str(path), data_only=True)
    written = []
    for ws in wb.worksheets:
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            continue
        safe = "".join(c for c in ws.title if c not in '\\/:*?"<>|') or ws.title
        written.append(_write_csv(outdir, safe + ".csv", rows))
    return written, []


def _from_docx(path, outdir):
    if importlib.util.find_spec("docx") is None:
        return [], ["缺 python-docx，无法解析 DOCX 表格"]
    import docx
    doc = docx.Document(str(path))
    written = []
    for idx, table in enumerate(doc.tables, 1):
        rows = [[c.text.strip() for c in row.cells] for row in table.rows]
        rows = [r for r in rows if any(x for x in r)]
        if not rows:
            continue
        written.append(_write_csv(outdir, "table-%02d.csv" % idx, rows))
    warnings = [] if written else ["文档中未发现表格"]
    return written, warnings


def _from_pptx(path, outdir):
    if importlib.util.find_spec("pptx") is None:
        return [], ["缺 python-pptx，无法解析 PPTX 表格"]
    from pptx import Presentation
    prs = Presentation(str(path))
    written = []
    for s_idx, slide in enumerate(prs.slides, 1):
        for t_idx, shape in enumerate(slide.shapes, 1):
            if not getattr(shape, "has_table", False):
                continue
            rows = [[c.text.strip() for c in row.cells]
                    for row in shape.table.rows]
            if not any(any(x for x in r) for r in rows):
                continue
            written.append(_write_csv(
                outdir, "slide%02d-table%02d.csv" % (s_idx, t_idx), rows))
    warnings = [] if written else ["文档中未发现表格"]
    return written, warnings


def _from_html(path, outdir):
    if importlib.util.find_spec("bs4") is None:
        return [], ["缺 bs4，无法解析 HTML 表格"]
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(Path(path).read_text(encoding="utf-8",
                                             errors="replace"),
                         "html.parser")
    written = []
    for idx, table in enumerate(soup.find_all("table"), 1):
        rows = []
        for tr in table.find_all("tr"):
            cells = [c.get_text(" ", strip=True)
                     for c in tr.find_all(["th", "td"])]
            if cells:
                rows.append(cells)
        if rows:
            written.append(_write_csv(outdir, "table-%02d.csv" % idx, rows))
    warnings = [] if written else ["文档中未发现表格"]
    return written, warnings


def main():
    p = argparse.ArgumentParser(description="Extract tables")
    p.add_argument("input")
    p.add_argument("-o", "--output", required=True)
    ns = p.parse_args()
    inp = Path(ns.input)
    outdir = Path(ns.output)
    outdir.mkdir(parents=True, exist_ok=True)
    suffix = inp.suffix.lower()
    written, warnings = [], []

    if suffix == ".pdf":
        try:
            spec = importlib.util.spec_from_file_location(
                "pdf_cli_local", Path(__file__).resolve().parent / "pdf_cli.py")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if mod.command_prefix():
                code = mod.run_action(["read", str(inp), "-o",
                                      str(outdir / "tables"), "-f", "table",
                                      "--table-format", "csv"])
                if code == 0:
                    written = [str(x) for x in outdir.glob("**/*.csv")]
                else:
                    warnings.append("宿主 CLI 表格抽取失败（退出码 %d）" % code)
            else:
                warnings.append("缺宿主 PDF CLI，PDF 表格请改用在线替代")
        except Exception as exc:  # noqa: BLE001
            warnings.append("PDF 表格抽取异常：%s" % exc)
    elif suffix in (".xlsx", ".xlsm"):
        written, warnings = _from_xlsx(inp, outdir)
    elif suffix == ".docx":
        written, warnings = _from_docx(inp, outdir)
    elif suffix == ".pptx":
        written, warnings = _from_pptx(inp, outdir)
    elif suffix in (".html", ".htm"):
        written, warnings = _from_html(inp, outdir)
    elif suffix in (".csv", ".tsv", ".txt"):
        dest = outdir / (inp.stem + ".csv")
        shutil.copy(inp, dest)
        written = [str(dest)]
    else:
        warnings.append("该格式暂不支持表格抽取：%s" % suffix)

    print(json.dumps({"output": str(outdir), "tables": len(written),
                      "files": written, "warnings": warnings},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
