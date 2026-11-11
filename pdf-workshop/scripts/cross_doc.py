#!/usr/bin/env python3
"""Cross-document search, change comparison and field extraction for PDF sets.

Text comes from the official workbuddy-pdf CLI (-f md); every hit keeps its
source file and 1-based page number so conclusions stay traceable.
"""

import argparse
import difflib
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wb_pdf  # noqa: E402

PAGE_MARK = re.compile(r"<!--\s*page\s+(\d+)\s*-->", re.IGNORECASE)
ALT_MARK = re.compile(r"^\s*(?:#\s*)?(?:page|第)\s*(\d+)\s*(?:页)?\s*$",
                      re.IGNORECASE | re.MULTILINE)

FIELD_PATTERNS = {
    "general": {
        "date": r"(?:20\d{2}[-/年]\d{1,2}[-/月]\d{1,2}日?)",
        "money": r"(?:[¥￥$]\s?\d[\d,]*(?:\.\d+)?\s?(?:万元|亿元|元)?|\d[\d,]*(?:\.\d+)?\s?(?:万元|亿元|元))",
        "percent": r"[+-]?\d+(?:\.\d+)?\s?%",
        "email": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        "url": r"https?://[^\s)）]+",
        "phone": r"(?<!\d)1[3-9]\d{9}(?!\d)",
    },
    "contract": {
        "party_a": r"甲方[（(]?[^：:\n]{0,20}[）)]?[：:]\s*([^\n，,；;]{2,40})",
        "party_b": r"乙方[（(]?[^：:\n]{0,20}[）)]?[：:]\s*([^\n，,；;]{2,40})",
        "amount": r"(?:合同(?:总)?金额|价款|总价)[^\n]{0,20}?([¥￥]?\s?\d[\d,]*(?:\.\d+)?\s?(?:万元|亿元|元)?)",
        "sign_date": r"(?:签署|签订|签约)日期[：:\s]*([^\n，,；;]{4,20})",
        "effective_date": r"(?:生效|起始)日期[：:\s]*([^\n，,；;]{4,20})",
        "penalty": r"(?:违约金|滞纳金)[^\n]{0,30}",
    },
    "finance": {
        "revenue": r"(?:营业收入|营收|销售额)[^\n]{0,20}?(\d[\d,]*(?:\.\d+)?\s?(?:万元|亿元|元)?)",
        "net_profit": r"(?:净利润|归母净利润)[^\n]{0,20}?(\d[\d,]*(?:\.\d+)?\s?(?:万元|亿元|元)?)",
        "total_assets": r"(?:总资产|资产总额)[^\n]{0,20}?(\d[\d,]*(?:\.\d+)?\s?(?:万元|亿元|元)?)",
        "yoy": r"(?:同比|YoY)[^\n]{0,12}?([+-]?\d+(?:\.\d+)?\s?%)",
    },
}


def expand_inputs(items, pattern="*.pdf"):
    files = []
    for item in items:
        path = Path(item)
        if path.is_dir():
            files.extend(sorted(path.glob(pattern)))
        elif any(c in item for c in "*?[]"):
            files.extend(sorted(Path().glob(item)))
        elif path.exists():
            files.append(path)
    return [f for f in files if f.suffix.lower() == ".pdf"]


def split_pages(md_text):
    marks = list(PAGE_MARK.finditer(md_text))
    if not marks:
        marks = list(ALT_MARK.finditer(md_text))
    if not marks:
        return [{"page": 1, "text": md_text.strip()}], ["未检测到页码标记，整篇记为第 1 页"]
    pages = []
    for index, mark in enumerate(marks):
        start = mark.end()
        end = marks[index + 1].start() if index + 1 < len(marks) else len(md_text)
        pages.append({"page": int(mark.group(1)), "text": md_text[start:end].strip()})
    return pages, []


def cmd_index(args):
    files = expand_inputs(args.inputs, args.pattern)
    if not files:
        raise RuntimeError("没有找到匹配的 PDF 文件")
    workdir = Path(args.workdir).resolve()
    workdir.mkdir(parents=True, exist_ok=True)
    documents = []
    for source in files:
        md_path = workdir / (source.stem + ".md")
        code = wb_pdf.run_action(["read", str(source), "-o", str(md_path),
                                  "-f", args.format])
        if code != 0 or not md_path.exists():
            documents.append({"id": source.name, "path": str(source.resolve()),
                              "pages": [], "warnings": ["文本提取失败"]})
            continue
        pages, warnings = split_pages(md_path.read_text(encoding="utf-8", errors="replace"))
        documents.append({"id": source.name, "path": str(source.resolve()),
                          "pages": pages, "warnings": warnings})
    index = {"format": "pdf-workshop/index-v1", "documents": documents}
    out = Path(args.output).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"index": str(out), "documents": len(documents),
                      "pages": sum(len(d["pages"]) for d in documents)},
                     ensure_ascii=False))
    return 0


