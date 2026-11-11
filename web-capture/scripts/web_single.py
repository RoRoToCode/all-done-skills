#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""web-single: archive a page as one self-contained HTML file (data: URIs)."""
import argparse

from web_common import (DEFAULT_TIMEOUT, DEFAULT_UA, Job, WebError, die)
from web_html import (Document, Node, data_uri, download_resource, guess_mime,
                      inline_css, serialize)


def main() -> int:
    p = argparse.ArgumentParser(description="Single-file offline web archive")
    p.add_argument("src", help="http(s) URL or local HTML file")
    p.add_argument("-o", "--output", required=True, help="output directory")
    p.add_argument("--max-assets", type=int, default=80)
    p.add_argument("--max-asset-bytes", type=int, default=3 * 1024 * 1024)
    p.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    p.add_argument("--ua", default=DEFAULT_UA)
    p.add_argument("--no-robots", action="store_true")
    a = p.parse_args()
    try:
        job = Job("web-single", a.src, a.output, a)
        source = job.load()
        doc = Document(source.text, source.url)
        resources = doc.resources()[:a.max_assets]
        inlined, failed, log = 0, 0, []
        for res in resources:
            url, node, attr, kind = (res["url"], res["node"], res["attr"], res["kind"])
            entry = {"kind": kind, "url": url}
            try:
                body, mime = download_resource(url, timeout=a.timeout, ua=a.ua,
                                               max_bytes=a.max_asset_bytes)
                if kind == "css":
                    css = body.decode("utf-8", "replace")
                    css, css_warnings = inline_css(css, url, timeout=a.timeout)
                    job.warnings.extend(css_warnings)
                    node.tag = "style"
                    node.attrs = {"data-web-capture-src": url}
                    node.children = [css]
                elif kind == "js":
                    node.attrs = {"data-web-capture-src": url}
                    node.children = [body.decode("utf-8", "replace")]
                else:
                    node.attrs[attr] = data_uri(body, guess_mime(url, kind, mime))
                inlined += 1
                entry.update({"status": "inlined", "bytes": len(body)})
            except WebError as exc:
                failed += 1
                entry.update({"status": "failed", "error": str(exc)})
                job.warnings.append("未内联 %s: %s" % (url, exc))
            log.append(entry)

        # <base href> would break data: / relative references in an offline copy
        for node in list(_walk(doc.root)):
            if node.tag == "base":
                node.attrs.pop("href", None)
                node.attrs["data-web-capture-removed"] = "base"
        head = next((n for n in _walk(doc.root) if n.tag == "head"), None)
        if head is not None:
            if not any(n.tag == "meta" and ("charset" in n.attrs
                       or n.attr("http-equiv", "").lower() == "content-type")
                       for n in head.children if isinstance(n, Node)):
                head.children.insert(0, Node("meta", {"charset": "utf-8"}, head))
        markup = ("<!DOCTYPE html>\n" if doc.doctype else "") + serialize(doc.root)
        job.write("page.single.html", markup)
        job.json("resources.json", log)
        return job.finish(title=doc.title, url=source.url,
                          resources=len(resources), inlined=inlined,
                          failed=failed, bytes=len(markup.encode("utf-8")))
    except WebError as exc:
        return die(str(exc), 1)
    except Exception as exc:
        return die("web-single 失败: %s: %s" % (type(exc).__name__, exc))


def _walk(node):
    for child in node.children:
        if isinstance(child, Node):
            yield child
            yield from _walk(child)


if __name__ == "__main__":
    raise SystemExit(main())
