# -*- coding: utf-8 -*-
"""文件全搞定 · 共享层：路径守卫、扫描、哈希与 12 个动作的实现。

安全底线（与家族其它技能一致）：
- 绝不删除、绝不移动用户原文件；重命名与归类默认只出预览，--apply 才落盘。
- 输出不覆盖输入；产物重名自动避让；不跟随符号链接目录。
- 结果统一为一行 JSON；需要机器读取时用 -o 写文件。
"""
from __future__ import annotations

import csv
import fnmatch
import hashlib
import io
import json
import mimetypes
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

EXIT_USAGE = 2
EXIT_IO = 3
EXIT_FAIL = 5
EXIT_SAFETY = 7
MAX_SCAN = 20000

TYPE_MAP = {
    "document": {"pdf", "doc", "docx", "rtf", "odt", "txt", "md", "wps", "epub"},
    "spreadsheet": {"xls", "xlsx", "csv", "ods", "tsv"},
    "presentation": {"ppt", "pptx", "odp"},
    "image": {"png", "jpg", "jpeg", "gif", "bmp", "webp", "tif", "tiff", "svg", "heic"},
    "audio": {"mp3", "wav", "flac", "aac", "m4a", "ogg", "wma"},
    "video": {"mp4", "avi", "mkv", "mov", "wmv", "flv", "webm", "m4v"},
    "archive": {"zip", "tar", "gz", "bz2", "xz", "7z", "rar"},
    "data": {"json", "ndjson", "xml", "yaml", "yml", "toml", "sql", "db", "sqlite"},
    "code": {"py", "js", "ts", "java", "c", "cpp", "h", "go", "rs", "sh", "html", "css"},
}


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
    """产物重名自动避让：name-2.ext / name-3.ext（目录同理）。"""
    path = Path(path)
    if not path.exists():
        return path
    stem, suffix = path.stem, path.suffix
    for i in range(2, 10000):
        cand = path.with_name("%s-%d%s" % (stem, i, suffix))
        if not cand.exists():
            return cand
    fail("重名避让次数超限：%s" % path, EXIT_IO)


def brief(payload):
    keys = ("count", "entries", "groups", "files", "hits", "failed",
            "total_bytes", "planned", "applied", "ok", "mismatch", "missing")
    return {k: payload[k] for k in keys if k in payload and not isinstance(payload[k], (list, dict))}


def deliver(ns, payload, text=None):
    """无 -o 时打印一行 JSON；有 -o 时另存文件并打印路径摘要。"""
    out = getattr(ns, "output", None)
    if not out:
        return emit(payload)
    path = unique_path(Path(out).resolve())
    if text is not None and path.suffix.lower() != ".json":
        w(path, text)
    else:
        w(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    return emit({"output": str(path), "bytes": path.stat().st_size,
                 "summary": brief(payload)})


def human_bytes(size):
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return "%d B" % size if unit == "B" else "%.1f %s" % (size, unit)
        size /= 1024.0


def file_type(name):
    ext = Path(name).suffix.lower().lstrip(".")
    for kind, exts in TYPE_MAP.items():
        if ext in exts:
            return kind
    return "other"


def is_hidden(p):
    return any(part.startswith(".") for part in p.parts)


def scan(root, recursive=False, pattern="*", include_hidden=False, limit=0):
    """只读扫描，返回文件 Path 列表；不跟随符号链接目录，有安全上限。"""
    root = Path(root).resolve()
    if not root.exists():
        fail("输入不存在：%s" % root, EXIT_IO)
    found, truncated = [], False
    if root.is_file():
        return ([root], False) if fnmatch.fnmatch(root.name, pattern) else ([], False)
    if recursive:
        for base, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if include_hidden or not d.startswith(".")
                       and not (Path(base) / d).is_symlink()]
            for name in sorted(files):
                p = Path(base) / name
                if not include_hidden and (is_hidden(p.relative_to(root)) or name.startswith(".")):
                    continue
                if p.is_symlink() or not fnmatch.fnmatch(name, pattern):
                    continue
                found.append(p)
                if len(found) >= MAX_SCAN or (limit and len(found) >= limit):
                    truncated = True
                    break
            if truncated:
                break
    else:
        for p in sorted(root.iterdir()):
            if not p.is_file() or p.is_symlink():
                continue
            if not include_hidden and p.name.startswith("."):
                continue
            if fnmatch.fnmatch(p.name, pattern):
                found.append(p)
                if len(found) >= MAX_SCAN or (limit and len(found) >= limit):
                    truncated = True
                    break
    return found, truncated


