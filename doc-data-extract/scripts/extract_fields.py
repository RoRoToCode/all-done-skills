#!/usr/bin/env python3
"""extract-fields: regex-based structured field extraction with presets.

Presets: general / contract / finance / invoice. Reused by batch_extract.
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ingest  # noqa: E402

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
    "invoice": {
        "invoice_no": r"(?:发票号码|发票号)[：:\s]*([0-9A-Za-z\-]{6,30})",
        "amount": r"(?:价税合计|金额|合计)[^\n]{0,20}?([¥￥]?\s?\d[\d,]*(?:\.\d+)?\s?(?:元)?)",
        "seller": r"(?:销售方|开票方|售方)[（(]?[^：:\n]{0,20}[）)]?[：:]\s*([^\n，,；;]{2,40})",
        "buyer": r"(?:购买方|购方)[（(]?[^：:\n]{0,20}[）)]?[：:]\s*([^\n，,；;]{2,40})",
        "tax_no": r"(?:纳税人识别号|税号)[：:\s]*([0-9A-Za-z]{15,20})",
    },
}


def run_fields(text, preset="general", max_hits=200):
    presets = ["general"] if preset == "general" else ["general", preset]
    patterns = {}
    for pr in presets:
        patterns.update(FIELD_PATTERNS[pr])
    results = []
    for name, pattern in patterns.items():
        for match in re.finditer(pattern, text):
            value = match.group(1) if match.lastindex else match.group(0)
            lo = max(0, match.start() - 20)
            hi = min(len(text), match.end() + 20)
            results.append({
                "field": name,
                "value": value.strip(),
                "context": re.sub(r"\s+", " ", text[lo:hi]).strip(),
            })
    return results[:max_hits], dict(Counter(r["field"] for r in results))


def main():
    p = argparse.ArgumentParser(description="Extract structured fields")
    p.add_argument("input")
    p.add_argument("-o", "--output", required=True)
    p.add_argument("--preset", default="general",
                   choices=list(FIELD_PATTERNS.keys()))
    p.add_argument("--max", type=int, default=200)
    ns = p.parse_args()
    res = ingest.extract(ns.input)
    results, by_field = run_fields(res["text"], ns.preset, ns.max)
    out = Path(ns.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"file": str(Path(ns.input).resolve()),
                               "preset": ns.preset, "count": len(results),
                               "by_field": by_field, "results": results,
                               "warnings": res["warnings"]},
                              ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(out), "preset": ns.preset,
                      "count": len(results), "by_field": by_field,
                      "warnings": res["warnings"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
