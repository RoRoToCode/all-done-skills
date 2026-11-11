#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""web-capture shared runtime.

Standard library only. Provides: URL/source loading with charset sniffing,
robots.txt handling, output-job bookkeeping, Edge/Chrome headless discovery,
and a tiny CDP (DevTools Protocol) client for full-page screenshots and PDF.

Nothing here uploads data anywhere: HTTP GET is issued only to the URL the
user supplied (and its robots.txt / page resources when explicitly asked).
"""
from __future__ import annotations

import argparse
import base64
import datetime as _dt
import gzip
import hashlib
import json
import os
import re
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
import zlib
from dataclasses import dataclass, field
from pathlib import Path

VERSION = "1.2.1"
DEFAULT_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 web-capture/1.0")
DEFAULT_TIMEOUT = 20
MAX_BODY = 12 * 1024 * 1024
MAX_RESOURCE = 3 * 1024 * 1024
SAFE_HEADERS = {"content-type", "content-length", "last-modified", "etag",
                "server", "location", "content-language", "date"}

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


class WebError(Exception):
    """A user-facing, recoverable failure (message is safe to print)."""


def is_url(value: str) -> bool:
    return bool(re.match(r"^(https?|file)://", str(value).strip(), re.I))


def stem_for(src: str) -> str:
    """Turn a URL or local path into a safe file name stem."""
    value = str(src).strip()
    if is_url(value):
        parts = urllib.parse.urlsplit(value)
        raw = "_".join(x for x in (parts.netloc, parts.path.strip("/")) if x)
        raw = urllib.parse.unquote(raw)
    else:
        raw = Path(value).stem or "page"
    raw = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff._-]+", "-", raw).strip("-.")
    return (raw or "page")[:80]


def normalize_url(url: str, base: str | None = None) -> str:
    url = (url or "").strip()
    if base and not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", url):
        url = urllib.parse.urljoin(base, url)
    p = urllib.parse.urlsplit(url)
    if p.scheme.lower() not in ("http", "https") or not p.netloc:
        return ""
    path = p.path or "/"
    return urllib.parse.urlunsplit((p.scheme.lower(), p.netloc.lower(), path,
                                    p.query, ""))


def same_origin(a: str, b: str) -> bool:
    pa, pb = urllib.parse.urlsplit(a), urllib.parse.urlsplit(b)
    return (pa.scheme.lower(), pa.netloc.lower()) == (pb.scheme.lower(), pb.netloc.lower())


def absolute(src: str, base: str) -> str:
    try:
        return urllib.parse.urljoin(base, src)
    except ValueError:
        return ""


def file_uri(path: Path) -> str:
    return path.resolve().as_uri()


@dataclass
class Source:
    requested: str
    url: str                      # final URL (after redirects) or file:// URI
    status: int
    headers: dict
    body: bytes
    text: str
    encoding: str
    local: bool
    elapsed_ms: int = 0
    warnings: list = field(default_factory=list)


def decode_body(body: bytes, headers: dict | None = None) -> tuple[str, str]:
    """Charset: HTTP header -> BOM -> <meta charset> -> utf-8 -> gb18030/latin1."""
    headers = headers or {}
    ctype = str(headers.get("content-type", ""))
    m = re.search(r"charset\s*=\s*['\"]?([A-Za-z0-9_.:-]+)", ctype, re.I)
    candidates = []
    if m:
        candidates.append(m.group(1))
    head = body[:4096]
    if head.startswith(b"\xef\xbb\xbf"):
        candidates.insert(0, "utf-8-sig")
    elif head.startswith((b"\xff\xfe", b"\xfe\xff")):
        candidates.insert(0, "utf-16")
    m2 = re.search(rb"<meta[^>]+charset\s*=\s*['\"]?\s*([A-Za-z0-9_.:-]+)",
                   head, re.I)
    if m2:
        candidates.append(m2.group(1).decode("ascii", "replace"))
    candidates += ["utf-8", "gb18030", "big5", "latin-1"]
    seen, errors = set(), []
    for codec in candidates:
        key = codec.lower().replace("_", "-")
        if key in seen:
            continue
        seen.add(key)
        try:
            text = body.decode(codec)
            return text, codec
        except (UnicodeDecodeError, LookupError) as exc:
            errors.append("%s: %s" % (codec, exc))
    return body.decode("utf-8", "replace"), "utf-8/replace"


def _decompress(body: bytes, encoding: str) -> bytes:
    encoding = (encoding or "").lower()
    try:
        if encoding == "gzip":
            return gzip.decompress(body)
        if encoding == "deflate":
            try:
                return zlib.decompress(body)
            except zlib.error:
                return zlib.decompress(body, -zlib.MAX_WBITS)
    except (OSError, zlib.error):
        return body
    return body


def fetch(url: str, *, timeout: float = DEFAULT_TIMEOUT, ua: str = DEFAULT_UA,
          max_bytes: int = MAX_BODY, respect_robots: bool = True) -> Source:
    """GET a public URL. Honours robots.txt by default."""
    clean = normalize_url(url)
    if not clean:
        raise WebError("不是可用的 http(s) 网址: %s" % url)
    allowed, note = robots_check(clean, ua, timeout, respect_robots)
    if not allowed:
        raise WebError("robots.txt 不允许抓取该地址（%s）；确需抓取请显式加 --no-robots" % note)
    req = urllib.request.Request(clean, headers={
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate",
    })
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(max_bytes + 1)
            headers = {k.lower(): v for k, v in resp.headers.items()}
            status, final = resp.status, resp.geturl()
    except urllib.error.HTTPError as exc:
        raise WebError("HTTP %s %s: %s" % (exc.code, exc.reason, clean)) from exc
    except (urllib.error.URLError, socket.timeout, TimeoutError) as exc:
        raise WebError("请求失败: %s (%s)" % (clean, getattr(exc, "reason", exc))) from exc
    warnings = []
    if len(body) > max_bytes:
        body = body[:max_bytes]
        warnings.append("响应超过 %d 字节，已截断" % max_bytes)
    body = _decompress(body, headers.get("content-encoding", ""))
    if "unavailable" in note or note.startswith("robots.txt HTTP"):
        warnings.append(note)
    text, codec = decode_body(body, headers)
    safe_headers = {k: v for k, v in headers.items() if k in SAFE_HEADERS}
    return Source(clean, final, status, safe_headers, body, text, codec,
                  False, int((time.time() - started) * 1000), warnings)


def load_source(src: str, *, timeout: float = DEFAULT_TIMEOUT,
                ua: str = DEFAULT_UA, respect_robots: bool = True) -> Source:
    """Load from http(s) URL, file:// URL or a local HTML/text file."""
    value = str(src).strip()
    if value.lower().startswith("file://"):
        p = urllib.parse.urlsplit(value)
        raw = urllib.parse.unquote(p.path.lstrip("/") if not re.match(r"^/[A-Za-z]:", p.path)
                                   else p.path[1:])
        value = raw
    if is_url(value):
        return fetch(value, timeout=timeout, ua=ua, respect_robots=respect_robots)
    path = Path(value).expanduser()
    if not path.is_file():
        raise WebError("找不到输入文件: %s" % path)
    body = path.read_bytes()
    text, codec = decode_body(body, {})
    return Source(value, file_uri(path), 200, {"content-length": str(len(body))},
                  body, text, codec, True, 0, [])


