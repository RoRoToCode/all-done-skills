#!/usr/bin/env python3
"""真删除 PDF 里的敏感文字（redaction），不是画白块盖住。

字面量模式用 page.search_for() 精确定位；正则模式按文本 span 命中——一个
span 命中就整段涂抹，宁可多删不可漏删，并在报告里写清命中了哪几段。

扫描件没有文字层，任何模式下都会命中 0 处：这种情况要么先做 OCR 生成
可搜索 PDF，要么把整页转成图片再处理，脚本会明确告警而不是假装成功。
"""

import argparse
import json
import re
import sys
from pathlib import Path

NAMED_COLORS = {"white": (1, 1, 1), "black": (0, 0, 0),
                "red": (1, 0, 0), "gray": (0.5, 0.5, 0.5),
                "grey": (0.5, 0.5, 0.5)}


def load_pymupdf():
    try:
        import pymupdf
        return pymupdf
    except ImportError:
        try:
            import fitz as pymupdf
            return pymupdf
        except ImportError:
            raise SystemExit("缺少 PyMuPDF，无法脱敏：python scripts/bootstrap.py install --pdf")


def parse_color(text):
    text = (text or "black").strip().lower()
    if text in NAMED_COLORS:
        return NAMED_COLORS[text]
    if text.startswith("#") and len(text) == 7:
        return tuple(int(text[i:i + 2], 16) / 255.0 for i in (1, 3, 5))
    try:
        gray = float(text)
        if 0.0 <= gray <= 1.0:
            return (gray, gray, gray)
    except ValueError:
        pass
    raise SystemExit("无法识别的 --fill 取值：%s（用 white/black/gray/#RRGGBB/0-1）" % text)


def parse_pages(spec, total):
    if not spec:
        return set(range(1, total + 1))
    wanted = set()
    for chunk in str(spec).split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" in chunk:
            lo, hi = chunk.split("-", 1)
            wanted.update(range(int(lo), int(hi) + 1))
        else:
            wanted.add(int(chunk))
    bad = [p for p in wanted if p < 1 or p > total]
    if bad:
        raise SystemExit("页码超出范围：%s（共 %d 页）" % (bad, total))
    return wanted


def literal_hits(page, terms):
    hits = []
    for term in terms:
        rects = page.search_for(term)
        hits.extend((term, rect) for rect in rects)
    return hits


def pattern_hits(page, pattern):
    """Match spans, not words: a span is one run of uniform styling."""
    hits, samples = [], []
    data = page.get_text("dict")
    for block in data.get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = span.get("text", "")
                if text and pattern.search(text):
                    hits.append((text.strip()[:80], load_pymupdf().Rect(span["bbox"])))
                    samples.append(text.strip()[:80])
    return hits, samples


def main():
    p = argparse.ArgumentParser(description="Redact text in a PDF")
    p.add_argument("input")
    p.add_argument("-o", "--output", required=True)
    p.add_argument("-p", "--password")
    p.add_argument("--text", action="append", default=[],
                   help="字面量关键词，可重复或用逗号分隔")
    p.add_argument("--text-file", help="每行一个关键词的文件")
    p.add_argument("--pattern", help="正则表达式（按文本 span 命中，整段涂抹）")
    p.add_argument("--pages", help="1-based 页码范围，如 2-4,7，默认全部")
    p.add_argument("--fill", default="black",
                   help="涂抹底色 white/black/gray/#RRGGBB/0-1，默认 black")
    p.add_argument("--remove-images", action="store_true",
                   help="被涂抹区域覆盖到的图片一并删除")
    p.add_argument("--dry-run", action="store_true")
    ns = p.parse_args()

    terms = []
    for chunk in ns.text:
        terms.extend([t.strip() for t in chunk.split(",") if t.strip()])
    if ns.text_file:
        content = Path(ns.text_file).read_text(encoding="utf-8")
        terms.extend([line.strip() for line in content.splitlines() if line.strip()])
    pattern = None
    if ns.pattern:
        try:
            pattern = re.compile(ns.pattern)
        except re.error as exc:
            raise SystemExit("正则无效：%s" % exc)
    if not terms and pattern is None:
        raise SystemExit("至少给一个 --text / --text-file / --pattern")

    source = Path(ns.input).resolve()
    target = Path(ns.output).resolve()
    if source == target:
        raise SystemExit("输出不能覆盖输入：%s" % target)
    if not source.is_file():
        raise SystemExit("输入不存在：%s" % source)

    pymupdf = load_pymupdf()
    color = parse_color(ns.fill)
    doc = pymupdf.open(str(source))
    if doc.needs_pass and not (ns.password and doc.authenticate(ns.password)):
        raise SystemExit("PDF 已加密，需要正确的 --password")

    wanted = parse_pages(ns.pages, doc.page_count)
    report, total_hits, empty_pages = [], 0, []
    for index, page in enumerate(doc, start=1):
        if index not in wanted:
            continue
        hits = []
        if terms:
            hits.extend(literal_hits(page, terms))
        samples = []
        if pattern is not None:
            regex_hits, samples = pattern_hits(page, pattern)
            hits.extend(regex_hits)
        if not page.get_text().strip():
            empty_pages.append(index)
        if not hits:
            continue
        for _label, rect in hits:
            page.add_redact_annot(rect, fill=color)
        total_hits += len(hits)
        report.append({"page": index, "hits": len(hits),
                       "match_labels": sorted({label for label, _ in hits})[:12]})
        if not ns.dry_run:
            try:
                page.apply_redactions(
                    images=1 if ns.remove_images else 2)
            except TypeError:
                page.apply_redactions()

    warnings = []
    if empty_pages:
        warnings.append("以下页面没有文字层（扫描件？），字面量/正则都命中不了：%s"
                        % ",".join(str(p) for p in sorted(empty_pages)))
    if total_hits == 0:
        warnings.append("没有命中任何内容；先确认关键词大小写与全半角，或该页是扫描件")
    if ns.dry_run:
        doc.close()
        print(json.dumps({"input": str(source), "pages_checked": len(wanted),
                          "hits": total_hits, "detail": report,
                          "warnings": warnings, "dry_run": True},
                         ensure_ascii=False))
        return 0

    target.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(target), garbage=4, deflate=True)
    pages_total = doc.page_count
    doc.close()
    print(json.dumps({"output": str(target), "pages": pages_total,
                      "pages_checked": len(wanted), "hits": total_hits,
                      "detail": report, "fill": ns.fill,
                      "warnings": warnings}, ensure_ascii=False))
    return 0 if total_hits else 3


if __name__ == "__main__":
    sys.exit(main())
