#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""web-to-pdf: print a page to PDF with Edge/Chrome headless."""
import argparse

from web_common import (DEFAULT_UA, Job, WebError, browser_status, die,
                        guard_url, render_page)


def main() -> int:
    p = argparse.ArgumentParser(description="Web page -> PDF")
    p.add_argument("src", help="http(s) URL or local HTML file")
    p.add_argument("-o", "--output", required=True, help="output directory")
    p.add_argument("--width", type=int, default=1280)
    p.add_argument("--height", type=int, default=900)
    p.add_argument("--wait", type=float, default=0.8)
    p.add_argument("--timeout", type=float, default=60)
    p.add_argument("--browser", help="explicit path to msedge/chrome")
    p.add_argument("--ua", default=DEFAULT_UA)
    p.add_argument("--no-robots", action="store_true")
    a = p.parse_args()
    try:
        status = browser_status(a.browser)
        if not status["available"]:
            raise WebError("%s（截图/PDF 需要本机 Edge 或 Chrome）" % status["error"])
        guard_url(a.src, a.ua, min(a.timeout, 10), not a.no_robots)
        job = Job("web-to-pdf", a.src, a.output, a)
        out = job.out / "page.pdf"
        info = render_page(a.src, out, "pdf", width=a.width, height=a.height,
                           full_page=True, wait=a.wait, timeout=a.timeout,
                           browser=a.browser)
        job.warnings.extend(info.get("warnings", []))
        job.files.append("page.pdf")
        job.json("capture.json", info)
        if not out.read_bytes()[:5].startswith(b"%PDF-"):
            raise WebError("生成的不是有效 PDF（文件头异常）")
        return job.finish(engine=info["engine"], degraded=info["degraded"],
                          bytes=out.stat().st_size, browser=info["browser"])
    except WebError as exc:
        return die(str(exc), 1, "可设 WEB_CAPTURE_BROWSER 或 --browser 指定浏览器路径")
    except Exception as exc:
        return die("web-to-pdf 失败: %s: %s" % (type(exc).__name__, exc))


if __name__ == "__main__":
    raise SystemExit(main())
