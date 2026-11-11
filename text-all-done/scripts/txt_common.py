# -*- coding: utf-8 -*-
"""文本动作的共享层：编码嗅探、读写、路径守卫。

设计取舍：
- 编码探测**先 BOM，再严格 UTF-8，再 GB18030**。GB18030 是 GBK/GB2312 的超集，
  比逐个猜 GBK 更稳；港台繁体落到 BIG5；最后用 Latin-1 兜底（永不失败）。
- 判定"这是不是 UTF-8"必须用严格模式解码，不能用 errors="replace"，否则任何
  字节序列都能"解码成功"，探测就失去意义。
- 写文件时显式指定 newline=""，让调用方给出的 \\n / \\r\\n 原样落盘，避免
  Windows 上被再转换一次（本项目踩过 \\r\\r\\n 的坑）。
"""

import json
import os
import sys
from pathlib import Path

BOMS = [
    (b"\xef\xbb\xbf", "utf-8-sig"),
    (b"\xff\xfe\x00\x00", "utf-32-le"),
    (b"\x00\x00\xfe\xff", "utf-32-be"),
    (b"\xff\xfe", "utf-16-le"),
    (b"\xfe\xff", "utf-16-be"),
]

# 用户可写的编码别名 -> Python codec
ALIASES = {
    "utf8": "utf-8", "utf-8": "utf-8",
    "utf8bom": "utf-8-sig", "utf-8-bom": "utf-8-sig", "utf-8-sig": "utf-8-sig",
    "gbk": "gb18030", "gb2312": "gb18030", "gb18030": "gb18030",
    "big5": "big5", "big-5": "big5",
    "utf16": "utf-16", "utf-16": "utf-16",
    "utf-16le": "utf-16-le", "utf-16-le": "utf-16-le",
    "utf-16be": "utf-16-be", "utf-16-be": "utf-16-be",
    "latin1": "latin-1", "latin-1": "latin-1", "iso-8859-1": "latin-1",
    "ascii": "ascii",
}

CONTENT_TYPES = {
    ".json": "application/json",
    ".md": "text/markdown",
    ".html": "text/html",
    ".csv": "text/csv",
    ".srt": "text/plain",
}


def fail(message, code=2):
    """Print a one-line error and exit with the documented code."""
    print(message, file=sys.stderr)
    raise SystemExit(code)


def normalise_encoding(name):
    if not name:
        return None
    key = str(name).strip().lower()
    if key not in ALIASES:
        fail("不支持的编码：%s（可用：%s）"
             % (name, ", ".join(sorted(ALIASES))), 2)
    return ALIASES[key]


def sniff(data):
    """Return (encoding, text, bom_bytes). Raises SystemExit when undecodable."""
    for bom, encoding in BOMS:
        if data.startswith(bom):
            try:
                return encoding, data.decode(encoding), bom
            except UnicodeDecodeError:
                break
    for encoding in ("utf-8", "gb18030", "big5"):
        try:
            return encoding, data.decode(encoding), b""
        except UnicodeDecodeError:
            continue
    return "latin-1", data.decode("latin-1"), b""


def read_text(path, encoding=None, strict=False):
    """Read a text file. Returns (text, info-dict)."""
    path = Path(path)
    if not path.is_file():
        fail("输入不存在：%s" % path, 3)
    data = path.read_bytes()
    info = {"bytes": len(data), "bom": False}
    if encoding:
        codec = normalise_encoding(encoding)
        try:
            text = data.decode(codec)
        except UnicodeDecodeError as exc:
            if strict:
                fail("按 %s 解码失败：%s" % (codec, exc), 2)
            text, info["decode_error"] = data.decode(codec, "replace"), str(exc)
        info["encoding"] = codec
        info["bom"] = data.startswith(b"\xef\xbb\xbf")
    else:
        codec, text, bom = sniff(data)
        info["encoding"] = codec
        info["bom"] = bool(bom)
    info["lines"] = text.count("\n") + (1 if text and not text.endswith("\n") else 0)
    return text, info


def detect_newline(text):
    crlf = text.count("\r\n")
    stripped = text.replace("\r\n", "")
    cr = stripped.count("\r")
    lf = stripped.count("\n")
    if crlf >= lf and crlf >= cr and crlf:
        return "crlf"
    if cr > lf and cr:
        return "cr"
    return "lf"


def to_newline(text, style):
    style = (style or "keep").lower()
    if style == "keep":
        return text
    normalised = text.replace("\r\n", "\n").replace("\r", "\n")
    if style == "crlf":
        return normalised.replace("\n", "\r\n")
    if style == "cr":
        return normalised.replace("\n", "\r")
    return normalised


def guard_paths(source, target):
    source = Path(source).resolve()
    target = Path(target).resolve() if target else None
    if target is not None and source == target:
        fail("输出不能覆盖输入：%s" % target, 3)
    if target is not None and target.is_dir():
        fail("输出是目录，请给文件路径：%s" % target, 3)
    return source, target


def write_text(path, text, encoding="utf-8", newline="keep"):
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    codec = normalise_encoding(encoding) or "utf-8"
    body = to_newline(text, newline)
    with path.open("w", encoding=codec, newline="") as handle:
        handle.write(body)
    return path


def emit(payload, code=0):
    print(json.dumps(payload, ensure_ascii=False))
    return code


def derive_output(source, suffix):
    source = Path(source)
    return str(source.with_name(source.stem + suffix))


def human_bytes(size):
    for unit in ("B", "KB", "MB"):
        if size < 1024 or unit == "MB":
            return ("%d B" % size) if unit == "B" else ("%.1f %s" % (size, unit))
        size /= 1024.0


def iter_pairs(ns):
    """Shared --input/--output handling for single-file actions."""
    target = ns.output or derive_output(ns.input, "-out" + Path(ns.input).suffix)
    source, target = guard_paths(ns.input, target)
    return source, target


def main_guard():
    """Windows console default cp936 cannot print every glyph; keep output safe.

    被管道捕获时还要统一成 UTF-8——父进程按 UTF-8 解码 cp936 字节会得到替换符。
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            if stream.isatty():
                stream.reconfigure(errors="replace")
            else:
                stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001 - non-reconfigurable stream
            pass
