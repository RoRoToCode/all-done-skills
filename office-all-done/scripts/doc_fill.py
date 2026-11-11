#!/usr/bin/env python3
"""Fill {{key}} placeholders in a .docx template from a JSON data source.

--data accepts, in this order: a path to a .json file, an inline JSON object, or
`key=value` pairs separated by `;` (handy on Windows, where the command line
tends to swallow the double quotes of inline JSON).

The template is never modified; the result is written to a new file. Body
paragraphs, tables, headers and footers are all covered. When a placeholder is
split across several runs, the first run's formatting wins.

Install python-docx via `python scripts/bootstrap.py install`.
"""

import argparse
import json
import re
import sys
from pathlib import Path

try:
    from docx import Document
except ImportError:
    sys.exit("缺少 python-docx。请先运行：python scripts/bootstrap.py install")

PLACEHOLDER = re.compile(r"\{\{\s*([^{}]+?)\s*\}\}")


def parse_pairs(raw):
    """Parse `k=v;k=v` into a dict. Only `;`/newline separate pairs, so values
    may contain commas (e.g. 金额=1,280,000)."""
    data = {}
    for chunk in re.split(r"[;\n]", raw):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "=" not in chunk:
            return None
        key, value = chunk.split("=", 1)
        data[key.strip()] = value.strip()
    return data or None


def load_data(raw):
    path = Path(raw)
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        obj = None
    if isinstance(obj, dict):
        return obj
    pairs = parse_pairs(raw)
    if pairs:
        return pairs
    sys.exit("--data 无法解析：%s\n"
             "可传入 ①JSON 文件路径 ②内联 JSON（Windows 下引号易被吞）"
             " ③key=value 形式，多组用 ; 分隔" % raw[:120])


def apply_text(text, data):
    for key, value in data.items():
        text = text.replace("{{%s}}" % key, str(value))
        text = text.replace("{{ %s }}" % key, str(value))
    return text


def fill_paragraph(paragraph, data):
    if "{{" not in paragraph.text:
        return 0
    full = "".join(run.text for run in paragraph.runs)
    new = apply_text(full, data)
    if new == full or not paragraph.runs:
        return 0
    first = paragraph.runs[0]
    first.text = new
    for run in paragraph.runs[1:]:
        run._element.getparent().remove(run._element)
    return 1


def iter_paragraphs(document):
    for paragraph in document.paragraphs:
        yield paragraph
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    yield paragraph
    for section in document.sections:
        for part in (section.header, section.footer,
                     section.first_page_header, section.first_page_footer,
                     section.even_page_header, section.even_page_footer):
            if part is None:
                continue
            for paragraph in part.paragraphs:
                yield paragraph
            for table in part.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for paragraph in cell.paragraphs:
                            yield paragraph


def remaining(document):
    found = []
    for paragraph in iter_paragraphs(document):
        found.extend(PLACEHOLDER.findall(paragraph.text))
    return sorted(set(found))


def main():
    p = argparse.ArgumentParser(description="Fill docx template placeholders")
    p.add_argument("input")
    p.add_argument("-o", "--output", required=True)
    p.add_argument("--data", required=True,
                   help="JSON file path, inline JSON, or key=value pairs")
    ns = p.parse_args()

    data = load_data(ns.data)
    document = Document(ns.input)

    touched = 0
    for paragraph in iter_paragraphs(document):
        touched += fill_paragraph(paragraph, data)

    out = Path(ns.output).resolve()
    if str(out) == str(Path(ns.input).resolve()):
        sys.exit("refusing to overwrite the template")
    out.parent.mkdir(parents=True, exist_ok=True)
    document.save(str(out))

    print("done: %s" % out)
    print("keys=%d paragraphs_filled=%d bytes=%d" %
          (len(data), touched, out.stat().st_size))
    left = remaining(Document(str(out)))
    if left:
        print("warning: 仍有占位符未替换：%s" % ", ".join(left[:10]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