_ROBOTS_CACHE: dict = {}


def robots_check(url: str, ua: str, timeout: float, respect: bool = True) -> tuple[bool, str]:
    """Return (allowed, note). Fetching robots.txt itself never needs consent."""
    if not respect:
        return True, "robots disabled"
    p = urllib.parse.urlsplit(url)
    root = "%s://%s" % (p.scheme, p.netloc)
    if root not in _ROBOTS_CACHE:
        rp = urllib.robotparser.RobotFileParser()
        note = ""
        try:
            req = urllib.request.Request(root + "/robots.txt",
                                         headers={"User-Agent": ua})
            with urllib.request.urlopen(req, timeout=min(timeout, 8)) as resp:
                raw = resp.read(256 * 1024)
            rp.parse(raw.decode("utf-8", "replace").splitlines())
            note = "robots.txt loaded"
        except urllib.error.HTTPError as exc:
            rp.parse([])              # 404 / 403 => treat as no restrictions
            note = "robots.txt HTTP %s" % exc.code
        except Exception as exc:
            rp.parse([])
            note = "robots.txt unavailable (%s)" % type(exc).__name__
        _ROBOTS_CACHE[root] = (rp, note)
    rp, note = _ROBOTS_CACHE[root]
    try:
        ok = rp.can_fetch(ua, url)
    except Exception:
        ok = True
    delay = None
    try:
        delay = rp.crawl_delay(ua)
    except Exception:
        pass
    return ok, ("%s; crawl-delay=%s" % (note, delay)) if delay else note


