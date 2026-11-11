# -*- coding: utf-8 -*-
"""隐私全搞定 · 共享层：规则引擎、元数据读写、二维码/条码与 10 个动作。

零必需依赖。二维码生成/识别是可选增强：缺依赖时明确给本地安装指引（rc=2），
绝不伪装成功、绝不联网安装。元数据清理只生成新副本，原文件只读。
"""
from __future__ import annotations

import html
import json
import re
import struct
import sys
import zipfile
import zlib
from pathlib import Path

EXIT_USAGE = 2
EXIT_IO = 3
EXIT_FAIL = 5

# ---------------------------------------------------------------- 规则引擎

def _luhn(s):
    total, alt = 0, False
    for ch in reversed(s):
        d = int(ch)
        if alt:
            d *= 2
            if d > 9:
                d -= 9
        total += d
        alt = not alt
    return total % 10 == 0


def _id_check(s):
    if len(s) != 18:
        return False
    weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
    codes = "10X98765432"
    total = sum(int(c) * w for c, w in zip(s[:17], weights))
    return codes[total % 11] == s[17].upper()


def _ipv4(s):
    return all(0 <= int(x) <= 255 for x in s.split("."))


RULES = [
    {"name": "phone_cn", "label": "手机号", "pattern": r"(?<!\d)1[3-9]\d{9}(?!\d)", "check": None},
    {"name": "id_card_cn", "label": "身份证", "pattern": r"(?<!\d)\d{17}[\dXx](?!\d)", "check": _id_check},
    {"name": "email", "label": "邮箱", "pattern": r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", "check": None},
    {"name": "bank_card", "label": "银行卡", "pattern": r"(?<!\d)\d{13,19}(?!\d)", "check": _luhn},
    {"name": "ipv4", "label": "IPv4", "pattern": r"(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)", "check": _ipv4},
    {"name": "mac", "label": "MAC 地址", "pattern": r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b", "check": None},
    {"name": "car_plate_cn", "label": "车牌", "pattern": r"[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领][A-Z][A-Z0-9]{5}", "check": None},
    {"name": "passport_cn", "label": "护照号", "pattern": r"(?<![A-Za-z0-9])[EGDSP]\d{8}(?!\d)", "check": None},
    {"name": "qq", "label": "QQ 号", "pattern": r"(?i)(?<!\d)QQ[号:：\s]*[1-9]\d{4,10}(?!\d)", "check": None},
    {"name": "api_key", "label": "API 密钥", "pattern": r"(?:sk-|ak-|api[_-]?key|token)[\-_A-Za-z0-9]{16,}", "check": None},
    {"name": "url_token", "label": "URL 令牌", "pattern": r"[?&](?:token|access_token|key|secret)=[A-Za-z0-9._\-]{8,}", "check": None},
]

CODE128 = [
    "212222", "222122", "222221", "121223", "121322", "131222", "122213", "122312",
    "132212", "221213", "221312", "231212", "112232", "122132", "122231", "113222",
    "123122", "123221", "223211", "221132", "221231", "213212", "223112", "312131",
    "311222", "321122", "321221", "312212", "322112", "322211", "212123", "212321",
    "232121", "111323", "131123", "131321", "112313", "132113", "132311", "211313",
    "231113", "231311", "112133", "112331", "132131", "113123", "113321", "133121",
    "313121", "211331", "231131", "213113", "213311", "213131", "311123", "311321",
    "331121", "312113", "312311", "332111", "314111", "221411", "431111", "111224",
    "111422", "121124", "121421", "141122", "141221", "112214", "112412", "122114",
    "122411", "142112", "142211", "241211", "221114", "413111", "241112", "134111",
    "111242", "121142", "121241", "114212", "124112", "124211", "411212", "421112",
    "421211", "212141", "214121", "412121", "111143", "111341", "131141", "114113",
    "114311", "411113", "411311", "113141", "114131", "311141", "411131", "211412",
    "211214", "211232", "2331112",
]


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


def read_text(path, encoding=None):
    p = Path(path)
    if not p.is_file():
        fail("输入不存在：%s" % p, EXIT_IO)
    raw = p.read_bytes()
    codecs = [encoding] if encoding else ["utf-8-sig", "gb18030", "latin-1"]
    for codec in codecs:
        try:
            text = raw.decode(codec)
        except (UnicodeDecodeError, LookupError):
            continue
        if codec == "utf-8-sig" and not raw.startswith(b"\xef\xbb\xbf"):
            # 不带 BOM 的普通 UTF-8：回写时若沿用 utf-8-sig 会凭空多出一个 BOM
            codec = "utf-8"
        return text, codec
    return raw.decode("utf-8", "replace"), "utf-8/replace"


def deliver(ns, payload, text=None, binary=None):
    out = getattr(ns, "output", None)
    if not out:
        if text is not None:
            print(text, end="")
            return 0
        return emit(payload)
    p = unique_path(Path(out).resolve())
    if binary is not None:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(binary)
    else:
        w(p, text if text is not None else json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    return emit({"output": str(p), "bytes": p.stat().st_size,
                 "summary": {k: payload[k] for k in ("hits", "count", "files", "failed")
                             if k in payload and isinstance(payload[k], (int, list))}})


def load_rules(ns):
    rules = [dict(r) for r in RULES]
    if ns.types:
        wanted = {x.strip() for x in ns.types.split(",") if x.strip()}
        unknown = wanted - {r["name"] for r in rules}
        if unknown:
            fail("未知规则名：%s" % ", ".join(sorted(unknown)), EXIT_USAGE)
        rules = [r for r in rules if r["name"] in wanted]
    if ns.rules:
        custom = json.loads(read_text(ns.rules)[0])
        if not isinstance(custom, list):
            fail("自定义规则必须是数组", EXIT_USAGE)
        for item in custom:
            if not isinstance(item, dict) or not item.get("name") or not item.get("pattern"):
                fail("自定义规则缺 name/pattern：%s" % item, EXIT_USAGE)
            try:
                re.compile(item["pattern"])
            except re.error as exc:
                fail("自定义规则正则无效 %s：%s" % (item.get("name"), exc), EXIT_USAGE)
            rules.append({"name": item["name"], "label": item.get("label", item["name"]),
                          "pattern": item["pattern"], "check": None})
    return rules


def mask_value(kind, value):
    if kind == "email" and "@" in value:
        name, domain = value.split("@", 1)
        return (name[0] + "***@" + domain) if name else "***@" + domain
    if kind == "ipv4":
        parts = value.split(".")
        return parts[0] + ".*.*.*" if len(parts) == 4 else "***"
    if len(value) >= 8:
        return value[:3] + "*" * (len(value) - 7) + value[-4:]
    if len(value) >= 4:
        return value[:1] + "*" * (len(value) - 2) + value[-1:]
    return "*" * len(value)


def replacement(rule, value, mode):
    if mode == "placeholder":
        return "<%s>" % rule["label"]
    if mode == "remove":
        return ""
    return mask_value(rule["name"], value)


def find_hits(text, rules, context=0, stats=None):
    hits = []
    for rule in rules:
        for m in re.finditer(rule["pattern"], text):
            value = m.group(0)
            if rule.get("check") and not rule["check"](value):
                # 校验位不过的候选（如随手编的身份证）不算命中，但要计数，
                # 否则用户会以为规则没生效。
                if stats is not None:
                    stats[rule["name"]] = stats.get(rule["name"], 0) + 1
                continue
            line = text.count("\n", 0, m.start()) + 1
            col = m.start() - (text.rfind("\n", 0, m.start()) + 1) + 1
            item = {"type": rule["name"], "label": rule["label"],
                    "masked": mask_value(rule["name"], value),
                    "line": line, "column": col, "start": m.start(), "end": m.end(),
                    "length": len(value)}
            if context:
                item["context"] = text[max(0, m.start() - context):m.end() + context]
            hits.append(item)
    hits.sort(key=lambda h: h["start"])
    return hits


def redact(text, rules, mode):
    """按规则倒序替换，避免 offset 漂移；更具体的规则先处理，减少相互覆盖。"""
    count, by_type = 0, {}
    for rule in rules:
        spans = []
        for m in re.finditer(rule["pattern"], text):
            value = m.group(0)
            if rule.get("check") and not rule["check"](value):
                continue
            spans.append((m.start(), m.end(), replacement(rule, value, mode)))
        for start, end, repl in reversed(spans):
            text = text[:start] + repl + text[end:]
            count += 1
            by_type[rule["name"]] = by_type.get(rule["name"], 0) + 1
    return text, count, by_type


# ---------------------------------------------------------------- 元数据

def _jpeg_meta(data):
    out = {"format": "jpeg", "segments": []}
    if not data.startswith(b"\xff\xd8"):
        return {"format": "unknown", "skipped": "不是 JPEG"}
    pos = 2
    while pos + 4 <= len(data):
        if data[pos] != 0xFF:
            break
        marker = data[pos + 1]
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            pos += 2
            continue
        if marker == 0xDA or marker == 0xD9:
            break
        length = struct.unpack(">H", data[pos + 2:pos + 4])[0]
        seg = data[pos + 4:pos + 2 + length]
        name = {0xE0: "APP0", 0xE1: "APP1", 0xE2: "APP2", 0xEC: "APP12",
                0xED: "APP13", 0xFE: "COM"}.get(marker, "marker-%02X" % marker)
        entry = {"name": name, "bytes": len(seg)}
        printable = "".join(chr(c) if 32 <= c < 127 else " " for c in seg[:120])
        found = re.findall(r"[ -~]{5,}", printable)
        if found:
            entry["text"] = [x.strip() for x in found[:8] if x.strip()]
        if seg.startswith(b"Exif\x00\x00"):
            entry["exif"] = _tiff_meta(seg[6:])
        out["segments"].append(entry)
        pos += 2 + length
    return out


def _tiff_meta(tiff):
    if len(tiff) < 8:
        return {}
    endian = "<" if tiff[:2] == b"II" else ">"
    try:
        off = struct.unpack(endian + "I", tiff[4:8])[0]
        count = struct.unpack(endian + "H", tiff[off:off + 2])[0]
    except (struct.error, IndexError):
        return {}
    names = {0x010E: "ImageDescription", 0x010F: "Make", 0x0110: "Model",
             0x0112: "Orientation", 0x0131: "Software", 0x0132: "DateTime",
             0x8298: "Copyright", 0x013B: "Artist", 0x8825: "GPSInfo"}
    out = {}
    for i in range(min(count, 60)):
        entry = off + 2 + i * 12
        if entry + 12 > len(tiff):
            break
        tag, typ, size = struct.unpack(endian + "HHI", tiff[entry:entry + 8])
        if typ == 2 and size <= 256:
            if size <= 4:
                raw = tiff[entry + 8:entry + 8 + size]
            else:
                ptr = struct.unpack(endian + "I", tiff[entry + 8:entry + 12])[0]
                raw = tiff[ptr:ptr + size]
            out[names.get(tag, "tag-0x%04X" % tag)] = raw.decode("latin-1", "replace").strip("\x00 ")
        elif typ in (3, 4) and size == 1:
            out[names.get(tag, "tag-0x%04X" % tag)] = \
                struct.unpack(endian + "H", tiff[entry + 8:entry + 10])[0] if typ == 3 else \
                struct.unpack(endian + "I", tiff[entry + 8:entry + 12])[0]
    return out


def _png_meta(data):
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        return {"format": "unknown", "skipped": "不是 PNG"}
    pos, out = 8, {"format": "png", "text_chunks": []}
    while pos + 12 <= len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        ctype = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + length]
        if ctype in (b"tEXt", b"iTXt", b"zTXt"):
            try:
                if ctype == b"zTXt":
                    key, rest = body.split(b"\x00", 1)
                    text = zlib.decompress(rest[1:]).decode("utf-8", "replace")
                elif ctype == b"tEXt":
                    key, text = body.split(b"\x00", 1)
                    text = text.decode("latin-1", "replace")
                else:
                    key = body.split(b"\x00", 1)[0]
                    text = body.decode("latin-1", "replace")[:120]
                out["text_chunks"].append({"keyword": key.decode("latin-1"), "text": text[:200]})
            except (ValueError, zlib.error):
                out["text_chunks"].append({"keyword": "?", "text": "<无法解析>"})
        if ctype == b"IEND":
            break
        pos += 12 + length
    return out


def _ooxml_meta(p):
    out = {"format": "ooxml", "properties": {}}
    try:
        with zipfile.ZipFile(p) as z:
            for name in ("docProps/core.xml", "docProps/app.xml"):
                if name not in z.namelist():
                    continue
                raw = z.read(name).decode("utf-8", "replace")
                pairs = re.findall(r"<([A-Za-z0-9:_\-]+)[^>]*>([^<]{1,300})</\1>", raw)
                out["properties"][name] = {tag: text.strip() for tag, text in pairs if text.strip()}
    except zipfile.BadZipFile:
        out["skipped"] = "不是有效的 OOXML zip"
    return out


def _pdf_meta(data):
    out = {"format": "pdf", "info": {}}
    for key in ("Author", "Creator", "Producer", "Title", "Subject", "Keywords",
                "CreationDate", "ModDate"):
        m = re.search(rb"/" + key.encode() + rb"\s*\(((?:\\.|[^\\()])*)\)", data)
        if m:
            out["info"][key] = m.group(1).decode("latin-1", "replace")
    if b"/Encrypt" in data:
        out["encrypted"] = True
    return out


def metadata_of(path):
    p = Path(path)
    data = p.read_bytes()
    ext = p.suffix.lower()
    if ext in (".jpg", ".jpeg", ".jpe"):
        return _jpeg_meta(data)
    if ext == ".png":
        return _png_meta(data)
    if ext in (".docx", ".xlsx", ".pptx"):
        return _ooxml_meta(p)
    if ext == ".pdf":
        return _pdf_meta(data)
    return {"format": ext or "unknown", "skipped": "该格式没有可用的元数据解析器"}


def clean_bytes(path, kinds=None):
    p = Path(path)
    data = p.read_bytes()
    ext = p.suffix.lower()
    removed, skipped = [], []
    want = set(kinds) if kinds else {"jpeg", "png", "ooxml", "pdf"}
    if ext in (".jpg", ".jpeg", ".jpe") and "jpeg" in want:
        if not data.startswith(b"\xff\xd8"):
            return None, [], ["不是 JPEG"]
        out, pos, sos = bytearray(data[:2]), 2, None
        drop = {0xE1, 0xE2, 0xEC, 0xED, 0xFE}
        while pos + 4 <= len(data):
            if data[pos] != 0xFF:
                break
            marker = data[pos + 1]
            if marker == 0xDA:
                sos = pos
                break
            if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                out += data[pos:pos + 2]
                pos += 2
                continue
            length = struct.unpack(">H", data[pos + 2:pos + 4])[0]
            if marker in drop:
                removed.append("marker-%02X" % marker)
            else:
                out += data[pos:pos + 2 + length]
            pos += 2 + length
        out += data[sos:] if sos is not None else b"\xff\xd9"
        return bytes(out), removed, skipped
    if ext == ".png" and "png" in want:
        if not data.startswith(b"\x89PNG\r\n\x1a\n"):
            return None, [], ["不是 PNG"]
        out, pos = bytearray(data[:8]), 8
        while pos + 12 <= len(data):
            length = struct.unpack(">I", data[pos:pos + 4])[0]
            ctype = data[pos + 4:pos + 8]
            chunk = data[pos:pos + 12 + length]
            if ctype in (b"tEXt", b"iTXt", b"zTXt", b"eXIf"):
                removed.append(ctype.decode("latin-1"))
            else:
                out += chunk
            if ctype == b"IEND":
                break
            pos += 12 + length
        return bytes(out), removed, skipped
    if ext in (".docx", ".xlsx", ".pptx") and "ooxml" in want:
        import io
        buf = io.BytesIO()
        try:
            with zipfile.ZipFile(p) as src, zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as dst:
                for item in src.infolist():
                    raw = src.read(item.filename)
                    if item.filename in ("docProps/core.xml", "docProps/app.xml"):
                        text = raw.decode("utf-8", "replace")
                        new = re.sub(r"(<[A-Za-z0-9:_\-]+[^>]*>)[^<]{1,300}(</)", r"\1\2", text)
                        if new != text:
                            removed.append(item.filename)
                        raw = new.encode("utf-8")
                    dst.writestr(item, raw)
            return buf.getvalue(), removed, skipped
        except zipfile.BadZipFile:
            return None, [], ["不是有效的 OOXML zip"]
    if ext == ".pdf" and "pdf" in want:
        if b"/Encrypt" in data:
            return None, [], ["加密 PDF 不改写"]
        out = data
        for key in (b"Author", b"Creator", b"Producer", b"Title", b"Subject",
                    b"Keywords", b"CreationDate", b"ModDate"):
            pattern = rb"/" + key + rb"\s*\(((?:\\.|[^\\()])*)\)"
            out, n = re.subn(pattern, b"/" + key + b" ()", out)
            if n:
                removed.append(key.decode())
        skipped.append("只清理 /Info 常见键；注释、修订、XMP 与对象流未处理")
        return out, removed, skipped
    return None, [], ["该格式不支持清理：%s" % (ext or "unknown")]


# ---------------------------------------------------------------- 10 个动作

def run_pv_scan(ns):
    text, codec = read_text(ns.input, ns.encoding)
    rules = load_rules(ns)
    rejected = {}
    hits = find_hits(text, rules, ns.context, rejected)
    by_type = {}
    for h in hits:
        by_type[h["type"]] = by_type.get(h["type"], 0) + 1
    return deliver(ns, {"input": str(ns.input), "encoding": codec,
                        "hits": len(hits), "by_type": by_type,
                        "rejected": rejected,
                        "rules": [r["name"] for r in rules],
                        "findings": hits,
                        "note": "默认不输出命中内容明文；rejected 是校验位未通过而排除的候选数"})


def run_pv_redact(ns):
    text, codec = read_text(ns.input, ns.encoding)
    rules = load_rules(ns)
    preview = not ns.output or ns.dry_run
    new_text, count, by_type = redact(text, rules, ns.mode)
    payload = {"input": str(ns.input), "encoding": codec, "mode": ns.mode,
               "hits": count, "by_type": by_type, "preview": preview,
               "bytes_in": len(text.encode(codec, "replace")),
               "bytes_out": len(new_text.encode(codec, "replace"))}
    if preview:
        payload["sample"] = new_text[:200]
        return emit(payload)
    p = unique_path(Path(ns.output).resolve())
    if p == Path(ns.input).resolve():
        fail("输出不能覆盖输入：%s" % p, EXIT_IO)
    p.write_bytes(new_text.encode(codec, "replace"))
    return emit({"output": str(p), "hits": count, "by_type": by_type,
                 "mode": ns.mode, "bytes": p.stat().st_size})


def run_pv_batch(ns):
    root = Path(ns.input).resolve()
    if not root.is_dir():
        fail("输入不是目录：%s" % root, EXIT_IO)
    out_dir = Path(ns.output).resolve() if ns.output else root.parent / (root.name + "-privacy")
    out_dir = unique_path(out_dir)
    out_dir.mkdir(parents=True)
    rules = load_rules(ns)
    results, failed, total = [], [], 0
    import fnmatch
    for p in sorted(root.rglob("*") if ns.recursive else root.iterdir()):
        if not p.is_file() or p.is_symlink() or not fnmatch.fnmatch(p.name, ns.pattern):
            continue
        try:
            text, codec = read_text(str(p))
        except Exception as exc:  # noqa: BLE001
            failed.append({"file": p.name, "error": str(exc)})
            continue
        if ns.mode == "scan":
            hits = find_hits(text, rules)
            item = {"file": p.name, "hits": len(hits)}
            rel = out_dir / (p.stem + "-findings.json")
            w(unique_path(rel), json.dumps({"file": p.name, "findings": hits},
                                           ensure_ascii=False, indent=2) + "\n")
        else:
            new_text, count, by_type = redact(text, rules, "mask")
            item = {"file": p.name, "hits": count, "by_type": by_type}
            if ns.apply:
                rel = out_dir / p.name
                w(unique_path(rel), new_text)
                item["output"] = str(rel)
            else:
                item["preview_only"] = True
        total += item.get("hits", 0)
        results.append(item)
    report = {"input": str(root), "output_dir": str(out_dir), "mode": ns.mode,
              "files": len(results), "hits": total, "apply": bool(ns.apply),
              "failed": failed, "results": results}
    w(out_dir / "report.json", json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return emit(report)


def run_pv_report(ns):
    data = json.loads(read_text(ns.input)[0])
    files = data.get("results", [])
    by_type = dict(data.get("by_type", {}))
    for f in files:
        for k, v in f.get("by_type", {}).items():
            by_type[k] = by_type.get(k, 0) + v
    payload = {"source": str(ns.input), "format": ns.format,
               "mode": data.get("mode", "scan"), "files": data.get("files", 1),
               "hits": data.get("hits", len(data.get("findings", []))),
               "by_type": by_type, "failed": data.get("failed", [])}
    if ns.format == "json":
        return deliver(ns, payload)
    lines = ["# 隐私扫描报告", "",
             "- 模式：%s" % payload["mode"],
             "- 文件数：%s" % payload["files"],
             "- 命中总数：%s" % payload["hits"],
             "- 失败：%d" % len(payload["failed"]), "",
             "| 类型 | 命中数 |", "|---|---|"]
    lines += ["| %s | %s |" % (k, v) for k, v in sorted(by_type.items())] or ["| （无） | 0 |"]
    md = "\n".join(lines) + "\n"
    if ns.format == "md":
        return deliver(ns, payload, md)
    rows = "".join("<tr><td>%s</td><td>%s</td></tr>" % (html.escape(k), v)
                   for k, v in sorted(by_type.items()))
    htm = ("<!doctype html><meta charset='utf-8'><title>隐私扫描报告</title>"
           "<style>body{font:14px/1.6 system-ui;margin:2rem;color:#222}"
           "table{border-collapse:collapse}td,th{border:1px solid #ddd;padding:4px 10px}</style>"
           "<h1>隐私扫描报告</h1><p>文件 %s，命中 %s，失败 %d</p>"
           "<table><tr><th>类型</th><th>命中数</th></tr>%s</table>"
           % (payload["files"], payload["hits"], len(payload["failed"]), rows))
    return deliver(ns, payload, htm)


def run_pv_rules(ns):
    rules = [dict(r) for r in RULES]
    problems = []
    if ns.rules:
        custom = json.loads(read_text(ns.rules)[0])
        if not isinstance(custom, list):
            fail("自定义规则必须是数组", EXIT_USAGE)
        for item in custom:
            try:
                re.compile(item.get("pattern", ""))
                rules.append({"name": item.get("name"), "label": item.get("label", ""),
                              "pattern": item.get("pattern"), "custom": True})
            except (re.error, AttributeError) as exc:
                problems.append("%s: %s" % (item.get("name"), exc))
    listed = [{"name": r["name"], "label": r["label"], "pattern": r["pattern"],
               "has_check": bool(r.get("check")), "custom": bool(r.get("custom"))}
              for r in rules if not ns.type or r["name"] == ns.type]
    return deliver(ns, {"count": len(listed), "problems": problems,
                        "valid": not problems, "rules": listed})


def run_pv_metadata(ns):
    rows, failed = [], []
    for raw in ns.input:
        p = Path(raw)
        if not p.is_file():
            failed.append({"file": str(p), "error": "不存在"})
            continue
        try:
            item = metadata_of(p)
            item["file"] = str(p)
            rows.append(item)
        except OSError as exc:
            failed.append({"file": str(p), "error": str(exc)})
    return deliver(ns, {"count": len(rows), "failed": failed, "files": rows})


def run_pv_clean(ns):
    src = Path(ns.input).resolve()
    if not src.is_file():
        fail("输入不存在：%s" % src, EXIT_IO)
    kinds = [x.strip() for x in ns.kinds.split(",")] if ns.kinds else None
    data, removed, skipped = clean_bytes(src, kinds)
    payload = {"input": str(src), "removed": removed, "skipped": skipped,
               "supported": data is not None, "dry_run": bool(ns.dry_run)}
    if data is None:
        payload["note"] = "未生成副本：该格式无法安全清理"
        return emit(payload)
    if ns.dry_run:
        return emit(dict(payload, preview=True))
    if not ns.output:
        fail("请给 -o 输出路径", EXIT_USAGE)
    p = unique_path(Path(ns.output).resolve())
    if p == src:
        fail("输出不能覆盖输入：%s" % p, EXIT_IO)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    return emit(dict(payload, output=str(p), bytes=len(data)))


def run_pv_barcode(ns):
    text = ns.text
    if any(ord(c) < 32 or ord(c) > 126 for c in text):
        fail("Code128-B 只支持 ASCII 可打印字符（32–126）", EXIT_USAGE)
    values = [ord(c) - 32 for c in text]
    checksum = (104 + sum((i + 1) * v for i, v in enumerate(values))) % 103
    sequence = [104] + values + [checksum] + [106]
    bars = []
    for code in sequence:
        pattern = CODE128[code]
        dark = True
        for width in pattern:
            bars.append((int(width), dark))
            dark = not dark
    quiet, scale, height = 10, ns.scale, ns.height
    total = sum(w for w, _ in bars) + 2 * quiet
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
             'viewBox="0 0 %d %d">' % (total * scale, height, total, height),
             '<rect width="%d" height="%d" fill="white"/>' % (total, height)]
    x = quiet
    for width, dark in bars:
        if dark:
            parts.append('<rect x="%d" y="0" width="%d" height="%d" fill="black"/>'
                         % (x, width, height))
        x += width
    parts.append("</svg>")
    svg = "\n".join(parts) + "\n"
    return deliver(ns, {"text": text, "modules": total, "checksum": checksum,
                        "format": "svg"}, svg)


def run_pv_qr_make(ns):
    try:
        import qrcode
    except ImportError:
        fail("缺可选依赖 qrcode：%s -m pip install qrcode[pil]（本技能不联网安装）"
             % sys.executable, EXIT_USAGE)
    if not ns.output:
        fail("请给 -o 输出路径", EXIT_USAGE)
    if ns.format == "svg":
        try:
            from qrcode.image.svg import SvgPathImage
        except ImportError:
            fail("SVG 后端不可用，请改用 --format png", EXIT_USAGE)
        img = qrcode.make(ns.text, image_factory=SvgPathImage, box_size=ns.size)
        p = unique_path(Path(ns.output).resolve())
        p.parent.mkdir(parents=True, exist_ok=True)
        img.save(str(p))
        return emit({"output": str(p), "format": "svg", "bytes": p.stat().st_size})
    img = qrcode.make(ns.text, box_size=ns.size)
    p = unique_path(Path(ns.output).resolve())
    p.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(p))
    return emit({"output": str(p), "format": "png", "bytes": p.stat().st_size})


def run_pv_qr_read(ns):
    decoded, failed, backend = [], [], None
    try:
        import cv2
        backend = "opencv-python"
        detector = cv2.QRCodeDetector()
        for raw in ns.input:
            try:
                img = cv2.imread(str(raw))
                if img is None:
                    failed.append({"file": str(raw), "error": "无法读取图片"})
                    continue
                value, _, _ = detector.detectAndDecode(img)
                decoded.append({"file": str(raw), "text": value or None})
            except Exception as exc:  # noqa: BLE001
                failed.append({"file": str(raw), "error": str(exc)})
    except ImportError:
        try:
            from pyzbar.pyzbar import decode as zdecode
            from PIL import Image
            backend = "pyzbar"
            for raw in ns.input:
                try:
                    items = zdecode(Image.open(str(raw)))
                    decoded.append({"file": str(raw),
                                    "text": [x.data.decode("utf-8", "replace") for x in items]})
                except Exception as exc:  # noqa: BLE001
                    failed.append({"file": str(raw), "error": str(exc)})
        except ImportError:
            fail("缺二维码识别后端：%s -m pip install opencv-python（或 pyzbar + pillow，"
                 "pyzbar 另需系统 zbar 动态库）" % sys.executable, EXIT_USAGE)
    return deliver(ns, {"backend": backend, "count": len(decoded),
                        "failed": failed, "results": decoded})
