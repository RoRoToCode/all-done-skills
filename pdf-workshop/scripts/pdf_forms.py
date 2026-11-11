#!/usr/bin/env python3
"""Inspect and fill AcroForm fields in a PDF.

  list  dump every field with its type, current value and allowed states
  fill  write values into the form and keep it editable (no flattening)

Checkbox and radio values are export states, not booleans: pass true/false and
the script picks the non-Off state itself, or pass the literal state name
(e.g. /Yes) when the form is unusual.

Scanned PDFs have no fields — if `list` comes back empty that is the reason,
not a bug. Run `pdf-ocr` first only if you need text, not fields.
"""

import argparse
import json
import sys
from pathlib import Path

try:
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import NameObject
except ImportError:
    raise SystemExit("缺少 pypdf：python scripts/bootstrap.py install")


def open_reader(path, password=None):
    reader = PdfReader(str(path))
    if reader.is_encrypted and not (password and reader.decrypt(password)):
        raise SystemExit("PDF 已加密，需要正确的 --password")
    return reader


def describe_field(name, spec):
    kind = str(spec.get("/FT") or "")
    states = spec.get("_States_") or []
    return {
        "name": name,
        "type": {"/Tx": "text", "/Btn": "button", "/Ch": "choice",
                 "/Sig": "signature"}.get(kind, kind or "unknown"),
        "value": str(spec.get("/V")) if spec.get("/V") is not None else None,
        "default": str(spec.get("/DV")) if spec.get("/DV") is not None else None,
        "states": [str(s) for s in states],
        "flags": int(spec.get("/Ff") or 0),
    }


def collect_fields(reader):
    raw = reader.get_fields() or {}
    return [describe_field(name, spec) for name, spec in raw.items()]


def parse_pairs(text):
    """'a=1;b=2' or a JSON object string."""
    text = text.strip()
    if text.startswith("{"):
        data = json.loads(text)
    else:
        data = {}
        for chunk in text.split(";"):
            if not chunk.strip():
                continue
            if "=" not in chunk:
                raise SystemExit("--data 需要 key=value 形式：%r" % chunk)
            key, value = chunk.split("=", 1)
            data[key.strip()] = value.strip()
    if not isinstance(data, dict):
        raise SystemExit("--data 必须是 JSON 对象或 key=value;key=value")
    return {str(k): str(v) for k, v in data.items()}


def load_fields(ns):
    if ns.fields:
        raw = Path(ns.fields)
        text = raw.read_text(encoding="utf-8") if raw.is_file() else ns.fields
        return parse_pairs(text)
    if ns.data:
        return parse_pairs(ns.data)
    raise SystemExit("fill 需要 --fields <JSON 文件/JSON 字符串> 或 --data k=v;k2=v2")


def normalise(field_map, values):
    """Translate true/false into the on-state that the file actually declares."""
    by_name = {f["name"]: f for f in field_map}
    cleaned, unknown = {}, []
    for key, value in values.items():
        spec = by_name.get(key)
        if spec is None:
            unknown.append(key)
            cleaned[key] = value
            continue
        if spec["type"] == "button":
            states = [s for s in spec["states"] if s not in ("/Off",)]
            lowered = value.strip().lower()
            if lowered in ("true", "yes", "on", "1"):
                cleaned[key] = states[0] if states else "/Yes"
            elif lowered in ("false", "no", "off", "0", ""):
                cleaned[key] = "/Off"
            else:
                cleaned[key] = value if value.startswith("/") else "/" + value
        else:
            cleaned[key] = value
    return cleaned, unknown


def cmd_list(ns):
    reader = open_reader(ns.input, ns.password)
    fields = collect_fields(reader)
    payload = {"input": str(Path(ns.input).resolve()), "pages": len(reader.pages),
               "field_count": len(fields), "fields": fields}
    if len(fields) == 0:
        payload["warnings"] = ["没有找到表单字段；扫描件或普通 PDF 本来就没有表单"]
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if ns.output:
        target = Path(ns.output).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        print(json.dumps({"output": str(target), "field_count": len(fields)},
                         ensure_ascii=False))
    else:
        print(text)
    return 0


def cmd_fill(ns):
    reader = open_reader(ns.input, ns.password)
    fields = collect_fields(reader)
    if not fields:
        raise SystemExit("该 PDF 没有表单字段，无法填写（扫描件请先做别的处理）")
    values, unknown = normalise(fields, load_fields(ns))

    writer = PdfWriter()
    writer.append(reader)
    for page in writer.pages:
        writer.update_page_form_field_values(page, values, auto_regenerate=False)
    try:
        writer.set_need_appearances_writer(True)
    except Exception:  # noqa: BLE001 - older pypdf
        pass

    target = Path(ns.output).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("wb") as handle:
        writer.write(handle)

    filled = [k for k in values if k not in unknown]
    print(json.dumps({"output": str(target), "pages": len(reader.pages),
                      "fields_total": len(fields), "filled": filled,
                      "unknown_fields": unknown,
                      "flattened": False,
                      "warnings": (["这些字段名不存在，已按原样写入：" + ", ".join(unknown)]
                                   if unknown else [])}, ensure_ascii=False))
    return 0


def main():
    p = argparse.ArgumentParser(description="PDF form fields: list / fill")
    sub = p.add_subparsers(dest="action", required=True)
    l = sub.add_parser("list")
    l.add_argument("input")
    l.add_argument("-o", "--output")
    l.add_argument("-p", "--password")
    f = sub.add_parser("fill")
    f.add_argument("input")
    f.add_argument("-o", "--output", required=True)
    f.add_argument("-p", "--password")
    f.add_argument("--fields", help="JSON file, or inline JSON object")
    f.add_argument("--data", help="key=value;key2=value2")
    ns = p.parse_args()
    return cmd_list(ns) if ns.action == "list" else cmd_fill(ns)


if __name__ == "__main__":
    sys.exit(main())