def guard_url(src: str, ua: str, timeout: float, respect: bool = True) -> str:
    """Robots gate for the browser-render actions (which bypass fetch()).

    Local files and non-http sources are always allowed. Returns a note.
    """
    if not is_url(src) or not str(src).lower().startswith("http"):
        return ""
    url = normalize_url(src)
    allowed, note = robots_check(url, ua, timeout, respect)
    if not allowed:
        raise WebError("robots.txt 不允许抓取该地址（%s）；确需抓取请显式加 --no-robots" % note)
    return note


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def utcnow() -> str:
    return _dt.datetime.now().astimezone().isoformat(timespec="seconds")


def dump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2, default=str) + "\n"


def print_json(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, default=str))


def unique_outdir(path) -> Path:
    """Never overwrite a previous run: an output dir holding manifest.json is
    retired automatically and the new run goes to `<name>-2`, `-3`, ...

    This is the "hands-free" contract: rerunning the same command needs no
    prompt and cannot silently destroy earlier captures.
    """
    requested = Path(path).expanduser().resolve()
    if not (requested / "manifest.json").exists():
        return requested
    for i in range(2, 51):
        alt = requested.with_name(requested.name + "-%d" % i)
        if not (alt / "manifest.json").exists():
            return alt
    return requested.with_name(requested.name + "-" + str(int(time.time())))


def die(msg: str, code: int = 1, hint: str = ""):
    print_json({"ok": False, "error": msg, "hint": hint})
    return code


class Job:
    """One output directory + manifest + warnings, shared by every action."""

    def __init__(self, action: str, src: str, out: str, args=None):
        self.action = action
        self.src = str(src)
        self.args = args or argparse.Namespace()
        self.warnings: list[str] = []
        self.files: list[str] = []
        requested = Path(out).expanduser().resolve()
        self.out = unique_outdir(out)
        if self.out != requested:
            self.warnings.append("输出目录已有产物，自动避让到 %s" % self.out.name)
        if not is_url(self.src):
            inp = Path(self.src).expanduser().resolve()
            if self.out == inp or (inp.is_file() and self.out == inp.parent):
                raise WebError("输出目录与输入路径冲突，拒绝覆盖输入: %s" % inp)
        if self.out.exists() and not self.out.is_dir():
            raise WebError("输出路径已存在且不是目录: %s" % self.out)
        self.out.mkdir(parents=True, exist_ok=True)

    def load(self) -> Source:
        s = load_source(self.src, timeout=float(getattr(self.args, "timeout", DEFAULT_TIMEOUT)),
                        ua=getattr(self.args, "ua", DEFAULT_UA),
                        respect_robots=not getattr(self.args, "no_robots", False))
        self.warnings.extend(s.warnings)
        return s

    def write(self, name: str, data) -> Path:
        path = self.out / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(data, bytes):
            path.write_bytes(data)
        elif isinstance(data, str):
            path.write_text(data, encoding="utf-8")
        else:
            path.write_text(dump(data), encoding="utf-8")
        self.files.append(name)
        return path

    def json(self, name: str, obj) -> Path:
        return self.write(name, dump(obj))

    def csv(self, name: str, rows: list[list]) -> Path:
        import csv
        import io
        buf = io.StringIO(newline="")
        w = csv.writer(buf)
        w.writerows(rows)
        # UTF-8 BOM so Excel opens Chinese without mojibake
        return self.write(name, "\ufeff" + buf.getvalue())

    def meta(self, source: Source) -> dict:
        return {
            "requested": source.requested,
            "final_url": source.url,
            "status": source.status,
            "encoding": source.encoding,
            "bytes": len(source.body),
            "sha256": sha256(source.body),
            "elapsed_ms": source.elapsed_ms,
            "local": source.local,
            "fetched_at": utcnow(),
            "headers": source.headers,
        }

    def finish(self, **extra) -> int:
        payload = {"skill": "web-capture", "version": VERSION,
                   "action": self.action, "source": self.src,
                   "output": str(self.out), "generated_at": utcnow(),
                   "files": self.files, "warnings": self.warnings}
        payload.update(extra)
        self.json("manifest.json", payload)
        print_json({"ok": True, "action": self.action, "output": str(self.out),
                    "files": self.files, "warnings": self.warnings})
        return 0


