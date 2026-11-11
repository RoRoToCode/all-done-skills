#!/usr/bin/env python3
"""doc-to-text: extract a document's text into a Markdown/plain file."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ingest  # noqa: E402


def main():
    p = argparse.ArgumentParser(description="Document to text")
    p.add_argument("input")
    p.add_argument("-o", "--output", required=True)
    ns = p.parse_args()
    res = ingest.extract(ns.input)
    out = Path(ns.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(res["text"], encoding="utf-8")
    print(json.dumps({"output": str(out), "format": res["format"],
                      "chars": len(res["text"]), "warnings": res["warnings"]},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
