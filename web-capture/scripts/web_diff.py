#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""web-diff: compare two captures (URLs, local HTML files, or snapshot dirs)."""
import argparse
import difflib
import json
from pathlib import Path

from web_common import (DEFAULT_TIMEOUT, DEFAULT_UA, WebError, die, dump,
                        is_url, load_source, unique_outdir, utcnow)
from web_html import Document, visible_text

SNAPSHOT_NAMES = ("page.html", "index.html")


def resolve_pair(src: str, old_opt: str, new_opt: str) -> tuple[str, str]:
    if old_opt and new_opt:
        return old_opt, new_opt
    path = Path(src).expanduser()
    if is_url(src) or path.is_file():
        raw = path.read_text(encoding="utf-8-sig", errors="replace") if path.is_file() else ""
        if raw.lstrip().startswith("{"):
            cfg = json.loads(raw)
            return str(cfg.get("old", "")), str(cfg.get("new", ""))
        raise WebError("单个 URL/文件无法对比；请传 --old X --new Y，或给含 {old,new} 的 JSON / 快照目录")
    if not path.is_dir():
        raise WebError("找不到输入: %s" % path)
    for old_name, new_name in (("old.html", "new.html"), ("old/page.html", "new/page.html")):
        if (path / old_name).is_file() and (path / new_name).is_file():
            return str(path / old_name), str(path / new_name)
    for sub in ("old", "new"):
        d = path / sub
        if not d.is_dir() or not any((d / n).is_file() for n in SNAPSHOT_NAMES):
            break
    else:
        return str(path / "old"), str(path / "new")
    raise WebError("快照目录需含 old.html/new.html 或 old/、new/ 两个子目录（内含 page.html）")


def load_any(value: str, args) -> tuple[str, Document, str]:
    path = Path(value).expanduser()
    if path.is_dir():
        for name in SNAPSHOT_NAMES:
            if (path / name).is_file():
                value = str(path / name)
                break
    source = load_source(value, timeout=args.timeout, ua=args.ua,
                         respect_robots=not args.no_robots)
    doc = Document(source.text, source.url)
    return value, doc, visible_text(doc.main())


def main() -> int:
    p = argparse.ArgumentParser(description="Compare two web captures")
    p.add_argument("src", nargs="?", default="", help="JSON config or snapshot dir")
    p.add_argument("-o", "--output", required=True, help="output directory")
    p.add_argument("--old", help="old URL / HTML file / snapshot dir")
    p.add_argument("--new", help="new URL / HTML file / snapshot dir")
    p.add_argument("--strict", action="store_true", help="exit 2 when changes found")
    p.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    p.add_argument("--ua", default=DEFAULT_UA)
    p.add_argument("--no-robots", action="store_true")
    a = p.parse_args()
    try:
        if not a.src and not (a.old and a.new):
            raise WebError("需要 --old 与 --new，或包含 {old,new} 的配置文件")
        old_src, new_src = resolve_pair(a.src, a.old, a.new)
        out = unique_outdir(a.output)
        out.mkdir(parents=True, exist_ok=True)
        old_path, d1, t1 = load_any(old_src, a)
        new_path, d2, t2 = load_any(new_src, a)
        l1 = {x["href"] for x in d1.links()}
        l2 = {x["href"] for x in d2.links()}
        i1 = {x["src"] for x in d1.images()}
        i2 = {x["src"] for x in d2.images()}
        h1 = [x["text"] for x in d1.headings()]
        h2 = [x["text"] for x in d2.headings()]
        lines = list(difflib.unified_diff(t1.splitlines(), t2.splitlines(),
                                          fromfile="old", tofile="new", lineterm=""))
        result = {
            "old": {"source": old_path, "title": d1.title, "chars": len(t1),
                    "links": len(l1), "images": len(i1)},
            "new": {"source": new_path, "title": d2.title, "chars": len(t2),
                    "links": len(l2), "images": len(i2)},
            "title_changed": d1.title != d2.title,
            "text_diff": lines,
            "added_lines": sum(1 for x in lines if x.startswith("+") and not x.startswith("+++")),
            "removed_lines": sum(1 for x in lines if x.startswith("-") and not x.startswith("---")),
            "links_added": sorted(l2 - l1), "links_removed": sorted(l1 - l2),
            "images_added": sorted(i2 - i1), "images_removed": sorted(i1 - i2),
            "headings_added": [x for x in h2 if x not in h1],
            "headings_removed": [x for x in h1 if x not in h2],
            "metadata_added": sorted(set(d2.metas) - set(d1.metas)),
            "metadata_removed": sorted(set(d1.metas) - set(d2.metas)),
            "compared_at": utcnow(),
        }
        result["changed"] = any((result["title_changed"], lines,
                                 result["links_added"], result["links_removed"],
                                 result["images_added"], result["images_removed"],
                                 result["headings_added"], result["headings_removed"],
                                 result["metadata_added"], result["metadata_removed"]))
        (out / "diff.json").write_text(dump(result), encoding="utf-8")
        md = ["# 网页变更对比", "",
              "- 旧：%s（%s）" % (old_path, d1.title or "无标题"),
              "- 新：%s（%s）" % (new_path, d2.title or "无标题"),
              "- 结论：%s" % ("有变化" if result["changed"] else "无变化"), "",
              "## 摘要", "",
              "| 项目 | 旧 | 新 |", "| --- | --- | --- |",
              "| 正文字数 | %d | %d |" % (len(t1), len(t2)),
              "| 链接 | %d | %d |" % (len(l1), len(l2)),
              "| 图片 | %d | %d |" % (len(i1), len(i2)),
              "| 新增/删除行 | %d / %d | |" % (result["added_lines"], result["removed_lines"]),
              "", "## 正文差异", "", "```diff"]
        md += (lines[:400] or ["(无文本变化)"])
        md += ["```", ""]
        for label, key in (("新增链接", "links_added"), ("删除链接", "links_removed"),
                           ("新增图片", "images_added"), ("删除图片", "images_removed"),
                           ("新增标题", "headings_added"), ("删除标题", "headings_removed")):
            if result[key]:
                md += ["## " + label, ""] + ["- " + x for x in result[key][:50]] + [""]
        (out / "diff.md").write_text("\n".join(md), encoding="utf-8")
        (out / "manifest.json").write_text(dump({
            "skill": "web-capture", "action": "web-diff", "source": a.src or old_path,
            "output": str(out), "generated_at": utcnow(),
            "files": ["diff.md", "diff.json", "manifest.json"],
            "warnings": [], "changed": result["changed"]}), encoding="utf-8")
        print(json.dumps({"ok": True, "action": "web-diff", "output": str(out),
                          "changed": result["changed"],
                          "added_lines": result["added_lines"],
                          "removed_lines": result["removed_lines"]},
                         ensure_ascii=False))
        return 2 if (a.strict and result["changed"]) else 0
    except WebError as exc:
        return die(str(exc), 1)
    except Exception as exc:
        return die("web-diff 失败: %s: %s" % (type(exc).__name__, exc))


if __name__ == "__main__":
    raise SystemExit(main())
