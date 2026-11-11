#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""web-batch: capture a list of URLs / local HTML files, one folder each."""
import argparse
import json
import re
import time
from pathlib import Path

from web_common import (DEFAULT_TIMEOUT, DEFAULT_UA, WebError, die, dump,
                        is_url, load_source, stem_for, unique_outdir, utcnow)
from web_html import Document


def read_sources(src: str) -> list[str]:
    path = Path(src).expanduser()
    if is_url(src):
        return [src]
    if not path.exists():
        raise WebError("找不到输入: %s" % path)
    if path.is_dir():
        for name in ("urls.txt", "urls.json", "urls.csv"):
            if (path / name).is_file():
                path = path / name
                break
        else:
            return [str(p) for p in sorted(path.glob("*.html")) +
                    sorted(path.glob("*.htm"))]
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    if path.suffix.lower() == ".json":
        data = json.loads(text)
        items = data.get("urls", []) if isinstance(data, dict) else data
        return [str(x) for x in items]
    if path.suffix.lower() == ".csv":
        import csv
        import io
        rows = list(csv.reader(io.StringIO(text)))
        if not rows:
            return []
        header = [c.strip().lower() for c in rows[0]]
        idx = header.index("url") if "url" in header else 0
        return [r[idx].strip() for r in rows[1:] if len(r) > idx and r[idx].strip()]
    return [line.strip() for line in text.splitlines()
            if line.strip() and not line.lstrip().startswith("#")]


def main() -> int:
    p = argparse.ArgumentParser(description="Batch capture a URL list")
    p.add_argument("src", help="urls .txt/.json/.csv, a directory, or one URL")
    p.add_argument("-o", "--output", required=True, help="output directory")
    p.add_argument("--format", default="html,md",
                   help="comma list: html,md,extract / all")
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--delay", type=float, default=0.6)
    p.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    p.add_argument("--ua", default=DEFAULT_UA)
    p.add_argument("--no-robots", action="store_true")
    a = p.parse_args()
    try:
        wanted = {"html", "md", "extract"} if a.format == "all" else {
            x.strip() for x in a.format.split(",") if x.strip()}
        if wanted - {"html", "md", "extract"}:
            raise WebError("--format 只支持 html,md,extract,all")
        sources = read_sources(a.src)[:max(1, a.limit)]
        if not sources:
            raise WebError("输入里没有可抓取的 URL 或 HTML 文件")
        out = unique_outdir(a.output)
        out.mkdir(parents=True, exist_ok=True)
        rows, warnings, ok_count = [["index", "url", "status", "title", "bytes", "error"]], [], 0
        for i, url in enumerate(sources, 1):
            folder = out / ("%02d-%s" % (i, stem_for(url)[:60]))
            folder.mkdir(parents=True, exist_ok=True)
            entry = [str(i), url, "", "", "", ""]
            try:
                source = load_source(url, timeout=a.timeout, ua=a.ua,
                                     respect_robots=not a.no_robots)
                doc = Document(source.text, source.url)
                if "html" in wanted:
                    (folder / "page.html").write_bytes(source.body)
                if "md" in wanted:
                    md, outline = doc.markdown()
                    (folder / "page.md").write_text(
                        "# %s\n\n%s" % (doc.title, md), encoding="utf-8")
                    (folder / "outline.json").write_text(
                        dump(outline), encoding="utf-8")
                if "extract" in wanted:
                    (folder / "extract.json").write_text(dump({
                        "url": source.url, "title": doc.title,
                        "links": doc.links(), "images": doc.images(),
                        "metas": doc.metas}), encoding="utf-8")
                (folder / "meta.json").write_text(dump({
                    "url": source.url, "title": doc.title,
                    "status": source.status, "encoding": source.encoding,
                    "bytes": len(source.body), "fetched_at": utcnow()}),
                    encoding="utf-8")
                entry[2:5] = ["ok", doc.title, str(len(source.body))]
                ok_count += 1
            except (WebError, OSError, ValueError) as exc:
                entry[2], entry[5] = "failed", str(exc)
                warnings.append("%s: %s" % (url, exc))
                (folder / "error.txt").write_text(str(exc), encoding="utf-8")
            rows.append(entry)
            if a.delay > 0 and i < len(sources):
                time.sleep(a.delay)
        csv_text = _csv(rows)
        (out / "index.csv").write_text("\ufeff" + csv_text, encoding="utf-8")
        (out / "manifest.json").write_text(dump({
            "skill": "web-capture", "action": "web-batch", "source": a.src,
            "output": str(out), "generated_at": utcnow(),
            "total": len(sources), "succeeded": ok_count,
            "failed": len(sources) - ok_count, "format": sorted(wanted),
            "files": ["index.csv", "manifest.json"], "warnings": warnings}),
            encoding="utf-8")
        print(json.dumps({"ok": True, "action": "web-batch", "output": str(out),
                          "total": len(sources), "succeeded": ok_count,
                          "failed": len(sources) - ok_count,
                          "warnings": warnings}, ensure_ascii=False))
        return 0
    except WebError as exc:
        return die(str(exc), 1)
    except Exception as exc:
        return die("web-batch 失败: %s: %s" % (type(exc).__name__, exc))


def _csv(rows) -> str:
    import csv
    import io
    buf = io.StringIO(newline="")
    csv.writer(buf).writerows(rows)
    return buf.getvalue()


if __name__ == "__main__":
    raise SystemExit(main())