# --------------------------------------------------------------------------
# Browser (Edge / Chrome headless) + minimal CDP client
# --------------------------------------------------------------------------

BROWSER_PATHS = [
    os.environ.get("WEB_CAPTURE_BROWSER", ""),
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "/usr/bin/microsoft-edge", "/usr/bin/google-chrome",
    "/usr/bin/chromium", "/usr/bin/chromium-browser",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
]


def find_browser(explicit: str | None = None) -> str:
    candidates = ([explicit] if explicit else []) + BROWSER_PATHS + [
        shutil.which(n) or "" for n in ("msedge", "chrome", "google-chrome",
                                        "chromium", "microsoft-edge")]
    for item in candidates:
        if item and Path(item).is_file():
            return str(item)
    raise WebError("未找到 Edge/Chrome 浏览器；可设置 WEB_CAPTURE_BROWSER 或传 --browser 指定路径")


def browser_status(explicit: str | None = None) -> dict:
    try:
        path = find_browser(explicit)
        return {"available": True, "path": path,
                "name": "Edge" if "edge" in path.lower() else "Chromium/Chrome",
                "engine": "CDP + headless CLI"}
    except WebError as exc:
        return {"available": False, "path": None, "name": None, "error": str(exc)}


class _WS:
    """RFC6455 client, just enough for DevTools JSON messages."""

    def __init__(self, url: str, timeout: float = 30):
        p = urllib.parse.urlsplit(url)
        self.sock = socket.create_connection((p.hostname, p.port or 80), timeout=timeout)
        self.sock.settimeout(timeout)
        key = base64.b64encode(os.urandom(16)).decode()
        path = p.path + (("?" + p.query) if p.query else "")
        req = ("GET %s HTTP/1.1\r\nHost: %s:%d\r\nUpgrade: websocket\r\n"
               "Connection: Upgrade\r\nSec-WebSocket-Key: %s\r\n"
               "Sec-WebSocket-Version: 13\r\n\r\n"
               % (path, p.hostname, p.port or 80, key))
        self.sock.sendall(req.encode("ascii"))
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise WebError("CDP 握手失败（连接关闭）")
            buf += chunk
        if b" 101 " not in buf.split(b"\r\n", 1)[0]:
            raise WebError("CDP 握手被拒绝: %s" % buf.split(b"\r\n", 1)[0][:120])
        self._buf = buf.split(b"\r\n\r\n", 1)[1]
        self._id = 0

    def _read(self, n: int) -> bytes:
        while len(self._buf) < n:
            chunk = self.sock.recv(max(4096, n - len(self._buf)))
            if not chunk:
                raise WebError("CDP 连接中断")
            self._buf += chunk
        out, self._buf = self._buf[:n], self._buf[n:]
        return out

    def send(self, obj: dict) -> None:
        payload = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        head = bytearray([0x81])
        n = len(payload)
        if n < 126:
            head.append(0x80 | n)
        elif n < 65536:
            head.append(0x80 | 126)
            head += struct.pack("!H", n)
        else:
            head.append(0x80 | 127)
            head += struct.pack("!Q", n)
        mask = os.urandom(4)
        head += mask
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        self.sock.sendall(bytes(head) + masked)

    def recv(self) -> dict:
        b0, b1 = self._read(2)
        opcode = b0 & 0x0F
        n = b1 & 0x7F
        if n == 126:
            n = struct.unpack("!H", self._read(2))[0]
        elif n == 127:
            n = struct.unpack("!Q", self._read(8))[0]
        if b1 & 0x80:
            mask = self._read(4)
            raw = bytes(b ^ mask[i % 4] for i, b in enumerate(self._read(n)))
        else:
            raw = self._read(n)
        if opcode == 0x9:                       # ping -> pong
            self.sock.sendall(bytes([0x8A, 0x80]) + b"\x00\x00\x00\x00")
            return self.recv()
        if opcode == 0x8:
            raise WebError("CDP 连接被浏览器关闭")
        try:
            return json.loads(raw.decode("utf-8", "replace"))
        except json.JSONDecodeError:
            return {}

    def request(self, method: str, params: dict | None = None,
                timeout: float = 30) -> dict:
        self._id += 1
        rid = self._id
        self.send({"id": rid, "method": method, "params": params or {}})
        self.sock.settimeout(timeout)
        deadline = time.time() + timeout
        while time.time() < deadline:
            msg = self.recv()
            if msg.get("id") != rid:
                continue                        # CDP event, ignore
            if "error" in msg:
                raise WebError("CDP %s: %s" % (method, msg["error"].get("message")))
            return msg.get("result", {})
        raise WebError("CDP %s 超时" % method)

    def close(self) -> None:
        try:
            self.sock.close()
        except OSError:
            pass


