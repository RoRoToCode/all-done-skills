#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""web-crawl: polite same-origin BFS crawl with depth/page caps."""
import argparse
import re
import time
from collections import deque
from pathlib import Path

from web_common import (DEFAULT_TIMEOUT, DEFAULT_UA, WebError, die, dump,
                        is_url, load_source, normalize_url, robots_check,
                        same_origin, stem_for, unique_outdir, utcnow)
from web_html import Document

SKIP_EXT = re.compile(r"\.(pdf|zip|rar|7z|exe|msi|dmg|apk|mp3|mp4|avi|mov|"
                      r"jpg|jpeg|png|gif|webp|svg|ico|woff2?|ttf|eot|css|js|"
                      r"doc|docx|xls|xlsx|ppt|pptx|csv|json|xml|rss)(\?|$)", re.I)


def main() -> int:
    p = argparse.ArgumentParser(description="Shallow same-origin crawl")
    p.add_argument("src", help="starting http(s) URL")
    p.add_argument("-o", "--output", required=True, help="output directory")
    p.add_argument("--depth", type=int, default=2)
    p.add_argument("--max-pages", type=int, default=30)
    p.add_argument("--delay", type=float, default=0.5)
    p.add_argument("--include", help="regex that a followed URL must match")
    p.add_argument("--exclude", help="regex that a followed URL must NOT match")
    p.add_argument("--cross-origin", action="store_true", help="allow other hosts")
    p.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    p.add_argument("--ua", default=DEFAULT_UA)
    p.add_argument("--no-robots", action="store_true")
    a = p.parse_args()
    try:
        seed = normalize_url(a.src)
        if not seed:
            raise WebError("爬取起点必须是 http(s) 网页地址，不支持本地文件")
        inc = re.compile(a.include) if a.include else None
        exc_re = re.compile(a.exclude) if a.exclude else None
        out = unique_outdir(a.output)
        (out / "pages").mkdir(parents=True, exist_ok=True)
        queue = deque([(seed, 0)])
        seen, rows, edges, warnings = {seed}, [], [], []
        visited = 0
        while queue and visited < max(1, a.max_pages):
            url, depth = queue.popleft()
            allowed, note = robots_check(url, a.ua, a.timeout, not a.no_robots)
            if not allowed:
                warnings.append("robots.txt 拒绝 %s" % url)
                continue
            try:
                source = load_source(url, timeout=a.timeout, ua=a.ua,
                                     respect_robots=False)   # checked above
                doc = Document(source.text, source.url)
                base = stem_for(url)[:60] + "-" + str(visited + 1).zfill(2)
                (out / "pages" / (base + ".html")).write_bytes(source.body)
                md, _ = doc.markdown()
                (out / "pages" / (base + ".md")).write_text(md, encoding="utf-8")
                rows.append([str(visited + 1), str(depth), url,
                             str(source.status), doc.title, str(len(source.body))])
                visited += 1
                if depth < max(0, a.depth):
                    for link in doc.links():
                        nxt = normalize_url(link["href"], source.url)
                        if not nxt or nxt in seen or SKIP_EXT.search(nxt):
                            continue
                        if not a.cross_origin and not same_origin(nxt, seed):
                            continue
                        if inc and not inc.search(nxt):
                            continue
                        if exc_re and exc_re.search(nxt):
                            continue
                        seen.add(nxt)
                        edges.append([url, nxt])
                        queue.append((nxt, depth + 1))
            except (WebError, OSError, ValueError) as err:
                warnings.append("%s: %s" % (url, err))
                rows.append([str(visited + 1), str(depth), url, "failed", "", "0"])
            if a.delay > 0 and queue:
                time.sleep(a.delay)
        (out / "urls.csv").write_text("\ufeff" + _csv(
            [["index", "depth", "url", "status", "title", "bytes"]] + rows),
            encoding="utf-8")
        (out / "graph.json").write_text(dump(
            [{"from": f, "to": t} for f, t in edges]), encoding="utf-8")
        (out / "manifest.json").write_text(dump({
            "skill": "web-capture", "action": "web-crawl", "source": seed,
            "output": str(out), "generated_at": utcnow(), "depth": a.depth,
            "max_pages": a.max_pages, "visited": visited,
            "discovered": len(seen), "edges": len(edges),
            "cross_origin": bool(a.cross_origin), "robots": not a.no_robots,
            "files": ["urls.csv", "graph.json", "manifest.json"],
            "warnings": warnings}), encoding="utf-8")
        import json
        print(json.dumps({"ok": True, "action": "web-crawl", "output": str(out),
                          "visited": visited, "discovered": len(seen),
                          "warnings": warnings}, ensure_ascii=False))
        return 0
    except WebError as exc:
        return die(str(exc), 1)
    except Exception as exc:
        return die("web-crawl 失败: %s: %s" % (type(exc).__name__, exc))


def _csv(rows) -> str:
    import csv
    import io
    buf = io.StringIO(newline="")
    csv.writer(buf).writerows(rows)
    return buf.getvalue()


if __name__ == "__main__":
    raise SystemExit(main())
