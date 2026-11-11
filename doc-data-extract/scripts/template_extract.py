#!/usr/bin/env python3
"""template-extract: template-driven extraction for fixed-layout documents.

Template JSON shapes accepted:

  {"fields": [{"name": "contract_no", "patterns": ["合同编号[:：]\\s*(\\S+)"],
               "required": true},
              {"name": "party_a", "label": "甲方"},
              {"name": "amount", "between": ["合同总金额", "元"]}]}

  {"fields": {"contract_no": "合同编号[:：]\\s*(\\S+)"}}
  {"fields": ["甲方", "乙方", "合同编号"]}

Field keys: name / patterns|regex / label / between / required / multiple.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ingest  # noqa: E402

TRIM = " \t\r\n:："
# A label value on a form line usually stops at a gap or the next field cue.
LABEL_STOP = re.compile(r"\s{2,}|(?:联系电话|联系方式|电话|手机|邮箱|传真|"
                        r"地址|开户行|账号|日期)[：:]")


def trim_label(value):
    m = LABEL_STOP.search(value)
    return (value[:m.start()] if m else value).strip().strip(TRIM)


def normalize_template(raw):
    """Coerce every accepted template shape into a list of field dicts."""
    fields = raw.get("fields") if isinstance(raw, dict) else raw
    if fields is None:
        raise SystemExit("template has no `fields`")
    if isinstance(fields, dict):
        return [{"name": k, "patterns": [v]} for k, v in fields.items()]
    if isinstance(fields, list):
        out = []
        for item in fields:
            if isinstance(item, str):
                out.append({"name": item, "label": item})
            elif isinstance(item, dict) and item.get("name"):
                out.append(item)
            else:
                raise SystemExit("bad field entry: %r" % (item,))
        return out
    raise SystemExit("`fields` must be a list or an object")


def compile_field(field):
    patterns = []
    if field.get("patterns"):
        patterns.extend(field["patterns"])
    if field.get("regex"):
        patterns.append(field["regex"])
    if field.get("label"):
        patterns.append(r"%s\s*[：:]\s*([^\n，,；;]{1,80})"
                        % re.escape(str(field["label"])))
    if field.get("between"):
        start, end = field["between"]
        patterns.append(r"%s([\s\S]{1,120}?)%s"
                        % (re.escape(start), re.escape(end)))
    if not patterns:
        raise SystemExit("field %r has no patterns/label/between"
                         % field.get("name"))
    return [re.compile(p) for p in patterns]


def extract_field(field, compiled, pages, multiple):
    values, pages_hit = [], []
    for page in pages:
        text = page["text"]
        for pattern in compiled:
            for m in pattern.finditer(text):
                value = (m.group(1) if m.lastindex else m.group(0))
                value = (value or "").strip().strip(TRIM)
                if field.get("label"):
                    value = trim_label(value)
                if not value:
                    continue
                values.append(value)
                pages_hit.append(page["page"])
                if not multiple:
                    return values, pages_hit
    return values, pages_hit


def run(path, template_path):
    res = ingest.extract(path)
    raw = json.loads(Path(template_path).read_text(encoding="utf-8"))
    fields = normalize_template(raw)
    result, missing = {}, []
    for field in fields:
        name = field["name"]
        multiple = bool(field.get("multiple"))
        compiled = compile_field(field)
        values, pages_hit = extract_field(field, compiled, res["pages"],
                                          multiple)
        value = values[0] if values else None
        entry = {"value": value, "found": bool(values),
                 "page": pages_hit[0] if pages_hit else None,
                 "count": len(values)}
        if multiple:
            entry["all"] = values
        if field.get("required") and not values:
            entry["required"] = True
            missing.append(name)
        result[name] = entry

    required_total = sum(1 for f in fields if f.get("required"))
    found_total = sum(1 for e in result.values() if e["found"])
    return {
        "file": str(Path(path).resolve()),
        "template": str(Path(template_path).resolve()),
        "template_id": raw.get("id") if isinstance(raw, dict) else None,
        "fields": result,
        "found": found_total,
        "missing_required": missing,
        "coverage": round(found_total / len(fields), 3) if fields else 0.0,
        "required_coverage": (round((required_total - len(missing)) /
                                    required_total, 3)
                              if required_total else None),
        "warnings": res["warnings"],
    }


def main():
    p = argparse.ArgumentParser(description="Template-driven extraction")
    p.add_argument("input")
    p.add_argument("-o", "--output", required=True)
    p.add_argument("--template", required=True)
    p.add_argument("--strict", action="store_true",
                   help="exit 2 when a required field is missing")
    ns = p.parse_args()
    doc = run(ns.input, ns.template)
    out = Path(ns.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    print(json.dumps({"output": str(out), "found": doc["found"],
                      "coverage": doc["coverage"],
                      "missing_required": doc["missing_required"],
                      "warnings": doc["warnings"]}, ensure_ascii=False))
    if ns.strict and doc["missing_required"]:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
