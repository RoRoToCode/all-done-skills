#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""压缩包全搞定 · 公共模块。

统一格式识别、成员读写、安全解压（zip-slip / tar-slip 防护）、冲突自动放行、
结果输出与退出码。仅依赖 Python 标准库即可完成全部 13 项动作；
pyzipper / py7zr / rarfile 为可选增强，缺失时自动降级而非中断。
"""
import bz2
import fnmatch
import gzip
import io
import lzma
import os
import stat
import struct
import sys
import tarfile
import tempfile
import time
import zipfile
import zlib
from collections import namedtuple

# Windows 控制台可能不是 UTF-8
for _stream in (sys.stdout, sys.stderr):
    try:
        if (_stream.encoding or "").lower().replace("-", "") != "utf8":
            _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

EXIT_USAGE = 2          # 用法错误 / 缺依赖
EXIT_IO = 3             # 输入输出错误（不存在、输出=输入、格式不支持）
EXIT_CORRUPT = 4        # 包损坏 / 校验失败
EXIT_FAIL = 5           # 动作失败
EXIT_PASSWORD = 6       # 缺密码 / 密码错误
EXIT_UNSAFE = 7         # 路径穿越等安全风险被拒绝


class ArchiveError(Exception):
    def __init__(self, msg, code=EXIT_FAIL):
        super().__init__(msg)
        self.code = code


class UnsafePath(ArchiveError):
    def __init__(self, msg):
        super().__init__(msg, EXIT_UNSAFE)


class PasswordError(ArchiveError):
    def __init__(self, msg):
        super().__init__(msg, EXIT_PASSWORD)


class MissingDependency(ArchiveError):
    def __init__(self, msg):
        super().__init__(msg, EXIT_USAGE)


def fail(msg, code=EXIT_FAIL):
    raise ArchiveError(msg, code)


Entry = namedtuple("Entry", "name size csize mtime is_dir encrypted crc")

FMT_ALIAS = {
    "zip": "zip", "jar": "zip",
    "tar": "tar",
    "tgz": "tgz", "tar.gz": "tgz", "tar-gz": "tgz", "gztar": "tgz",
    "tbz2": "tbz2", "tar.bz2": "tbz2", "tbz": "tbz2", "bztar": "tbz2",
    "txz": "txz", "tar.xz": "txz", "xztar": "txz",
    "gz": "gz", "gzip": "gz",
    "bz2": "bz2", "bzip2": "bz2",
    "xz": "xz", "lzma": "xz",
    "7z": "7z", "rar": "rar",
}
EXT_FMT = (
    (".tar.gz", "tgz"), (".tar.bz2", "tbz2"), (".tar.xz", "txz"),
    (".tgz", "tgz"), (".tbz2", "tbz2"), (".tbz", "tbz2"), (".txz", "txz"),
    (".zip", "zip"), (".jar", "zip"), (".tar", "tar"),
    (".gz", "gz"), (".bz2", "bz2"), (".xz", "xz"),
    (".7z", "7z"), (".rar", "rar"),
)
DEFAULT_EXT = {"zip": ".zip", "tar": ".tar", "tgz": ".tar.gz",
               "tbz2": ".tar.bz2", "txz": ".tar.xz", "gz": ".gz",
               "bz2": ".bz2", "xz": ".xz", "7z": ".7z", "rar": ".rar"}
TAR_FMTS = {"tar": "", "tgz": "gz", "tbz2": "bz2", "txz": "xz"}
SINGLE_FMTS = {"gz", "bz2", "xz"}
ARCHIVE_FMTS = {"zip", "tar", "tgz", "tbz2", "txz", "gz", "bz2", "xz", "7z", "rar"}
OPTIONAL_DEPS = ("pyzipper", "py7zr", "rarfile")


def normalize_fmt(value):
    key = (value or "").lower().strip().lstrip(".")
    if key not in FMT_ALIAS:
        fail("不支持的格式 %r；可用：%s"
             % (value, " ".join(sorted(set(FMT_ALIAS.values())))), EXIT_IO)
    return FMT_ALIAS[key]


def detect_format(path, default="zip"):
    low = str(path).lower()
    for ext, fmt in EXT_FMT:
        if low.endswith(ext):
            return fmt
    if low.endswith(".z") or low.endswith(".taz"):
        return "tgz"
    return default


def ext_for(fmt):
    return DEFAULT_EXT[normalize_fmt(fmt)]


def human(n):
    n = float(n or 0)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return "%.0f %s" % (n, unit) if unit == "B" else "%.1f %s" % (n, unit)
        n /= 1024


def now_dt():
    return time.localtime()[:6]


def dt_to_ts(dt):
    try:
        return time.mktime(tuple(dt) + (0, 0, -1))
    except Exception:
        return time.time()


def result(path, **fields):
    parts = []
    if path and os.path.isfile(path):
        parts.append("已保存 %s" % path)
        parts.append("体积=%s" % human(os.path.getsize(path)))
    elif path:
        parts.append("已输出 %s" % path)
    for k, v in fields.items():
        if v is not None and v != "":
            parts.append("%s=%s" % (k, v))
    print("  ".join(parts))


def ensure_parent(path):
    d = os.path.dirname(os.path.abspath(path))
    if d:
        os.makedirs(d, exist_ok=True)


def no_overwrite(inp, out):
    """输出不得等于/落在输入文件上。"""
    if inp and out and os.path.abspath(inp) == os.path.abspath(out):
        fail("输出不得等于输入：%s" % inp, EXIT_IO)


def need_exists(path):
    if not path or not os.path.exists(path):
        fail("输入不存在：%s" % path, EXIT_IO)
    return path


def safe_name(name, strip=0):
    """规范化归档内路径：拒绝绝对路径、盘符、.. 越界；返回 POSIX 风格相对路径。"""
    raw = str(name).replace("\\", "/")
    if raw.startswith("/") or raw.startswith("//"):
        raise UnsafePath("归档内绝对路径被拒绝：%s" % name)
    if len(raw) > 1 and raw[1] == ":":
        raise UnsafePath("归档内盘符路径被拒绝：%s" % name)
    parts = []
    for seg in raw.split("/"):
        if seg in ("", "."):
            continue
        if seg == "..":
            raise UnsafePath("归档内路径越界（..）被拒绝：%s" % name)
        parts.append(seg)
    if strip:
        parts = parts[int(strip):]
    if not parts:
        return ""
    return "/".join(parts)


def safe_target(outdir, name, strip=0):
    rel = safe_name(name, strip)
    if not rel:
        return None
    base = os.path.abspath(outdir)
    target = os.path.abspath(os.path.join(base, *rel.split("/")))
    if os.path.commonpath([base, target]) != base:
        raise UnsafePath("解压目标越出输出目录：%s" % name)
    return target


def conflict_path(target, mode="rename"):
    """默认无需逐项确认：自动改名，不逐项询问；overwrite / skip 可选。"""
    if not os.path.exists(target) or mode == "overwrite":
        return target
    if mode == "skip":
        return None
    stem, ext = os.path.splitext(target)
    i = 2
    while os.path.exists("%s (%d)%s" % (stem, i, ext)):
        i += 1
    return "%s (%d)%s" % (stem, i, ext)


def dep_available(name):
    try:
        __import__(name)
        return True
    except Exception:
        return False


def password_bytes(password):
    return password.encode("utf-8") if password else None


def _entry(name, data, mtime=None, encrypted=False, crc=None, is_dir=False):
    data = data or b""
    return Entry(name, len(data), len(data), mtime or now_dt(),
                 is_dir, encrypted,
                 zlib.crc32(data) & 0xFFFFFFFF if crc is None else crc)


# ---------------------------------------------------------------------------
# 读取：所有格式统一产出 (Entry, bytes|None)
# ---------------------------------------------------------------------------
def read_members(path, fmt=None, password=None, allow_links=False):
    fmt = normalize_fmt(fmt) if fmt else detect_format(path)
    pwd = password_bytes(password)
    need_exists(path)

    if fmt == "7z":
        if not dep_available("py7zr"):
            raise MissingDependency(
                "读取 7z 需要 py7zr：pip install py7zr（或用 arc-convert 先转成 zip）")
        import py7zr
        # py7zr 1.x 移除了 readall()/read()，只能先解到临时目录再逐个读。
        with tempfile.TemporaryDirectory(prefix="arc7z_") as tmp:
            with py7zr.SevenZipFile(path, "r", password=password) as z:
                names = z.getnames()
                z.extractall(path=tmp)
            for name in names:
                full = os.path.join(tmp, name.replace("/", os.sep))
                if name.endswith("/") or not os.path.isfile(full):
                    yield _entry(name, b""), None
                    continue
                with open(full, "rb") as f:
                    data = f.read()
                yield _entry(name, data), data
        return

    if fmt == "rar":
        if not dep_available("rarfile"):
            raise MissingDependency(
                "读取 rar 需要 rarfile + unrar 二进制：pip install rarfile")
        import rarfile
        with rarfile.RarFile(path) as r:
            for info in r.infolist():
                if info.isdir():
                    yield _entry(info.filename, b"", is_dir=True), None
                    continue
                data = r.read(info, pwd=password)
                yield _entry(info.filename, data), data
        return

    if fmt in SINGLE_FMTS:
        opener = {"gz": gzip.open, "bz2": bz2.open, "xz": lzma.open}[fmt]
        with opener(path, "rb") as f:
            data = f.read()
        base = os.path.basename(path)
        for ext, _ in EXT_FMT:
            if base.lower().endswith(ext):
                base = base[:-len(ext)]
                break
        yield _entry(base or "data", data), data
        return

    if fmt in TAR_FMTS:
        with tarfile.open(path, "r:" + (TAR_FMTS[fmt] or "*")) as t:
            for m in t:
                if m.isdir():
                    yield _entry(m.name, b"", _dt(m.mtime), is_dir=True), None
                    continue
                if m.issym() or m.islnk() or not (m.isfile() or m.isreg()):
                    if allow_links:
                        continue
                    sys.stderr.write("跳过不安全链接条目：%s\n" % m.name)
                    continue
                f = t.extractfile(m)
                data = f.read() if f else b""
                yield _entry(m.name, data, _dt(m.mtime)), data
        return

    # zip：AES 加密的包标准库解不开（报 "That compression method is not
    # supported"），有密码且装了 pyzipper 时改用 pyzipper 打开。
    if pwd and dep_available("pyzipper"):
        import pyzipper
        zctx = pyzipper.AESZipFile(path, "r")
        zctx.setpassword(pwd)
    else:
        zctx = zipfile.ZipFile(path)
    with zctx as z:
        for info in z.infolist():
            enc = bool(info.flag_bits & 0x1)
            if enc and not pwd:
                raise PasswordError("压缩包已加密，需要 --password")
            if info.is_dir():
                yield _entry(info.filename, b"", info.date_time, is_dir=True), None
                continue
            try:
                data = z.read(info, pwd=pwd)
            except RuntimeError as exc:
                raise PasswordError("密码错误或条目损坏：%s" % exc)
            except Exception as exc:
                fail("读取条目失败 %s：%s" % (info.filename, exc), EXIT_CORRUPT)
            e = _entry(info.filename, data, info.date_time, enc, info.CRC)
            yield e._replace(csize=info.compress_size), data


def _dt(ts):
    try:
        return time.localtime(ts)[:6]
    except Exception:
        return now_dt()


def list_entries(path, fmt=None, password=None, allow_links=False):
    return [e for e, _ in read_members(path, fmt, password, allow_links)]


# ---------------------------------------------------------------------------
# 写入
# ---------------------------------------------------------------------------
def write_members(out, members, fmt="zip", level=6, comment="",
                  password=None, force_fmt=None):
    fmt = normalize_fmt(force_fmt or fmt or detect_format(out))
    no_overwrite(None, out)
    ensure_parent(out)
    members = list(members)
    level = max(1, min(9, int(level or 6)))

    if fmt == "7z":
        if not dep_available("py7zr"):
            raise MissingDependency("写入 7z 需要 py7zr：pip install py7zr")
        import py7zr
        kw = {"password": password} if password else {}
        with py7zr.SevenZipFile(out, "w", **kw) as z:
            for e, data in members:
                if e.is_dir:
                    continue
                z.writef(io.BytesIO(data or b""), safe_name(e.name))
        return out

    if fmt == "rar":
        fail("rar 为只读格式（无开源写入器）；请改用 zip / 7z / tar.*", EXIT_IO)

    if fmt in SINGLE_FMTS:
        files = [(e, d) for e, d in members if not e.is_dir]
        if len(files) != 1:
            fail("单文件压缩格式 %s 只能装 1 个文件（当前 %d 个），请改用 zip / tar.*"
                 % (fmt, len(files)), EXIT_IO)
        e, data = files[0]
        opener = {"gz": gzip.open, "bz2": bz2.open, "xz": lzma.open}[fmt]
        with opener(out, "wb") as f:
            f.write(data or b"")
        return out

    if fmt in TAR_FMTS:
        mode = "w" + (":" + TAR_FMTS[fmt] if TAR_FMTS[fmt] else "")
        kw = {"compresslevel": level} if TAR_FMTS[fmt] == "gz" else {}
        with tarfile.open(out, mode, **kw) as t:
            for e, data in members:
                name = safe_name(e.name)
                if not name:
                    continue
                info = tarfile.TarInfo(name)
                info.mtime = int(dt_to_ts(e.mtime))
                if e.is_dir:
                    info.type = tarfile.DIRTYPE
                    info.mode = 0o755
                    t.addfile(info)
                else:
                    data = data or b""
                    info.size = len(data)
                    info.mode = 0o644
                    t.addfile(info, io.BytesIO(data))
        return out

    if password:
        if dep_available("pyzipper"):
            _write_aes_zip(out, members, level, comment, password)
        else:
            _write_zipcrypto(out, members, level, comment, password)
        return out

    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=level, allowZip64=True) as z:
        for e, data in members:
            name = safe_name(e.name)
            if not name:
                continue
            zi = zipfile.ZipInfo(name + ("/" if e.is_dir and not name.endswith("/") else ""),
                                 e.mtime or now_dt())
            if e.is_dir:
                zi.compress_type = zipfile.ZIP_STORED
                zi.external_attr = (0o40755 << 16) | 0x10
                z.writestr(zi, b"")
            else:
                zi.compress_type = zipfile.ZIP_DEFLATED
                zi.external_attr = 0o100644 << 16
                z.writestr(zi, data or b"")
        if comment:
            z.comment = comment.encode("utf-8")
    return out


def _write_aes_zip(out, members, level, comment, password):
    import pyzipper
    # pyzipper 0.4 起 AESZipFile 直接把参数透传给 zipfile.ZipFile，
    # 不再接受 nbits；WZ_AES 本身就是 AES-256，不需要显式指定密钥位数。
    with pyzipper.AESZipFile(out, "w", compression=zipfile.ZIP_DEFLATED,
                             compresslevel=level, encryption=pyzipper.WZ_AES) as z:
        z.setpassword(password.encode("utf-8"))
        for e, data in members:
            name = safe_name(e.name)
            if not name or e.is_dir:
                continue
            z.writestr(name, data or b"")
        if comment:
            z.comment = comment.encode("utf-8")


# --- 纯标准库 ZipCrypto 写入（传统 PKZIP 加密；弱加密，仅防误看） ----------
def _crc_table():
    tbl = []
    for i in range(256):
        c = i
        for _ in range(8):
            c = (c >> 1) ^ (0xEDB88320 if c & 1 else 0)
        tbl.append(c)
    return tbl


_CRC_TABLE = _crc_table()


def _crc_byte(ch, crc):
    return (crc >> 8) ^ _CRC_TABLE[(crc ^ ch) & 0xFF]


class _ZipCrypto:
    def __init__(self, pwd):
        self.k = [0x12345678, 0x23456789, 0x34567890]
        for b in pwd:
            self._update(b)

    def _update(self, b):
        self.k[0] = _crc_byte(b, self.k[0])
        self.k[1] = (self.k[1] + (self.k[0] & 0xFF)) & 0xFFFFFFFF
        self.k[1] = (self.k[1] * 134775813 + 1) & 0xFFFFFFFF
        self.k[2] = _crc_byte(self.k[1] >> 24, self.k[2])

    def _stream_byte(self):
        t = (self.k[2] | 2) & 0xFFFF
        return ((t * (t ^ 1)) >> 8) & 0xFF

    def encrypt(self, data):
        out = bytearray()
        for b in data:
            out.append(b ^ self._stream_byte())
            self._update(b)
        return bytes(out)


def _dos(dt):
    y, mo, d, h, mi, s = (list(dt) + [0] * 6)[:6]
    y = max(1980, min(2107, int(y)))
    return (((int(h) << 11) | (int(mi) << 5) | (int(s) // 2)),
            ((y - 1980) << 9) | (int(mo) << 5) | int(d))


def _write_zipcrypto(out, members, level, comment, password):
    pwd = password.encode("utf-8")
    items = [(safe_name(e.name), (data or b""), e.mtime or now_dt())
             for e, data in members if not e.is_dir and safe_name(e.name)]
    if not items:
        fail("加密压缩包里没有可写入的文件", EXIT_IO)
    central, count = [], 0
    with open(out, "wb") as f:
        for name, raw, dt in items:
            nameb = name.encode("utf-8")
            crc = zlib.crc32(raw) & 0xFFFFFFFF
            co = zlib.compressobj(level, zlib.DEFLATED, -15)
            payload = co.compress(raw) + co.flush()
            crypto = _ZipCrypto(pwd)
            header = os.urandom(11) + bytes([(crc >> 24) & 0xFF])
            enc = crypto.encrypt(header) + crypto.encrypt(payload)
            method, csize, usize = 8, len(enc), len(raw)
            flags = 0x1 | 0x800
            dost, dosd = _dos(dt)
            offset = f.tell()
            f.write(struct.pack("<IHHHHHIIIHH", 0x04034B50, 20, flags, method,
                                dost, dosd, crc, csize, usize, len(nameb), 0))
            f.write(nameb)
            f.write(enc)
            central.append(struct.pack(
                "<IHHHHHHIIIHHHHHII", 0x02014B50, 20, 20, flags, method,
                dost, dosd, crc, csize, usize, len(nameb), 0, 0, 0, 0,
                0o100644 << 16, offset) + nameb)
            count += 1
        cd_offset = f.tell()
        for rec in central:
            f.write(rec)
        cd_size = f.tell() - cd_offset
        cb = (comment or "").encode("utf-8")
        f.write(struct.pack("<IHHHHIIH", 0x06054B50, 0, 0, count, count,
                            cd_size, cd_offset, len(cb)) + cb)
    return out


# ---------------------------------------------------------------------------
# 收集输入 / 解压 / 统计
# ---------------------------------------------------------------------------
def collect_paths(inputs, base=None, excludes=None):
    """把文件/目录展开成 [(归档名, 绝对路径, 是否目录)]。"""
    excludes = excludes or []
    out = []
    root = os.path.abspath(base) if base else None
    for raw in inputs:
        p = os.path.abspath(raw)
        need_exists(p)
        top = os.path.basename(p.rstrip(os.sep)) or "root"
        if os.path.isfile(p):
            name = os.path.relpath(p, root).replace(os.sep, "/") if root else top
            if _excluded(name, excludes):
                continue
            out.append((safe_name(name), p, False))
            continue
        for dirpath, dirnames, filenames in os.walk(p):
            dirnames[:] = [d for d in dirnames if not _excluded(d, excludes)]
            anchor = root if root else os.path.dirname(p)
            rel_dir = os.path.relpath(dirpath, anchor).replace(os.sep, "/")
            if rel_dir == ".." or rel_dir.startswith("../"):
                rel_dir = os.path.relpath(dirpath, os.path.dirname(p)).replace(os.sep, "/")
            full_dir = "" if rel_dir == "." else rel_dir
            if not filenames and not dirnames and full_dir:
                out.append((safe_name(full_dir), dirpath, True))
            for fn in sorted(filenames):
                rel = "/".join(x for x in (full_dir, fn) if x)
                if _excluded(rel, excludes) or _excluded(fn, excludes):
                    continue
                out.append((safe_name(rel), os.path.join(dirpath, fn), False))
    if not out:
        fail("没有可打包的文件（检查路径与 --exclude）", EXIT_IO)
    return out


def _excluded(rel, patterns):
    return any(fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(
        os.path.basename(rel), pat) for pat in patterns)


def files_to_members(items):
    for name, path, is_dir in items:
        if is_dir:
            yield _entry(name, b"", is_dir=True), None
            continue
        with open(path, "rb") as f:
            data = f.read()
        yield _entry(name, data, _dt(os.path.getmtime(path))), data


def extract_archive(path, outdir, fmt=None, password=None, members=None,
                    strip=0, on_conflict="rename", allow_links=False):
    """安全解压：逐条校验路径、自动改名放行、返回 (写入数, 跳过数)。"""
    os.makedirs(outdir, exist_ok=True)
    written = skipped = 0
    pats = members or []
    for e, data in read_members(path, fmt, password, allow_links):
        if pats and not any(fnmatch.fnmatch(e.name, p) for p in pats):
            continue
        target = safe_target(outdir, e.name, strip)
        if not target:
            continue
        if e.is_dir:
            os.makedirs(target, exist_ok=True)
            continue
        target = conflict_path(target, on_conflict)
        if target is None:
            skipped += 1
            continue
        ensure_parent(target)
        with open(target, "wb") as f:
            f.write(data or b"")
        written += 1
    return written, skipped


def archive_info(path, fmt=None, password=None):
    fmt = normalize_fmt(fmt) if fmt else detect_format(path)
    need_exists(path)
    entries = list_entries(path, fmt, password)
    usize = sum(e.size for e in entries if not e.is_dir)
    csize = os.path.getsize(path)
    enc = any(e.encrypted for e in entries)
    comment = ""
    if fmt == "zip":
        try:
            with zipfile.ZipFile(path) as z:
                comment = z.comment.decode("utf-8", "replace")
                enc = enc or any(i.flag_bits & 0x1 for i in z.infolist())
        except Exception:
            pass
    return {"path": path, "format": fmt, "entries": len(entries),
            "files": sum(1 for e in entries if not e.is_dir),
            "dirs": sum(1 for e in entries if e.is_dir),
            "original": usize, "packed": csize,
            "ratio": (100.0 * (1 - csize / usize)) if usize else 0.0,
            "encrypted": enc, "comment": comment, "entries_detail": entries}


def print_entries(entries, limit=None):
    print("%-6s %-12s %-12s %-19s %s" %
          ("序号", "原始", "压缩后", "修改时间", "路径"))
    shown = entries if not limit else entries[:limit]
    for i, e in enumerate(shown, 1):
        ts = "%04d-%02d-%02d %02d:%02d:%02d" % tuple(
            (list(e.mtime) + [0] * 6)[:6])
        print("%-6d %-12s %-12s %-19s %s%s" %
              (i, human(e.size), "-" if e.is_dir else human(e.csize), ts,
               e.name, "  [目录]" if e.is_dir else ("  [加密]" if e.encrypted else "")))
    if limit and len(entries) > limit:
        print("... 另有 %d 条，用 --limit 0 查看全部" % (len(entries) - limit))


def check_deps():
    print("依赖检查（标准库：zipfile / tarfile / gzip / bz2 / lzma，全部内置）：")
    print("  [已装] stdlib (zip / tar / gz / bz2 / xz 读写)")
    for d in OPTIONAL_DEPS:
        print("  [%s] %-10s %s" % ("已装" if dep_available(d) else "缺失", d,
                                   {"pyzipper": "AES-256 加密 zip（缺失时降级为 ZipCrypto）",
                                    "py7zr": "7z 读写（缺失时 7z 动作给出安装提示）",
                                    "rarfile": "rar 只读（还需 unrar 二进制）"}[d]))
    return 0
