#!/usr/bin/env python3
"""extract-kv: pull key-value pairs out of forms, configs and invoices."""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ingest  # noqa: E402

# Matches:  键：值   键: 值   键=值   Key: Value   （同一行）
KV = re.compile(
    r"^\s*([\u4e00-\u9fffA-Za-z0-9_．.（）()\-\/]{1,30})"
    r"[\s]*[:：=][\s]*(.+?)\s*$")
# Loose fallback: key and value separated by two or more spaces/tabs.
KV_LOOSE = re.compile(
    r"^([\u4e00-\u9fffA-Za-z0-9_．.（）()\-\/]{1,30})"
    r"[\t ]{2,}(.+?)\s*$")


def run_kv(text):
    pairs = []
    seen = set()
    for line in text.splitlines():
        m = KV.match(line) or KV_LOOSE.match(line)
        if not m:
            continue
        key = m.group(1).strip().rstrip("：:=")
        value = m.group(2).strip()
        if not value or key in seen:
            continue
        seen.add(key)
        pairs.append({"key": key, "value": value})
    return pairs


def main():
    p = argparse.ArgumentParser(description="Extract key-value pairs")
    p.add_argument("input")
    p.add_argument("-o", "--output", required=True)
    ns = p.parse_args()
    res = ingest.extract(ns.input)
    pairs = run_kv(res["text"])
    out = Path(ns.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"file": str(Path(ns.input).resolve()),
                               "count": len(pairs), "pairs": pairs,
                               "warnings": res["warnings"]},
                              ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(out), "count": len(pairs),
                      "warnings": res["warnings"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
