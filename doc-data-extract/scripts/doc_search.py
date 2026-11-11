#!/usr/bin/env python3
"""doc-search: build a lightweight index and search across documents."""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ingest  # noqa: E402


def main():
    p = argparse.ArgumentParser(description="Cross-document search")
    p.add_argument("query")
    p.add_argument("--inputs", nargs="+", required=True)
    p.add_argument("-o", "--output", required=True)
    p.add_argument("--regex", action="store_true")
    p.add_argument("--context", type=int, default=60)
    p.add_argument("--max", type=int, default=50)
    ns = p.parse_args()
    pattern = (re.compile(ns.query, re.IGNORECASE) if ns.regex
               else re.compile(re.escape(ns.query), re.IGNORECASE))
    hits = []
    for path in ns.inputs:
        res = ingest.extract(path)
        for pg in res["pages"]:
            text = pg["text"]
            for m in pattern.finditer(text):
                lo = max(0, m.start() - ns.context)
                hi = min(len(text), m.end() + ns.context)
                snippet = re.sub(r"\s+", " ", text[lo:hi]).strip()
                hits.append({"file": Path(path).name, "page": pg["page"],
                             "match": m.group(0), "snippet": snippet})
                if len(hits) >= ns.max:
                    break
            if len(hits) >= ns.max:
                break
        if len(hits) >= ns.max:
            break
    out = Path(ns.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"query": ns.query, "count": len(hits),
                               "hits": hits}, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    print(json.dumps({"output": str(out), "query": ns.query,
                      "count": len(hits)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