def load_index(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def cmd_search(args):
    index = load_index(args.index)
    pattern = (re.compile(args.query, re.IGNORECASE) if args.regex
               else re.compile(re.escape(args.query), re.IGNORECASE))
    hits = []
    for doc in index["documents"]:
        for page in doc["pages"]:
            text = page["text"]
            for match in pattern.finditer(text):
                lo = max(0, match.start() - args.context)
                hi = min(len(text), match.end() + args.context)
                snippet = re.sub(r"\s+", " ", text[lo:hi]).strip()
                hits.append({"file": doc["id"], "page": page["page"],
                             "match": match.group(0), "snippet": snippet})
                if len(hits) >= args.max:
                    break
            if len(hits) >= args.max:
                break
        if len(hits) >= args.max:
            break
    print(json.dumps({"query": args.query, "count": len(hits), "hits": hits},
                     ensure_ascii=False, indent=2))
    return 0


def _lines(doc):
    return [re.sub(r"\s+", " ", line).strip()
            for page in doc["pages"]
            for line in page["text"].splitlines()
            if len(line.strip()) > 8]


def cmd_compare(args):
    index = load_index(args.index)
    docs = index["documents"]
    comparisons = []
    for i in range(len(docs)):
        for j in range(i + 1, len(docs)):
            a, b = docs[i], docs[j]
            la, lb = _lines(a), _lines(b)
            matcher = difflib.SequenceMatcher(None, la, lb, autojunk=False)
            added, removed = [], []
            for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                if tag in ("insert", "replace"):
                    added.extend(lb[j1:j2])
                if tag in ("delete", "replace"):
                    removed.extend(la[i1:i2])
            sa, sb = set(la), set(lb)
            jaccard = len(sa & sb) / max(1, len(sa | sb))
            comparisons.append({
                "pair": [a["id"], b["id"]],
                "line_similarity": round(matcher.ratio(), 4),
                "content_overlap": round(jaccard, 4),
                "shared_lines": len(sa & sb),
                "only_in_first": removed[:args.top],
                "only_in_second": added[:args.top],
            })
    print(json.dumps({"pairs": comparisons}, ensure_ascii=False, indent=2))
    return 0


def cmd_fields(args):
    index = load_index(args.index)
    presets = ["general"] if args.preset == "general" else ["general", args.preset]
    patterns = {}
    for preset in presets:
        patterns.update(FIELD_PATTERNS[preset])
    results = []
    for doc in index["documents"]:
        for page in doc["pages"]:
            for name, pattern in patterns.items():
                for match in re.finditer(pattern, page["text"]):
                    value = match.group(1) if match.lastindex else match.group(0)
                    lo = max(0, match.start() - 20)
                    hi = min(len(page["text"]), match.end() + 20)
                    results.append({
                        "file": doc["id"], "page": page["page"],
                        "field": name, "value": value.strip(),
                        "context": re.sub(r"\s+", " ", page["text"][lo:hi]).strip(),
                    })
    summary = Counter(r["field"] for r in results)
    print(json.dumps({"preset": args.preset, "count": len(results),
                      "by_field": dict(summary), "results": results[:args.max]},
                     ensure_ascii=False, indent=2))
    return 0


def build_parser():
    p = argparse.ArgumentParser(description="Cross-document PDF analysis")
    sub = p.add_subparsers(dest="action", required=True)

    i = sub.add_parser("index", help="extract text from many PDFs into an index")
    i.add_argument("inputs", nargs="+")
    i.add_argument("-o", "--output", required=True)
    i.add_argument("--pattern", default="*.pdf")
    i.add_argument("--format", default="md", choices=["md", "md-plain", "txt"])
    i.add_argument("--workdir", default=".pdf-workshop/index")

    s = sub.add_parser("search", help="search across documents with page refs")
    s.add_argument("query")
    s.add_argument("-i", "--index", required=True)
    s.add_argument("--regex", action="store_true")
    s.add_argument("--context", type=int, default=60)
    s.add_argument("--max", type=int, default=50)

    c = sub.add_parser("compare", help="pairwise line-level difference")
    c.add_argument("-i", "--index", required=True)
    c.add_argument("--top", type=int, default=15)

    f = sub.add_parser("fields", help="extract dates, amounts, parties, ratios")
    f.add_argument("-i", "--index", required=True)
    f.add_argument("--preset", default="general",
                   choices=["general", "contract", "finance"])
    f.add_argument("--max", type=int, default=200)
    return p


def main():
    args = build_parser().parse_args()
    handlers = {"index": cmd_index, "search": cmd_search,
                "compare": cmd_compare, "fields": cmd_fields}
    try:
        return handlers[args.action](args)
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)},
                         ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