class _CDP:
    def __init__(self, browser: str, timeout: float):
        self.browser = browser
        self.timeout = timeout
        self.tmp = Path(tempfile.mkdtemp(prefix="web-capture-profile-"))
        self.proc = None
        self.ws = None

    def __enter__(self):
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        args = [self.browser, "--headless=new", "--disable-gpu", "--no-sandbox",
                "--disable-dev-shm-usage", "--no-first-run",
                "--no-default-browser-check", "--hide-scrollbars",
                "--remote-debugging-port=0", "--user-data-dir=" + str(self.tmp),
                "about:blank"]
        try:
            self.proc = subprocess.Popen(args, stdout=subprocess.DEVNULL,
                                         stderr=subprocess.DEVNULL,
                                         creationflags=flags)
            port_file = self.tmp / "DevToolsActivePort"
            for _ in range(int(self.timeout * 10)):
                if port_file.is_file():
                    break
                time.sleep(0.1)
            else:
                raise WebError("浏览器未启动 DevTools 端口")
            port = int(port_file.read_text(encoding="ascii").splitlines()[0])
            with urllib.request.urlopen("http://127.0.0.1:%d/json/list" % port,
                                        timeout=5) as resp:
                targets = json.loads(resp.read())
            page = next((t for t in targets if t.get("type") == "page"), None)
            if not page:
                raise WebError("浏览器没有可用页面 target")
            self.ws = _WS(page["webSocketDebuggerUrl"], timeout=self.timeout)
            return self
        except Exception:
            self.close()
            raise

    def call(self, method, params=None, timeout=None):
        return self.ws.request(method, params, timeout or self.timeout)

    def load(self, url: str, width: int, height: int, wait: float) -> dict:
        self.call("Page.enable")
        self.call("Runtime.enable")
        self.call("Emulation.setDeviceMetricsOverride",
                  {"width": width, "height": height, "deviceScaleFactor": 1,
                   "mobile": False})
        self.call("Page.navigate", {"url": url})
        deadline = time.time() + self.timeout
        while time.time() < deadline:
            try:
                res = self.call("Runtime.evaluate",
                                {"expression": "document.readyState",
                                 "returnByValue": True}, timeout=5)
                if res.get("result", {}).get("value") == "complete":
                    break
            except (WebError, OSError, socket.timeout):
                pass
            time.sleep(0.2)
        if wait > 0:
            time.sleep(min(wait, 10))
        m = self.call("Page.getLayoutMetrics")
        size = m.get("cssContentSize") or m.get("contentSize") or {}
        return {"width": int(size.get("width") or width),
                "height": int(size.get("height") or height)}

    def close(self):
        if self.ws:
            self.ws.close()
            self.ws = None
        if self.proc:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=5)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
            self.proc = None
        shutil.rmtree(self.tmp, ignore_errors=True)

    def __exit__(self, *exc):
        self.close()