def info(p, root=None):
    p = Path(p)
    st = p.stat()
    rel = str(p.relative_to(root)) if root and p.is_relative_to(root) else str(p)
    return {
        "path": rel.replace("\\", "/"),
        "size": st.st_size,
        "size_human": human_bytes(st.st_size),
        "ext": p.suffix.lower().lstrip("."),
        "type": file_type(p.name),
        "mime": mimetypes.guess_type(p.name)[0] or "application/octet-stream",
        "mtime": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        "mtime_ts": int(st.st_mtime),
        "mode": oct(st.st_mode & 0o777),
        "is_symlink": p.is_symlink(),
    }


def hash_file(path, algo="sha256"):
    h = hashlib.new(algo)
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def to_csv(rows, fields=None):
    buf = io.StringIO()
    fields = fields or (list(rows[0].keys()) if rows else ["path"])
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: row.get(k, "") for k in fields})
    return buf.getvalue()


def to_md(rows, fields=None):
    fields = fields or (list(rows[0].keys()) if rows else ["path"])
    lines = ["| " + " | ".join(fields) + " |",
             "|" + "|".join(["---"] * len(fields)) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(k, "")).replace("|", "\\|")
                                      for k in fields) + " |")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- 12 个动作

def run_file_list(ns):
    root = Path(ns.input).resolve()
    files, truncated = scan(root, ns.recursive, ns.pattern, ns.include_hidden, ns.limit)
    rows = [info(p, root) for p in files]
    reverse = ns.sort == "size" or ns.sort == "mtime"
    key = {"name": "path", "size": "size", "mtime": "mtime_ts"}[ns.sort]
    rows.sort(key=lambda r: r[key], reverse=reverse)
    if ns.limit:
        rows = rows[:ns.limit]
    by_type = {}
    for r in rows:
        by_type[r["type"]] = by_type.get(r["type"], 0) + 1
    payload = {
        "input": str(root), "count": len(rows),
        "total_bytes": sum(r["size"] for r in rows), "by_type": by_type,
        "truncated": truncated, "sort": ns.sort, "files": rows,
    }
    text = None
    if ns.format == "csv":
        text = to_csv(rows)
    elif ns.format == "md":
        text = to_md(rows, ["path", "size_human", "type", "mtime"])
    return deliver(ns, payload, text)


