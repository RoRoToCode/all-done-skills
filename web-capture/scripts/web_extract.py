#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""web-extract: links, images, tables and page metadata -> JSON + CSV."""
import argparse

from web_common import DEFAULT_TIMEOUT, DEFAULT_UA, Job, WebError, die
from web_html import Document, table_rows

KINDS = ("links", "images", "tables", "meta")


def main() -> int:
    p = argparse.ArgumentParser(description="Structured extraction from a page")
    p.add_argument("src", help="http(s) URL or local HTML file")
    p.add_argument("-o", "--output", required=True, help="output directory")
    p.add_argument("--kind", default="all", help="all or comma list: links,images,tables,meta")
    p.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    p.add_argument("--ua", default=DEFAULT_UA)
    p.add_argument("--no-robots", action="store_true")
    a = p.parse_args()
    try:
        wanted = set(KINDS) if a.kind.strip() == "all" else {
            k.strip() for k in a.kind.split(",") if k.strip()}
        unknown = wanted - set(KINDS)
        if unknown:
            raise WebError("未知 --kind: %s" % ", ".join(sorted(unknown)))
        job = Job("web-extract", a.src, a.output, a)
        source = job.load()
        doc = Document(source.text, source.url)
        result = {"url": source.url, "title": doc.title, "kinds": sorted(wanted)}

        if "links" in wanted:
            links = doc.links()
            result["links"] = links
            job.csv("links.csv", [["text", "href", "rel", "title"]] +
                    [[x["text"], x["href"], x["rel"], x["title"]] for x in links])
        if "images" in wanted:
            images = doc.images()
            result["images"] = images
            job.csv("images.csv", [["src", "alt", "width", "height", "title"]] +
                    [[x["src"], x["alt"], x["width"], x["height"], x["title"]]
                     for x in images])
        if "tables" in wanted:
            tables = []
            for i, table in enumerate(doc.tables(), 1):
                rows = table_rows(table)
                name = "tables/table-%04d.csv" % i
                job.csv(name, rows)
                tables.append({"index": i, "file": name,
                               "rows": len(rows),
                               "columns": max((len(r) for r in rows), default=0),
                               "header": rows[0] if rows else []})
            result["tables"] = tables
        if "meta" in wanted:
            meta = {"title": doc.title, "language": doc.lang,
                    "canonical": doc.canonical, "metas": doc.metas,
                    "jsonld": doc.jsonld, "headings": doc.headings()}
            result["meta"] = meta
            job.json("meta.json", meta)

        job.json("extract.json", result)
        return job.finish(title=doc.title, url=source.url,
                          links=len(result.get("links", [])),
                          images=len(result.get("images", [])),
                          tables=len(result.get("tables", [])),
                          metas=len(doc.metas))
    except WebError as exc:
        return die(str(exc), 1)
    except Exception as exc:
        return die("web-extract 失败: %s: %s" % (type(exc).__name__, exc))


if __name__ == "__main__":
    raise SystemExit(main())
