# -*- coding: utf-8 -*-
"""数据全搞定 · 共享层：记录表模型、格式适配与 12 个动作的实现。

统一模型：list[dict]。所有格式只负责读写适配，变换动作都在模型上做。
零必需依赖：csv / json / xml.etree / tomllib(3.11+) 均为标准库；
YAML 装了 PyYAML 就走完整解析，没装则用内置的扁平子集（可复跑、可预测）。
"""
from __future__ import annotations

import csv
import io
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

try:
    import yaml as _yaml
except ImportError:
    _yaml = None
try:
    import tomllib as _toml
except ImportError:
    _toml = None

EXIT_USAGE = 2
EXIT_IO = 3
EXIT_FAIL = 5

FORMATS = ("csv", "tsv", "json", "ndjson", "xml", "yaml", "toml", "md")
EXT_FMT = {".csv": "csv", ".tsv": "tsv", ".json": "json", ".ndjson": "ndjson",
           ".jsonl": "ndjson", ".xml": "xml", ".yaml": "yaml", ".yml": "yaml",
           ".toml": "toml", ".md": "md", ".markdown": "md"}


def main_guard():
    """输出编码兜底：被管道/重定向捕获时统一按 UTF-8 写出，否则父进程按 UTF-8
    解码会得到一串替换符；直接接终端时不动编码，免得老式 cp936 控制台显示异常。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            if stream.isatty():
                stream.reconfigure(errors="replace")
            else:
                stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass


def fail(message, code=EXIT_USAGE):
    print(message, file=sys.stderr)
    raise SystemExit(code)


def emit(payload, code=0):
    print(json.dumps(payload, ensure_ascii=False))
    return code


def w(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))
    return path


def unique_path(path):
    path = Path(path)
    if not path.exists():
        return path
    for i in range(2, 10000):
        cand = path.with_name("%s-%d%s" % (path.stem, i, path.suffix))
        if not cand.exists():
            return cand
    fail("重名避让次数超限：%s" % path, EXIT_IO)


def read_text(path, encoding="utf-8"):
    p = Path(path)
    if not p.is_file():
        fail("输入不存在：%s" % p, EXIT_IO)
    raw = p.read_bytes()
    for codec in (encoding, "utf-8-sig", "gb18030"):
        try:
            return raw.decode(codec)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", "replace")


def guess_format(path, explicit=None):
    if explicit:
        fmt = explicit.lower().lstrip(".")
        if fmt not in FORMATS:
            fail("不支持的格式：%s（可用：%s）" % (fmt, ", ".join(FORMATS)), EXIT_USAGE)
        return fmt
    fmt = EXT_FMT.get(Path(path).suffix.lower())
    if not fmt:
        fail("无法从扩展名推断格式，请用 --from / --to 指定：%s" % path, EXIT_USAGE)
    return fmt


def scalar(v):
    """把任意值压成表格单元格字符串。"""
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False)
    return str(v)


def fields_of(records):
    out = []
    for row in records:
        for k in row:
            if k not in out:
                out.append(k)
    return out


def xml_name(k):
    name = re.sub(r"[^A-Za-z0-9_.\-]", "_", str(k))
    return name if name and not name[0].isdigit() else "f_" + name


def _mini_yaml_load(text):
    """内置 YAML 子集：'- k: v' 列表，或单个 'k: v' 映射。"""
    rows, cur = [], None
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        stripped = line.strip()
        if stripped.startswith("- "):
            if cur is not None:
                rows.append(cur)
            cur = {}
            stripped = stripped[2:].strip()
        elif line.startswith(("  ", "\t")) and cur is not None:
            stripped = stripped
        elif cur is None:
            cur = {}
        if ":" in stripped:
            k, v = stripped.split(":", 1)
            cur[k.strip()] = _mini_scalar(v.strip())
        elif stripped and cur is not None and not stripped.startswith("- "):
            cur.setdefault("value", _mini_scalar(stripped))
    if cur is not None:
        rows.append(cur)
    return rows


def _mini_scalar(v):
    if not v:
        return ""
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    if v.lower() in ("true", "false"):
        return v.lower() == "true"
    if v.lower() in ("null", "~"):
        return None
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    if re.fullmatch(r"-?\d+\.\d+", v):
        return float(v)
    return v


def _mini_toml_load(text):
    rows, cur = [], None
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s == "[[rows]]":
            if cur is not None:
                rows.append(cur)
            cur = {}
        elif cur is not None and "=" in s:
            k, v = s.split("=", 1)
            cur[k.strip().strip('"')] = _mini_scalar(v.strip())
    if cur is not None:
        rows.append(cur)
    return rows


def read_records(path, fmt, encoding="utf-8"):
    text = read_text(path, encoding)
    if fmt in ("csv", "tsv"):
        delimiter = "\t" if fmt == "tsv" else ","
        reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
        return [dict(r) for r in reader]
    if fmt == "json":
        data = json.loads(text)
        if isinstance(data, list):
            return [r if isinstance(r, dict) else {"value": r} for r in data]
        if isinstance(data, dict):
            for key in ("data", "rows", "records", "items"):
                if isinstance(data.get(key), list):
                    return [r if isinstance(r, dict) else {"value": r} for r in data[key]]
            return [data]
        return [{"value": data}]
    if fmt == "ndjson":
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    if fmt == "xml":
        root = ET.fromstring(text)
        if root.tag.lower() in ("row", "record", "item"):
            nodes = [root]
        else:
            nodes = list(root) or [root]
        rows = []
        for node in nodes:
            row = {child.tag: (child.text or "") for child in node}
            row.update({("%s" % k): v for k, v in node.attrib.items() if k not in row})
            rows.append(row or {"value": node.text or ""})
        return rows
    if fmt == "yaml":
        if _yaml is not None:
            data = _yaml.safe_load(text)
        else:
            data = _mini_yaml_load(text)
        if isinstance(data, dict):
            return [data]
        return [r if isinstance(r, dict) else {"value": r} for r in (data or [])]
    if fmt == "toml":
        if _toml is not None:
            data = _toml.loads(text)
        else:
            data = {"rows": _mini_toml_load(text)}
        rows = data.get("rows", data) if isinstance(data, dict) else data
        return [r if isinstance(r, dict) else {"value": r} for r in rows]
    fail("格式 %s 不支持读取（可先转成 CSV/JSON）" % fmt, EXIT_USAGE)


def _toml_value(v):
    if v is None:
        return None
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False)
    return json.dumps(scalar(v), ensure_ascii=False)


def write_records(records, path, fmt, encoding="utf-8"):
    path = Path(path)
    fields = fields_of(records)
    if fmt in ("csv", "tsv"):
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fields or ["value"],
                                delimiter="\t" if fmt == "tsv" else ",",
                                extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in records:
            writer.writerow({k: scalar(row.get(k, "")) for k in (fields or ["value"])})
        text = buf.getvalue()
    elif fmt == "json":
        text = json.dumps(records, ensure_ascii=False, indent=2) + "\n"
    elif fmt == "ndjson":
        text = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records)
    elif fmt == "xml":
        root = ET.Element("rows")
        for row in records:
            node = ET.SubElement(root, "row")
            for k in (fields or ["value"]):
                child = ET.SubElement(node, xml_name(k))
                child.text = scalar(row.get(k, ""))
        text = ET.tostring(root, encoding="unicode") + "\n"
    elif fmt == "yaml":
        if _yaml is not None:
            text = _yaml.safe_dump(records, allow_unicode=True, sort_keys=False)
        else:
            lines = []
            for row in records:
                keys = fields or ["value"]
                for i, k in enumerate(keys):
                    prefix = "- " if i == 0 else "  "
                    lines.append("%s%s: %s" % (prefix, k, scalar(row.get(k, ""))))
            text = "\n".join(lines) + ("\n" if lines else "")
    elif fmt == "toml":
        lines = []
        for row in records:
            lines.append("[[rows]]")
            for k in (fields or ["value"]):
                v = _toml_value(row.get(k, ""))
                if v is not None:
                    lines.append('%s = %s' % (xml_name(k).replace("-", "_"), v))
        text = "\n".join(lines) + ("\n" if lines else "")
    elif fmt == "md":
        keys = fields or ["value"]
        lines = ["| " + " | ".join(keys) + " |",
                 "|" + "|".join(["---"] * len(keys)) + "|"]
        for row in records:
            lines.append("| " + " | ".join(scalar(row.get(k, "")).replace("|", "\\|")
                                          for k in keys) + " |")
        text = "\n".join(lines) + "\n"
    else:
        fail("格式 %s 不支持写入" % fmt, EXIT_USAGE)
    w(path, text)
    return path


def deliver(ns, payload):
    """报告类动作：有 -o 写 JSON 报告，否则打印一行 JSON。"""
    out = getattr(ns, "output", None)
    if not out:
        return emit(payload)
    p = unique_path(Path(out).resolve())
    w(p, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    return emit({"output": str(p), "bytes": p.stat().st_size,
                 "records": payload.get("records", payload.get("count"))})


def write_out(ns, records, fmt, source=None, extra=None):
    """变换类动作：-o 是数据产物文件（不是报告），缺失时另存 <stem>-out.<ext>。"""
    out = getattr(ns, "output", None)
    if out:
        target = Path(out).resolve()
        if source and target == Path(source).resolve():
            fail("输出不能覆盖输入：%s" % target, EXIT_IO)
    else:
        base = Path(source) if source else Path("records")
        target = base.with_name(base.stem + "-out." + ("csv" if fmt == "tsv" else fmt))
    target = unique_path(target)
    write_records(records, target, fmt, getattr(ns, "encoding", "utf-8"))
    payload = {"output": str(target), "records": len(records),
               "fields": len(fields_of(records)), "format": fmt,
               "bytes": target.stat().st_size}
    if extra:
        payload.update(extra)
    return emit(payload)


def infer_type(values):
    present = [v for v in values if v not in (None, "")]
    if not present:
        return "string"
    if all(isinstance(v, bool) or scalar(v).lower() in ("true", "false") for v in present):
        return "boolean"
    if all(re.fullmatch(r"-?\d+", scalar(v)) for v in present):
        return "integer"
    if all(re.fullmatch(r"-?\d+(\.\d+)?", scalar(v)) for v in present):
        return "number"
    return "string"


def numeric(v):
    try:
        return float(scalar(v))
    except (ValueError, TypeError):
        return None


OPS = ("startswith", "endswith", "contains", "regex", ">=", "<=", "!=", "=", ">", "<", "in")


def parse_where(expr):
    m = re.match(r"^\s*([^\s]+)\s*(startswith|endswith|contains|regex|>=|<=|!=|=|>|<|in)\s*(.*)$",
                 expr.strip())
    if not m:
        fail("条件非法：%s（写法：字段 运算符 值）" % expr, EXIT_USAGE)
    return m.group(1), m.group(2), m.group(3).strip().strip('"\'')


def match_one(row, cond):
    field, op, value = cond
    actual = scalar(row.get(field, ""))
    if op == "=":
        return actual == value
    if op == "!=":
        return actual != value
    if op == "contains":
        return value in actual
    if op == "startswith":
        return actual.startswith(value)
    if op == "endswith":
        return actual.endswith(value)
    if op == "in":
        return actual in [x.strip() for x in value.split(",")]
    if op == "regex":
        try:
            return bool(re.search(value, actual))
        except re.error as exc:
            fail("正则无效：%s" % exc, EXIT_USAGE)
    a, b = numeric(actual), numeric(value)
    if a is None or b is None:
        a, b = actual, value
    return {">": a > b, "<": a < b, ">=": a >= b, "<=": a <= b}.get(op, False)


def flatten(obj, sep=".", prefix="", out=None):
    out = {} if out is None else out
    if isinstance(obj, dict):
        for k, v in obj.items():
            flatten(v, sep, prefix + str(k) + sep, out)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            flatten(v, sep, prefix + str(i) + sep, out)
    else:
        out[prefix.rstrip(sep) or "value"] = obj
    return out


# ---------------------------------------------------------------- 12 个动作

def run_data_convert(ns):
    fmt_in = guess_format(ns.input, ns.source_format)
    fmt_out = guess_format(ns.output or "out.csv", ns.target_format)
    records = read_records(ns.input, fmt_in, ns.encoding)
    return write_out(ns, records, fmt_out, ns.input)


def run_data_validate(ns):
    reports, problems = [], 0
    for raw in ns.input:
        fmt = guess_format(raw, ns.source_format)
        item = {"file": str(raw), "format": fmt}
        try:
            records = read_records(raw, fmt)
            fields = fields_of(records)
            inconsistent = [i for i, r in enumerate(records) if set(r) != set(fields)]
            missing = {k: sum(1 for r in records if r.get(k) in (None, "")) for k in fields}
            item.update({"records": len(records), "fields": len(fields),
                         "field_names": fields,
                         "inconsistent_rows": inconsistent[:20],
                         "missing_by_field": missing, "valid": not inconsistent})
            problems += int(bool(inconsistent))
        except Exception as exc:  # noqa: BLE001
            item.update({"valid": False, "error": str(exc)[:200]})
            problems += 1
        reports.append(item)
    payload = {"count": len(reports), "problems": problems,
               "files": reports, "strict": bool(ns.strict)}
    rc = deliver(ns, payload)
    return EXIT_FAIL if ns.strict and problems else rc


def run_data_schema(ns):
    records = read_records(ns.input, guess_format(ns.input, ns.source_format))
    fields = fields_of(records)
    props = {}
    for k in fields:
        values = [r.get(k) for r in records]
        t = infer_type(values)
        props[k] = {"type": "boolean" if t == "boolean" else
                    "integer" if t == "integer" else
                    "number" if t == "number" else "string"}
    required = [k for k in fields if all(r.get(k) not in (None, "") for r in records)]
    schema = {"$schema": "http://json-schema.org/draft-07/schema#",
              "title": ns.title, "type": "array", "record_count": len(records),
              "items": {"type": "object", "properties": props, "required": required}}
    return deliver(ns, {"schema": schema, "fields": len(fields),
                        "records": len(records), "required": required})


def run_data_merge(ns):
    fmt_out = guess_format(ns.output or "merged.csv", ns.target_format)
    tables = [read_records(p, guess_format(p)) for p in ns.inputs]
    if ns.how == "left" and ns.by:
        base = tables[0]
        index = {}
        for row in tables[1] if len(tables) > 1 else []:
            index.setdefault(scalar(row.get(ns.by, "")), row)
        merged = []
        for row in base:
            extra = index.get(scalar(row.get(ns.by, "")), {})
            merged.append({**row, **{k: v for k, v in extra.items() if k not in row}})
    else:
        merged = [r for table in tables for r in table]
    return write_out(ns, merged, fmt_out, ns.inputs[0],
                     {"inputs": len(tables), "how": ns.how, "by": ns.by})


def run_data_filter(ns):
    fmt_in = guess_format(ns.input, ns.source_format)
    fmt_out = guess_format(ns.output or "filtered.csv", ns.target_format)
    records = read_records(ns.input, fmt_in)
    conds = [parse_where(e) for e in ns.where]
    if conds:
        fn = all if ns.match == "all" else any
        kept = [r for r in records if fn(match_one(r, c) for c in conds)]
    else:
        kept = records
    if ns.limit:
        kept = kept[:ns.limit]
    return write_out(ns, kept, fmt_out, ns.input,
                     {"matched": len(kept), "source_records": len(records)})


def run_data_select(ns):
    fmt_in = guess_format(ns.input, ns.source_format)
    fmt_out = guess_format(ns.output or "selected.csv", ns.target_format)
    records = read_records(ns.input, fmt_in)
    keep = [x.strip() for x in ns.fields.split(",")] if ns.fields else None
    drop = {x.strip() for x in ns.exclude.split(",")} if ns.exclude else set()
    renames = {}
    for item in ns.rename:
        if ":" not in item:
            fail("重命名格式应为 old:new：%s" % item, EXIT_USAGE)
        old, new = item.split(":", 1)
        renames[old.strip()] = new.strip()
    out = []
    for row in records:
        item = {renames.get(k, k): v for k, v in row.items()
                if (keep is None or k in keep) and k not in drop}
        out.append(item)
    return write_out(ns, out, fmt_out, ns.input, {"renamed": len(renames)})


def run_data_sort(ns):
    fmt_in = guess_format(ns.input, ns.source_format)
    fmt_out = guess_format(ns.output or "sorted.csv", ns.target_format)
    records = read_records(ns.input, fmt_in)
    if not ns.by:
        fail("请用 --by 指定排序字段", EXIT_USAGE)

    def key(row):
        v = row.get(ns.by, "")
        return (numeric(v) if ns.numeric and numeric(v) is not None else scalar(v).lower())

    records.sort(key=key, reverse=ns.desc)
    return write_out(ns, records, fmt_out, ns.input, {"by": ns.by, "desc": bool(ns.desc)})


def run_data_dedupe(ns):
    fmt_in = guess_format(ns.input, ns.source_format)
    fmt_out = guess_format(ns.output or "uniq.csv", ns.target_format)
    records = read_records(ns.input, fmt_in)
    keys = [x.strip() for x in ns.by.split(",")] if ns.by else None
    seen, out = set(), []
    source = records[::-1] if ns.keep == "last" else records
    for row in source:
        marker = json.dumps([scalar(row.get(k, "")) for k in keys] if keys else row,
                           ensure_ascii=False, sort_keys=True)
        if marker not in seen:
            seen.add(marker)
            out.append(row)
    if ns.keep == "last":
        out.reverse()
    return write_out(ns, out, fmt_out, ns.input,
                     {"removed": len(records) - len(out), "keep": ns.keep})


def run_data_flatten(ns):
    fmt_out = guess_format(ns.output or "flat.csv", ns.target_format)
    raw = json.loads(read_text(ns.input))
    items = raw if isinstance(raw, list) else raw.get("data", [raw]) if isinstance(raw, dict) else [raw]
    out = [flatten(x if isinstance(x, (dict, list)) else {"value": x}, ns.sep)
           for x in items]
    return write_out(ns, out, fmt_out, ns.input, {"sep": ns.sep})


def run_data_stats(ns):
    records = read_records(ns.input, guess_format(ns.input, ns.source_format))
    fields = fields_of(records)
    stats = {}
    for k in fields:
        values = [r.get(k) for r in records]
        present = [scalar(v) for v in values if v not in (None, "")]
        freq = {}
        for v in present:
            freq[v] = freq.get(v, 0) + 1
        top = sorted(freq.items(), key=lambda x: -x[1])[:ns.top]
        stats[k] = {"count": len(values), "missing": len(values) - len(present),
                    "missing_rate": round((len(values) - len(present)) / max(len(values), 1), 4),
                    "unique": len(freq), "type": infer_type(values),
                    "min": min(present, key=numeric) if present and all(numeric(v) is not None for v in present) else None,
                    "max": max(present, key=numeric) if present and all(numeric(v) is not None for v in present) else None,
                    "top": [{"value": v, "count": c} for v, c in top]}
    return deliver(ns, {"input": str(ns.input), "records": len(records),
                        "fields": len(fields), "stats": stats})


def run_data_diff(ns):
    fmt = guess_format(ns.old, ns.source_format)
    old = read_records(ns.old, fmt)
    new = read_records(ns.new, guess_format(ns.new, ns.source_format))
    key = ns.key
    if key:
        om = {scalar(r.get(key, "")): r for r in old}
        nm = {scalar(r.get(key, "")): r for r in new}
        added = sorted(set(nm) - set(om))
        removed = sorted(set(om) - set(nm))
        changed = []
        for k in sorted(set(om) & set(nm)):
            delta = {f: {"old": scalar(om[k].get(f, "")), "new": scalar(nm[k].get(f, ""))}
                     for f in set(om[k]) | set(nm[k])
                     if scalar(om[k].get(f, "")) != scalar(nm[k].get(f, ""))}
            if delta:
                changed.append({"key": k, "fields": delta})
    else:
        added = [str(i) for i in range(len(old), len(new))]
        removed = [str(i) for i in range(len(new), len(old))]
        changed = [{"key": str(i), "fields": {f: {"old": scalar(old[i].get(f, "")),
                                                   "new": scalar(new[i].get(f, ""))}
                                              for f in set(old[i]) | set(new[i])
                                              if scalar(old[i].get(f, "")) != scalar(new[i].get(f, ""))}}
                   for i in range(min(len(old), len(new)))]
        changed = [c for c in changed if c["fields"]]
    return deliver(ns, {"old": str(ns.old), "new": str(ns.new), "key": key,
                        "old_records": len(old), "new_records": len(new),
                        "added": added, "removed": removed, "changed": changed,
                        "differences": len(added) + len(removed) + len(changed)})


def run_data_split(ns):
    records = read_records(ns.input, guess_format(ns.input, ns.source_format))
    out_dir = Path(ns.output).resolve() if ns.output else Path(ns.input).parent / (Path(ns.input).stem + "-parts")
    if out_dir.is_file():
        fail("输出路径是文件，请给目录：%s" % out_dir, EXIT_IO)
    out_dir = unique_path(out_dir)
    out_dir.mkdir(parents=True)
    groups = {}
    if ns.by == "field":
        if not ns.field:
            fail("--by field 需要 --field 指定字段", EXIT_USAGE)
        for row in records:
            groups.setdefault(re.sub(r"[^\w\-]", "_", scalar(row.get(ns.field, "empty"))), []).append(row)
    else:
        if ns.size <= 0:
            fail("--size 必须为正整数", EXIT_USAGE)
        for i in range(0, len(records), ns.size):
            groups["part-%04d" % (i // ns.size + 1)] = records[i:i + ns.size]
    manifest = []
    for name, rows in groups.items():
        path = out_dir / ("%s.%s" % (name, ns.target_format))
        write_records(rows, path, ns.target_format)
        manifest.append({"file": path.name, "records": len(rows)})
    w(out_dir / "split-manifest.json",
      json.dumps({"source": str(ns.input), "by": ns.by, "parts": manifest},
                 ensure_ascii=False, indent=2) + "\n")
    return emit({"output_dir": str(out_dir), "parts": len(manifest),
                 "records": len(records), "manifest": str(out_dir / "split-manifest.json")})
