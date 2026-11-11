#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dependency / connectivity self-check for web-capture.

Unlike the other skills in this family, web-capture has NO pip dependencies:
all text actions use the Python standard library. `install` therefore only
prints guidance instead of downloading anything. The only external component
is a local Edge/Chrome for screenshots and PDF.

  python scripts/bootstrap.py check
  python scripts/bootstrap.py browser
  python scripts/bootstrap.py probe https://example.com
  python scripts/bootstrap.py install
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys

from web_common import (VERSION, DEFAULT_UA, WebError, browser_status, dump,
                        load_source, robots_check, normalize_url)


def check() -> int:
    status = browser_status()
    info = {
        "skill": "web-capture",
        "version": VERSION,
        "python": sys.executable,
        "stdlib": {"status": "ok", "packages": []},
        "browser": status,
        "optional": {name: importlib.util.find_spec(name) is not None
                     for name in ("bs4", "lxml")},
        "hint": ("浏览器缺失：设置 WEB_CAPTURE_BROWSER 或安装 Edge/Chrome；"
                 "文本类动作仍可正常使用"),
    }
    info["status"] = "ok" if status["available"] else "degraded"
    print(dump(info), end="")
    return 0 if status["available"] else 2


def browser() -> int:
    print(dump(browser_status()), end="")
    return 0


def probe(url: str, timeout: float, no_robots: bool) -> int:
    from web_html import Document
    clean = normalize_url(url)
    if not clean:
        print(dump({"ok": False, "error": "需要 http(s) 网址"}), end="")
        return 1
    allowed, robots_note = robots_check(clean, DEFAULT_UA, timeout, not no_robots)
    result = {"ok": True, "url": clean, "user_agent": DEFAULT_UA,
              "robots_allowed": allowed, "robots_note": robots_note}
    if not allowed:
        print(dump(result), end="")
        return 1
    try:
        src = load_source(clean, timeout=timeout, respect_robots=False)
        doc = Document(src.text, src.url)
        result.update({
            "status": src.status, "final_url": src.url,
            "encoding": src.encoding, "bytes": len(src.body),
            "elapsed_ms": src.elapsed_ms, "title": doc.title,
            "headings": len(doc.headings()), "links": len(doc.links()),
            "images": len(doc.images()), "tables": len(doc.tables()),
            "warnings": src.warnings,
        })
    except (WebError, OSError) as exc:
        result.update({"ok": False, "error": str(exc)})
    print(dump(result), end="")
    return 0 if result["ok"] else 1


def install() -> int:
    print(dump({
        "ok": True,
        "mode": "no-op",
        "message": "无需 pip 安装：所有文本动作只用 Python 标准库。",
        "browser": browser_status(),
        "next": ["python scripts/bootstrap.py check",
                 "如需截图/PDF：安装 Microsoft Edge 或 Google Chrome，"
                 "或设置 WEB_CAPTURE_BROWSER=<浏览器可执行文件>"],
    }), end="")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="web-capture environment check")
    sub = p.add_subparsers(dest="action", required=True)
    sub.add_parser("check")
    sub.add_parser("browser")
    sub.add_parser("install")
    q = sub.add_parser("probe")
    q.add_argument("url")
    q.add_argument("--timeout", type=float, default=15)
    q.add_argument("--no-robots", action="store_true")
    a = p.parse_args()
    if a.action == "check":
        return check()
    if a.action == "browser":
        return browser()
    if a.action == "probe":
        return probe(a.url, a.timeout, a.no_robots)
    return install()


if __name__ == "__main__":
    raise SystemExit(main())
