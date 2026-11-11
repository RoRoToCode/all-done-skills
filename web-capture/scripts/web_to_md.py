#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""web-to-md: readable main content as Markdown, with an outline."""
import argparse
import json

from web_common import DEFAULT_TIMEOUT, DEFAULT_UA, Job, WebError, die, utcnow
from web_html import Document


def main() -> int:
    p = argparse.ArgumentParser(description="Web page -> clean Markdown")
    p.add_argument("src", help="http(s) URL or local HTML file")
    p.add_argument("-o", "--output", required=True, help="output directory")
    p.add_argument("--all", action="store_true", help="convert whole page, skip content extraction")
    p.add_argument("--no-frontmatter", action="store_true")
    p.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    p.add_argument("--ua", default=DEFAULT_UA)
    p.add_argument("--no-robots", action="store_true")
    a = p.parse_args()
    try:
        job = Job("web-to-md", a.src, a.output, a)
        source = job.load()
        doc = Document(source.text, source.url)
        main_node = doc.main()
        text, outline = doc.markdown(main_node, all_content=a.all)
        parts = []
        if not a.no_frontmatter:
            fm = {"title": doc.title, "source": source.url,
                  "captured_at": utcnow(), "language": doc.lang}
            parts.append("---\n" + "\n".join(
                "%s: %s" % (k, json.dumps(v, ensure_ascii=False))
                for k, v in fm.items()) + "\n---\n")
        if doc.title and not text.startswith("# "):
            parts.append("# " + doc.title + "\n")
        parts.append(text)
        job.write("page.md", "\n".join(parts))
        job.json("outline.json", {"title": doc.title, "headings": outline,
                                  "chars": len(text)})
        return job.finish(title=doc.title, url=source.url, chars=len(text),
                          headings=len(outline),
                          main_selector=_selector(main_node),
                          whole_page=bool(a.all))
    except WebError as exc:
        return die(str(exc), 1)
    except Exception as exc:
        return die("web-to-md 失败: %s: %s" % (type(exc).__name__, exc))


def _selector(node) -> str:
    return "%s#%s.%s" % (node.tag, node.attr("id"),
                         node.attr("class").replace(" ", ".")[:60])


if __name__ == "__main__":
    raise SystemExit(main())
