#!/usr/bin/env python3
"""extract-entities: rule + lexicon entity extraction with page citations.

Types: date / money / percent / email / phone / id_card / uscc / bank_account /
url / org / person / address / custom(--dict).

All hits are candidates: rule-based matching cannot guarantee correctness,
so every entity carries its page and a short context for review.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ingest  # noqa: E402

ORG_SUFFIX = (r"(?:有限责任公司|股份有限公司|有限公司|集团公司|集团|公司|"
              r"银行|支行|分行|信用社|医院|大学|学院|研究院|研究所|"
              r"事务所|会计师事务所|律师事务所|中心|工厂|厂|商店|合作社)")
ORG_TAIL = re.compile(r"[\u4e00-\u9fa5A-Za-z0-9（）()·]{2,40}?" + ORG_SUFFIX)

PATTERNS = {
    "date": r"(?:20\d{2}\s*[-/年]\s*\d{1,2}\s*[-/月]\s*\d{1,2}\s*日?"
            r"|\d{4}-\d{1,2}-\d{1,2})",
    "money": r"(?:[¥￥$]\s?\d[\d,]*(?:\.\d+)?\s?(?:万元|亿元|元)?"
             r"|\d[\d,]*(?:\.\d+)?\s?(?:万元|亿元|元))",
    "percent": r"[+-]?\d+(?:\.\d+)?\s?%",
    "email": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    "phone": r"(?<!\d)(?:1[3-9]\d{9}|0\d{2,3}-?\d{7,8})(?!\d)",
    "id_card": r"(?<!\d)\d{17}[\dXx](?!\d)",
    "uscc": r"(?<![0-9A-Z])[0-9A-HJ-NPQRTUWXY]{18}(?![0-9A-Z])",
    "bank_account": r"(?<!\d)\d{16,19}(?!\d)",
    "url": r"https?://[^\s)）\]】,，]+",
    "org": ORG_TAIL.pattern,
    "person": (r"(?:法定代表人|法人代表|委托代理人|联系人|经办人|负责人|"
               r"签约代表|姓名)[：:\s]{0,3}([\u4e00-\u9fa5]{2,4})"
               r"|([\u4e00-\u9fa5]{2,3})(?:先生|女士|经理|总监|律师)"),
    "address": (r"[\u4e00-\u9fa5]{2,10}(?:省|自治区|特别行政区)"
                r"[\u4e00-\u9fa5]{0,10}(?:市|自治州)"
                r"[\u4e00-\u9fa5]{0,20}(?:区|县|市)?"
                r"[\u4e00-\u9fa5A-Za-z\d]{0,30}?(?:路|街|大道|巷|弄)"
                r"[\u4e00-\u9fa5A-Za-z\d]{0,10}号?"),
}

# Higher priority wins when two types claim overlapping spans.
PRIORITY = ["id_card", "uscc", "email", "url", "phone", "bank_account",
            "date", "percent", "money", "address", "person", "org"]
PRIORITY_RANK = {name: i for i, name in enumerate(PRIORITY)}

CUE_PREFIX = re.compile(r"^(?:甲方|乙方|丙方|买方|卖方|供方|需方|"
                        r"销售方|购买方|开票方|收款方|付款方)[：:\s]*")


def load_dict(path):
    """Lexicon files: one `text` or `text,type` per line; # lines ignored."""
    entries = []
    if not path:
        return entries
    for raw in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "," in line:
            text, _, typ = line.partition(",")
            entries.append((text.strip(), typ.strip() or "custom"))
        else:
            entries.append((line, "custom"))
    return entries


def _clean_org(value):
    value = CUE_PREFIX.sub("", value).strip()
    return value.strip("：: 　")


def collect(text, extra=None):
    hits = []
    for name, pattern in PATTERNS.items():
        for m in re.finditer(pattern, text):
            value = m.group(0)
            if name == "person":
                value = m.group(1) or m.group(2) or ""
            if not value:
                continue
            if name == "person":
                # A cue-captured name must not swallow common non-name words.
                if value in ("本人", "双方", "各方", "甲方", "乙方", "公司"):
                    continue
            if name == "org":
                value = _clean_org(value)
                if len(value) < 4:
                    continue
            hits.append({"type": name, "value": value.strip(),
                         "start": m.start(), "end": m.end()})
    for value, typ in (extra or []):
        for m in re.finditer(re.escape(value), text):
            hits.append({"type": typ, "value": value,
                         "start": m.start(), "end": m.end()})
    return hits


def resolve(hits):
    """Drop overlaps, keeping the highest-priority, longest match."""
    ordered = sorted(hits, key=lambda h: (PRIORITY_RANK.get(h["type"], 99),
                                          -(h["end"] - h["start"])))
    kept = []
    for hit in ordered:
        clash = False
        for other in kept:
            if hit["start"] < other["end"] and other["start"] < hit["end"]:
                clash = True
                break
        if not clash:
            kept.append(hit)
    return kept


def run(path, dict_path=None, types=None):
    res = ingest.extract(path)
    extra = load_dict(dict_path)
    entities = {}
    for page in res["pages"]:
        text = page["text"]
        for hit in resolve(collect(text, extra)):
            if types and hit["type"] not in types:
                continue
            key = (hit["type"], hit["value"])
            lo = max(0, hit["start"] - 24)
            hi = min(len(text), hit["end"] + 24)
            context = re.sub(r"\s+", " ", text[lo:hi]).strip()
            if key in entities:
                entities[key]["count"] += 1
                continue
            entities[key] = {"type": hit["type"], "value": hit["value"],
                             "page": page["page"], "count": 1,
                             "context": context}
    items = sorted(entities.values(),
                   key=lambda e: (PRIORITY_RANK.get(e["type"], 99),
                                  e["page"], -e["count"]))
    by_type = {}
    for item in items:
        by_type.setdefault(item["type"], 0)
        by_type[item["type"]] += 1
    return {"file": str(Path(path).resolve()), "format": res["format"],
            "count": len(items), "by_type": by_type, "entities": items,
            "warnings": res["warnings"]}


def write_csv(path, items):
    import csv
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=["type", "value", "page",
                                                "count", "context"])
        writer.writeheader()
        for item in items:
            writer.writerow({k: item[k] for k in writer.fieldnames})


def main():
    p = argparse.ArgumentParser(description="Entity extraction")
    p.add_argument("input")
    p.add_argument("-o", "--output", required=True)
    p.add_argument("--dict", dest="dict_path", help="custom lexicon file")
    p.add_argument("--types", help="comma separated type filter, e.g. org,person")
    p.add_argument("--csv", help="also write a CSV table here")
    ns = p.parse_args()
    types = [t.strip() for t in ns.types.split(",")] if ns.types else None
    doc = run(ns.input, ns.dict_path, types)
    out = Path(ns.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    result = {"output": str(out), "count": doc["count"],
              "by_type": doc["by_type"], "warnings": doc["warnings"]}
    if ns.csv:
        write_csv(ns.csv, doc["entities"])
        result["csv"] = str(Path(ns.csv).resolve())
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
