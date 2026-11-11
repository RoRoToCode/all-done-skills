#!/usr/bin/env python3
"""batch-extract: run field extraction across many documents and consolidate."""
import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ingest  # noqa: E402
from extract_fields import run_fields  # noqa: E402


def main():
    p = argparse.ArgumentParser(description="Batch field extraction")
    p.add_argument("--inputs", nargs="+", required=True)
    p.add_argument("-o", "--output", required=True)
    p.add_argument("--preset", default="general",
                   choices=["general", "contract", "finance", "invoice"])
    ns = p.parse_args()
    outdir = Path(ns.output)
    outdir.mkdir(parents=True, exist_ok=True)
    rows, summary = [], []
    for path in ns.inputs:
        res = ingest.extract(path)
        results, by_field = run_fields(res["text"], ns.preset)
        summary.append({"file": str(Path(path).resolve()), "count": len(results),
                        "by_field": by_field, "warnings": res["warnings"]})
        for r in results:
            rows.append({"file": Path(path).name, "field": r["field"],
                         "value": r["value"], "context": r["context"]})

    csv_path = outdir / "fields.csv"
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=["file", "field", "value", "context"])
        w.writeheader()
        w.writerows(rows)
    json_path = outdir / "fields.json"
    json_path.write_text(json.dumps({"preset": ns.preset, "total": len(rows),
                                     "files": summary, "rows": rows},
                                    ensure_ascii=False, indent=2),
                         encoding="utf-8")
    print(json.dumps({"output": str(outdir), "preset": ns.preset,
                      "total": len(rows), "files": len(summary)},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
