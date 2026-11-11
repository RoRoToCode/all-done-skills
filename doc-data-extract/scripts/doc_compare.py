#!/usr/bin/env python3
"""doc-compare: pairwise line-level similarity between documents."""
import argparse
import difflib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ingest  # noqa: E402


def _lines(res):
    return [re.sub(r"\s+", " ", ln).strip()
            for pg in res["pages"]
            for ln in pg["text"].splitlines()
            if len(ln.strip()) > 8]


def main():
    p = argparse.ArgumentParser(description="Compare documents")
    p.add_argument("--inputs", nargs="+", required=True)
    p.add_argument("-o", "--output", required=True)
    p.add_argument("--top", type=int, default=15)
    ns = p.parse_args()
    docs = [(Path(x).name, _lines(ingest.extract(x))) for x in ns.inputs]
    comparisons = []
    for i in range(len(docs)):
        for j in range(i + 1, len(docs)):
            a, b = docs[i], docs[j]
            la, lb = a[1], b[1]
            matcher = difflib.SequenceMatcher(None, la, lb, autojunk=False)
            added, removed = [], []
            for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                if tag in ("insert", "replace"):
                    added.extend(lb[j1:j2])
                if tag in ("delete", "replace"):
                    removed.extend(la[i1:i2])
            sa, sb = set(la), set(lb)
            jac = len(sa & sb) / max(1, len(sa | sb))
            comparisons.append({
                "pair": [a[0], b[0]],
                "line_similarity": round(matcher.ratio(), 4),
                "content_overlap": round(jac, 4),
                "shared_lines": len(sa & sb),
                "only_in_first": removed[:ns.top],
                "only_in_second": added[:ns.top],
            })
    out = Path(ns.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"pairs": comparisons}, ensure_ascii=False,
                              indent=2), encoding="utf-8")
    print(json.dumps({"output": str(out), "pairs": len(comparisons)},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