def run_file_tree(ns):
    root = Path(ns.input).resolve()
    if not root.is_dir():
        fail("输入不是目录：%s" % root, EXIT_IO)
    lines = [root.name + "/"]
    count, truncated = 0, False

    def walk(folder, prefix, depth):
        nonlocal count, truncated
        if depth > ns.depth:
            return
        try:
            entries = sorted(folder.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        except OSError:
            return
        if not ns.include_hidden:
            entries = [e for e in entries if not e.name.startswith(".")]
        for i, p in enumerate(entries):
            if count >= ns.max_entries:
                truncated = True
                return
            last = i == len(entries) - 1
            link = p.is_symlink()
            lines.append("%s%s %s%s" % (prefix, "└──" if last else "├──",
                                        p.name, "/ " if p.is_dir() else "") +
                         (" [symlink]" if link else ""))
            count += 1
            if p.is_dir() and not link:
                walk(p, prefix + ("    " if last else "│   "), depth + 1)
            if truncated:
                return

    walk(root, "", 1)
    return deliver(ns, {"input": str(root), "depth": ns.depth,
                        "entries": count, "truncated": truncated,
                        "lines": lines, "tree": "\n".join(lines)},
                   "\n".join(lines) + "\n")


def run_file_find(ns):
    root = Path(ns.input).resolve()
    pattern = ns.name or "*"
    files, truncated = scan(root, ns.recursive, pattern, False, ns.limit)
    exts = {e.strip().lower().lstrip(".") for e in (ns.ext or "").split(",") if e.strip()}
    now = datetime.now().timestamp()
    rows = []
    for p in files:
        d = info(p, root)
        if exts and d["ext"] not in exts:
            continue
        if ns.min_size and d["size"] < ns.min_size * 1024:
            continue
        if ns.max_size and d["size"] > ns.max_size * 1024:
            continue
        if ns.days and now - d["mtime_ts"] > ns.days * 86400:
            continue
        rows.append(d)
        if ns.limit and len(rows) >= ns.limit:
            truncated = True
            break
    return deliver(ns, {"input": str(root), "count": len(rows),
                        "truncated": truncated, "files": rows},
                   to_csv(rows) if getattr(ns, "output", None) and
                   Path(ns.output).suffix.lower() == ".csv" else None)


def run_file_rename(ns):
    root = Path(ns.input).resolve()
    if not root.is_dir():
        fail("输入不是目录：%s" % root, EXIT_IO)
    files, truncated = scan(root, ns.recursive, ns.pattern, False)
    if ns.replace:
        try:
            rx = re.compile(ns.replace)
        except re.error as exc:
            fail("正则无效：%s" % exc, EXIT_USAGE)
    else:
        rx = None
    used, plan = set(), []
    for i, p in enumerate(files):
        stem = rx.sub(ns.replacement, p.stem) if rx else p.stem
        if not stem.strip():
            stem = p.stem
        seq = str(ns.start + i) if ns.seq else ""
        name = ns.prefix + stem + seq + ns.suffix + p.suffix
        if "/" in name or "\\" in name:
            fail("新文件名含路径分隔符：%s" % name, EXIT_SAFETY)
        candidate = p.with_name(name)
        n = 2
        while (str(candidate) in used or (candidate.exists() and candidate != p)):
            candidate = p.with_name("%s-%d%s" % (Path(name).stem, n, Path(name).suffix))
            n += 1
        used.add(str(candidate))
        plan.append({"from": str(p.relative_to(root)).replace("\\", "/"),
                     "to": candidate.name, "changed": candidate != p})
    payload = {"input": str(root), "planned": len(plan),
               "apply": bool(ns.apply), "truncated": truncated, "plan": plan}
    if not ns.apply:
        return deliver(ns, payload)
    applied, failed = [], []
    for item in plan:
        src = root / item["from"]
        dst = src.with_name(item["to"])
        try:
            if src != dst:
                src.rename(unique_path(dst) if dst.exists() else dst)
            applied.append(item)
        except OSError as exc:
            failed.append({"file": item["from"], "error": str(exc)})
    map_path = unique_path(root / "rename-map.json")
    w(map_path, json.dumps({"applied": applied, "failed": failed},
                           ensure_ascii=False, indent=2) + "\n")
    payload.update({"applied": len(applied), "failed": failed,
                    "rename_map": str(map_path), "plan": applied})
    return deliver(ns, payload)


def run_file_organize(ns):
    root = Path(ns.input).resolve()
    if not root.is_dir():
        fail("输入不是目录：%s" % root, EXIT_IO)
    if not ns.output:
        fail("请给 -o 目标目录", EXIT_USAGE)
    target = Path(ns.output).resolve()
    if target == root or root in target.parents:
        fail("目标目录不能等于源目录或位于源目录内部：%s" % target, EXIT_IO)
    files, truncated = scan(root, ns.recursive, ns.pattern, False)
    plan = []
    for p in files:
        d = info(p, root)
        if ns.by == "ext":
            bucket = d["ext"] or "no-ext"
        elif ns.by == "type":
            bucket = d["type"]
        else:
            try:
                bucket = datetime.fromtimestamp(d["mtime_ts"]).strftime(ns.date_format)
            except ValueError:
                fail("日期格式无效：%s" % ns.date_format, EXIT_USAGE)
        rel = Path(d["path"])
        dest = target / bucket / rel.name
        plan.append({"from": d["path"], "to": str(dest.relative_to(target))})
    payload = {"input": str(root), "output": str(target), "by": ns.by,
               "planned": len(plan), "apply": bool(ns.apply),
               "truncated": truncated, "plan": plan}
    if not ns.apply:
        return emit(payload)  # -o 是目标目录，不能当结果文件写
    copied, failed = [], []
    for item in plan:
        src = root / item["from"]
        dst = target / item["to"]
        try:
            dst = unique_path(dst)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied.append({"from": item["from"], "to": str(dst)})
        except OSError as exc:
            failed.append({"file": item["from"], "error": str(exc)})
    payload.update({"applied": len(copied), "failed": failed, "plan": copied})
    return emit(payload)


def run_file_dedupe(ns):
    root = Path(ns.input).resolve()
    files, truncated = scan(root, ns.recursive, ns.pattern, False)
    by_size = {}
    for p in files:
        try:
            size = p.stat().st_size
        except OSError:
            continue
        if size >= ns.min_size:
            by_size.setdefault(size, []).append(p)
    groups, reclaimable, failed = [], 0, []
    for size, paths in by_size.items():
        if len(paths) < 2:
            continue
        by_hash = {}
        for p in paths:
            try:
                by_hash.setdefault(hash_file(p, ns.algo), []).append(p)
            except OSError as exc:
                failed.append({"file": str(p), "error": str(exc)})
        for digest, same in by_hash.items():
            if len(same) < 2:
                continue
            members = [str(p.relative_to(root)).replace("\\", "/") for p in same]
            reclaimable += size * (len(same) - 1)
            groups.append({"hash": digest, "size": size,
                           "count": len(same), "keep": members[0],
                           "files": members})
    groups.sort(key=lambda g: g["size"] * (g["count"] - 1), reverse=True)
    return deliver(ns, {"input": str(root), "algorithm": ns.algo,
                        "scanned": len(files), "groups": len(groups),
                        "duplicate_files": sum(g["count"] - 1 for g in groups),
                        "reclaimable_bytes": reclaimable,
                        "reclaimable_human": human_bytes(reclaimable),
                        "truncated": truncated, "failed": failed,
                        "duplicates": groups, "note": "只报告，不删除任何文件"})


def run_file_hash(ns):
    algo = ns.algo
    entries, failed = [], []
    for raw in ns.input:
        p = Path(raw).resolve()
        if not p.exists():
            failed.append({"file": str(p), "error": "不存在"})
            continue
        if p.is_file():
            paths = [p]
        else:
            paths, _ = scan(p, ns.recursive, ns.pattern, False)
        for f in paths:
            try:
                entries.append({"path": str(f), "size": f.stat().st_size,
                                "hash": hash_file(f, algo)})
            except OSError as exc:
                failed.append({"file": str(f), "error": str(exc)})
    return deliver(ns, {"algorithm": algo, "count": len(entries),
                        "failed": failed, "files": entries})


def run_file_verify(ns):
    src = Path(ns.input).resolve()
    if not src.is_file():
        fail("校验清单不存在：%s" % src, EXIT_IO)
    root = Path(ns.root).resolve() if ns.root else src.parent
    raw = src.read_text(encoding="utf-8-sig", errors="replace")
    items = []
    try:
        data = json.loads(raw)
        entries = data.get("files", data) if isinstance(data, dict) else data
        for e in entries:
            items.append((e.get("hash") or e.get("sha256"), e.get("path") or e.get("file")))
    except (ValueError, AttributeError):
        for line in raw.splitlines():
            parts = line.strip().split(None, 1)
            if len(parts) == 2:
                items.append((parts[0], parts[1].lstrip("*")))
    if not items:
        fail("清单里没有可校验的条目", EXIT_USAGE)
    ok, mismatch, missing = [], [], []
    for digest, rel in items:
        if not digest or not rel:
            continue
        p = Path(rel) if Path(rel).is_absolute() else root / rel
        if not p.is_file():
            missing.append(rel)
            continue
        try:
            actual = hash_file(p, ns.algo)
        except OSError as exc:
            missing.append("%s (%s)" % (rel, exc))
            continue
        (ok if actual.lower() == str(digest).lower() else mismatch).append(rel)
    return deliver(ns, {"checklist": str(src), "algorithm": ns.algo,
                        "total": len(items), "ok": len(ok),
                        "mismatch": len(mismatch), "missing": len(missing),
                        "mismatch_files": mismatch, "missing_files": missing})


def run_file_size(ns):
    root = Path(ns.input).resolve()
    files, truncated = scan(root, ns.recursive, "*", False)
    rows = [info(p, root) for p in files]
    total = sum(r["size"] for r in rows)
    empty = [r["path"] for r in rows if r["size"] == 0]
    by_ext, by_type = {}, {}
    for r in rows:
        key = r["ext"] or "no-ext"
        by_ext[key] = by_ext.get(key, 0) + r["size"]
        by_type[r["type"]] = by_type.get(r["type"], 0) + r["size"]
    big = [r for r in rows if r["size"] >= ns.min_mb * 1024 * 1024]
    big.sort(key=lambda r: r["size"], reverse=True)
    payload = {"input": str(root), "count": len(rows), "total_bytes": total,
               "total_human": human_bytes(total), "empty_files": empty,
               "by_ext": by_ext, "by_type": by_type, "truncated": truncated,
               "top": big[:ns.top]}
    if ns.empty_only:
        payload["top"] = []
    return deliver(ns, payload)


def run_file_compare(ns):
    left, right = Path(ns.left).resolve(), Path(ns.right).resolve()
    for p in (left, right):
        if not p.is_dir():
            fail("输入不是目录：%s" % p, EXIT_IO)
    lf, _ = scan(left, ns.recursive, "*", False)
    rf, _ = scan(right, ns.recursive, "*", False)
    lmap = {str(p.relative_to(left)).replace("\\", "/"): p for p in lf}
    rmap = {str(p.relative_to(right)).replace("\\", "/"): p for p in rf}
    only_left = sorted(set(lmap) - set(rmap))
    only_right = sorted(set(rmap) - set(lmap))
    different, same = [], []
    for rel in sorted(set(lmap) & set(rmap)):
        a, b = lmap[rel], rmap[rel]
        if a.stat().st_size != b.stat().st_size:
            different.append(rel)
        elif ns.hash and hash_file(a) != hash_file(b):
            different.append(rel)
        else:
            same.append(rel)
    return deliver(ns, {"left": str(left), "right": str(right),
                        "only_left": only_left, "only_right": only_right,
                        "different": different, "same_count": len(same),
                        "differences": len(only_left) + len(only_right) + len(different),
                        "identical": not (only_left or only_right or different)})


def run_file_metadata(ns):
    rows, failed = [], []
    for raw in ns.input:
        p = Path(raw).resolve()
        if not p.exists():
            failed.append({"file": str(p), "error": "不存在"})
            continue
        try:
            d = info(p)
            st = p.stat()
            d.update({"absolute": str(p), "is_dir": p.is_dir(),
                      "created": datetime.fromtimestamp(st.st_ctime).strftime("%Y-%m-%d %H:%M:%S"),
                      "accessed": datetime.fromtimestamp(st.st_atime).strftime("%Y-%m-%d %H:%M:%S")})
            rows.append(d)
        except OSError as exc:
            failed.append({"file": str(p), "error": str(exc)})
    return deliver(ns, {"count": len(rows), "failed": failed, "files": rows})


def run_file_copy(ns):
    if not ns.output:
        fail("请给 -o 目标目录", EXIT_USAGE)
    target = Path(ns.output).resolve()
    if target.is_file():
        fail("目标必须是目录：%s" % target, EXIT_IO)
    copied, failed = [], []
    for raw in ns.input:
        p = Path(raw).resolve()
        if not p.exists():
            failed.append({"file": str(p), "error": "不存在"})
            continue
        if p.is_file():
            pairs = [(p, target / p.name)]
        else:
            if target == p or p in target.parents:
                failed.append({"file": str(p), "error": "目标位于源目录内部"})
                continue
            files, _ = scan(p, ns.recursive, ns.pattern, False)
            pairs = [(f, target / p.name / f.relative_to(p)) for f in files]
        for src, dst in pairs:
            try:
                dst = unique_path(dst)
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                copied.append({"from": str(src), "to": str(dst)})
            except OSError as exc:
                failed.append({"file": str(src), "error": str(exc)})
    return emit({"output": str(target), "applied": len(copied),
                 "failed": failed, "files": copied})
