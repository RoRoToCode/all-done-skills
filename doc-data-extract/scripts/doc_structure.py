#!/usr/bin/env python3
"""doc-structure: page-aware block tree + outline for any supported document.

Blocks: heading / paragraph / list / table / quote.
Heading detection is heuristic (markdown levels, 第X章/节, 一、, （一）, 1.2.3).
Each block is tagged with its page number so downstream steps can cite it.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ingest  # noqa: E402

MD_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*$")
CN_CHAPTER = re.compile(r"^(第[一二三四五六七八九十百零〇\d]+[章篇部分])\s*(.*)$")
CN_SECTION = re.compile(r"^(第[一二三四五六七八九十百零〇\d]+节)\s*(.*)$")
CN_CLAUSE = re.compile(r"^([一二三四五六七八九十]+)[、.．]\s*(.+)$")
CN_PAREN = re.compile(r"^[（(]([一二三四五六七八九十]+)[）)]\s*(.+)$")
NUM_HEADING = re.compile(r"^(\d+(?:\.\d+){0,2})[、.．]?\s+(\S.{0,60})$")
BULLET = re.compile(r"^(?:[-*+•·▪◦]\s+|\d+[.)、]\s+)")
QUOTE = re.compile(r"^>\s?")
SENT_END = "。！？；：，、,.;:!?)）】」』"


def _is_heading(line):
    """Return (level, title) when the line looks like a heading, else None."""
    m = MD_HEADING.match(line)
    if m:
        return len(m.group(1)), m.group(2).strip()
    m = CN_CHAPTER.match(line)
    if m and len(line) <= 40 and not line.endswith(tuple(SENT_END)):
        return 1, (m.group(1) + " " + m.group(2)).strip()
    m = CN_SECTION.match(line)
    if m and len(line) <= 40 and not line.endswith(tuple(SENT_END)):
        return 2, (m.group(1) + " " + m.group(2)).strip()
    m = CN_CLAUSE.match(line)
    if m and len(line) <= 40 and not line.endswith(tuple(SENT_END)):
        return 2, line.strip()
    m = CN_PAREN.match(line)
    if m and len(line) <= 40 and not line.endswith(tuple(SENT_END)):
        return 3, line.strip()
    m = NUM_HEADING.match(line)
    if m and len(m.group(2)) <= 40 and not m.group(2).endswith(tuple(SENT_END)):
        depth = m.group(1).count(".") + 1
        if depth <= 4:
            return depth, line.strip()
    return None


def _join(prev, nxt):
    """Join hard-wrapped lines: no space between CJK, one space otherwise."""
    if not prev:
        return nxt
    a, b = prev[-1], nxt[0]
    if "\u4e00" <= a <= "\u9fff" or "\u4e00" <= b <= "\u9fff":
        return prev + nxt
    return prev + " " + nxt


SEP_ROW = re.compile(r"^\|?[\s:|-]+\|?$")


def _is_table_line(line):
    return "|" in line and bool(line.strip())


def parse_page(text, page_no):
    blocks = []
    lines = [ln.rstrip() for ln in text.splitlines()]
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        if _is_table_line(line):
            rows, j = [], i
            while j < len(lines) and _is_table_line(lines[j].strip()):
                rows.append(lines[j].strip())
                j += 1
            rows = [r for r in rows if not SEP_ROW.match(r)]
            if len(rows) >= 2:
                blocks.append({"type": "table", "page": page_no,
                               "rows": len(rows), "text": "\n".join(rows)})
                i = j
                continue

        heading = _is_heading(line)
        if heading:
            blocks.append({"type": "heading", "page": page_no,
                           "level": heading[0], "text": heading[1]})
            i += 1
            continue

        if BULLET.match(line):
            items = []
            while i < len(lines):
                cur = lines[i].strip()
                if not cur:
                    break
                if BULLET.match(cur):
                    items.append(BULLET.sub("", cur).strip())
                elif items and not _is_heading(cur) and not _is_table_line(cur):
                    items[-1] = _join(items[-1], cur)
                else:
                    break
                i += 1
            blocks.append({"type": "list", "page": page_no,
                           "items": items, "text": "\n".join(items)})
            continue

        if QUOTE.match(line):
            blocks.append({"type": "quote", "page": page_no,
                           "text": QUOTE.sub("", line).strip()})
            i += 1
            continue

        para = line
        i += 1
        while i < len(lines):
            cur = lines[i].strip()
            if (not cur or _is_heading(cur) or BULLET.match(cur)
                    or QUOTE.match(cur) or _is_table_line(cur)):
                break
            para = _join(para, cur)
            i += 1
        blocks.append({"type": "paragraph", "page": page_no, "text": para})

    return blocks


def run(path):
    res = ingest.extract(path)
    pages, outline = [], []
    index = 0
    for item in res["pages"]:
        blocks = parse_page(item["text"], item["page"])
        for block in blocks:
            block["index"] = index
            index += 1
            if block["type"] == "heading":
                outline.append({"level": block["level"],
                                "title": block["text"],
                                "page": block["page"],
                                "index": block["index"]})
        pages.append({"page": item["page"], "blocks": blocks})

    counts = {"heading": 0, "paragraph": 0, "list": 0, "table": 0, "quote": 0}
    for page in pages:
        for block in page["blocks"]:
            counts[block["type"]] += 1
    warnings = list(res["warnings"])
    if res["format"] == "pdf" and counts["table"] == 0:
        warnings.append("PDF 转 Markdown 会丢失表格竖线，结构里可能看不到表格；"
                        "表格请用 extract-tables 单独抽取")
    return {
        "file": str(Path(path).resolve()),
        "format": res["format"],
        "pages": pages,
        "outline": outline,
        "stats": {"pages": len(pages), "blocks": index,
                  "chars": len(res["text"]), **counts},
        "warnings": warnings,
    }


def main():
    p = argparse.ArgumentParser(description="Document layout structure")
    p.add_argument("input")
    p.add_argument("-o", "--output", required=True)
    ns = p.parse_args()
    doc = run(ns.input)
    out = Path(ns.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    print(json.dumps({"output": str(out), "format": doc["format"],
                      "stats": doc["stats"],
                      "outline_head": doc["outline"][:3],
                      "warnings": doc["warnings"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
