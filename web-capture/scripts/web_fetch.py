#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""web-fetch: save one page verbatim, with metadata and optional local assets."""
import argparse
import mimetypes
import re
from pathlib import Path

from web_common import (DEFAULT_TIMEOUT, DEFAULT_UA, Job, WebError, die,
                        dump, print_json)
from web_html import Document, download_resource, serialize


def asset_name(index: int, url: str, kind: str) -> str:
    tail = Path(url.split("?")[0]).name or "asset"
    tail = re.sub(r"[^0-9A-Za-z._-]", "_", tail)[:48]
    ext = Path(tail).suffix
    if not ext:
        ext = {"css": ".css", "js": ".js", "image": ".bin"}.get(kind, ".bin")
        tail += ext
    return "%03d-%s" % (index, tail)


def main() -> int:
    p = argparse.ArgumentParser(description="Save a web page (HTML + metadata)")
    p.add_argument("src", help="http(s) URL or local HTML file")
    p.add_argument("-o", "--output", required=True, help="output directory")
    p.add_argument("--assets", action="store_true", help="also download css/js/images")
    p.add_argument("--max-assets", type=int, default=60)
    p.add_argument("--max-asset-bytes", type=int, default=3 * 1024 * 1024)
    p.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    p.add_argument("--ua", default=DEFAULT_UA)
    p.add_argument("--no-robots", action="store_true")
    a = p.parse_args()
    try:
        job = Job("web-fetch", a.src, a.output, a)
        source = job.load()
        job.write("page.html", source.body)
        meta = job.meta(source)
        doc = Document(source.text, source.url)
        meta.update({"title": doc.title, "language": doc.lang,
                     "links": len(doc.links()), "images": len(doc.images()),
                     "tables": len(doc.tables()), "resources": len(doc.resources())})
        job.json("meta.json", meta)
        resource_log = []
        if a.assets:
            for i, res in enumerate(doc.resources()[:a.max_assets], 1):
                entry = {"kind": res["kind"], "url": res["url"]}
                try:
                    body, mime = download_resource(
                        res["url"], timeout=a.timeout, ua=a.ua,
                        max_bytes=a.max_asset_bytes)
                    name = asset_name(i, res["url"], res["kind"])
                    job.write("assets/" + name, body)
                    entry.update({"file": "assets/" + name, "bytes": len(body),
                                  "mime": mime, "status": "ok"})
                    res["node"].attrs[res["attr"]] = "assets/" + name
                except WebError as exc:
                    entry.update({"status": "failed", "error": str(exc)})
                    job.warnings.append("资源下载失败 %s: %s" % (res["url"], exc))
                resource_log.append(entry)
            job.json("resources.json", resource_log)
            job.write("page.local.html",
                      ("<!DOCTYPE html>\n" if doc.doctype else "") + serialize(doc.root))
        return job.finish(title=doc.title, url=source.url,
                          assets_saved=sum(1 for r in resource_log
                                           if r.get("status") == "ok"))
    except WebError as exc:
        return die(str(exc), 1, "检查网址或网络；本地文件可直接传路径")
    except Exception as exc:
        return die("web-fetch 失败: %s: %s" % (type(exc).__name__, exc))


if __name__ == "__main__":
    raise SystemExit(main())