def _browser_url(src: str) -> str:
    if is_url(src):
        return src
    path = Path(src).expanduser()
    if not path.is_file():
        raise WebError("找不到输入文件: %s" % path)
    return file_uri(path)


def _cli_capture(browser: str, url: str, out: Path, kind: str,
                 width: int, height: int, timeout: float) -> None:
    tmp = Path(tempfile.mkdtemp(prefix="web-capture-cli-"))
    flag = "--screenshot=" + str(out) if kind == "png" else "--print-to-pdf=" + str(out)
    args = [browser, "--headless=new", "--disable-gpu", "--no-sandbox",
            "--hide-scrollbars", "--no-first-run", "--user-data-dir=" + str(tmp),
            "--window-size=%d,%d" % (width, height),
            "--virtual-time-budget=5000", flag]
    if kind == "pdf":
        args.append("--no-pdf-header-footer")
    args.append(url)
    try:
        proc = subprocess.run(args, capture_output=True, text=True,
                              encoding="utf-8", errors="replace",
                              timeout=timeout,
                              creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
                              if os.name == "nt" else 0)
        if not out.is_file() or out.stat().st_size == 0:
            raise WebError("命令行渲染未产出文件 (%s)" %
                           (proc.stderr or proc.stdout or "")[-180:].strip())
    except subprocess.TimeoutExpired as exc:
        raise WebError("浏览器渲染超时（%ss）" % timeout) from exc
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def render_page(src: str, out: Path, kind: str = "png", *, width: int = 1440,
                height: int = 900, full_page: bool = True, wait: float = 0.8,
                timeout: float = 60, browser: str | None = None) -> dict:
    """Screenshot (png) or print (pdf). CDP first, CLI fallback.

    Returns an evidence dict; degraded=True means only a viewport-sized CLI
    render was produced, which must be surfaced to the user.
    """
    engine_path = find_browser(browser)
    url = _browser_url(src)
    out.parent.mkdir(parents=True, exist_ok=True)
    warnings: list[str] = []
    try:
        with _CDP(engine_path, timeout) as cdp:
            size = cdp.load(url, width, height, wait)
            if kind == "png":
                h = min(max(size["height"], height), 40000) if full_page else height
                if full_page and h != height:
                    cdp.call("Emulation.setDeviceMetricsOverride",
                             {"width": width, "height": h,
                              "deviceScaleFactor": 1, "mobile": False})
                res = cdp.call("Page.captureScreenshot",
                               {"format": "png", "fromSurface": True,
                                "captureBeyondViewport": bool(full_page)},
                               timeout=max(timeout, 30))
                out.write_bytes(base64.b64decode(res["data"]))
            else:
                res = cdp.call("Page.printToPDF",
                               {"printBackground": True, "preferCSSPageSize": True,
                                "landscape": False, "scale": 1.0},
                               timeout=max(timeout, 30))
                out.write_bytes(base64.b64decode(res["data"]))
        return {"engine": "cdp", "browser": engine_path, "full_page": bool(full_page),
                "width": width, "height": size["height"], "degraded": False,
                "warnings": warnings, "url": url}
    except Exception as exc:                      # CDP unavailable -> CLI fallback
        warnings.append("CDP 整页渲染不可用，已降级为命令行视口渲染: %s" % exc)
        _cli_capture(engine_path, url, out, kind, width, height, timeout)
        warnings.append("降级产物只覆盖 %dx%d 视口，不是完整长图" % (width, height))
        return {"engine": "cli", "browser": engine_path, "full_page": False,
                "width": width, "height": height, "degraded": True,
                "warnings": warnings, "url": url}
