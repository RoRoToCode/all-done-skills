#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""eb-validate：轻量 EPUB 规范校验（不依赖 epubcheck / 不联网）。"""
import argparse
import os
import re
import sys
from xml.etree import ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eb_common import (Epub, json_dump, norm_href, parse_nav, parse_ncx, result,
                       setup_stdout, EXIT_FAIL)


def main():
    setup_stdout()
    ap = argparse.ArgumentParser(description="EPUB 规范校验")
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", help="校验报告 JSON")
    ap.add_argument("--strict", action="store_true", help="存在 error 时退出码 5")
    args = ap.parse_args()

    ep = Epub(args.input)
    checks = []

    def add(code, level, msg, detail=""):
        checks.append({"code": code, "level": level, "message": msg, "detail": detail})

    # 1. mimetype
    names = [n.replace("\\", "/") for n in ep.zf.namelist()]
    if not names or names[0] != "mimetype":
        add("mimetype-first", "error", "mimetype 必须是 ZIP 的第一个条目",
            names[0] if names else "空包")
    elif ep.infos.get("mimetype") and ep.infos["mimetype"].compress_type != 0:
        add("mimetype-stored", "error", "mimetype 必须不压缩（STORED）")
    if ep.has("mimetype"):
        raw = ep.read("mimetype").decode("ascii", errors="replace").strip()
        if raw != "application/epub+zip":
            add("mimetype-value", "error", "mimetype 内容不是 application/epub+zip", raw)
    else:
        add("mimetype-missing", "error", "缺少 mimetype 文件")

    # 2. container / OPF
    if not ep.has("META-INF/container.xml"):
        add("container", "error", "缺少 META-INF/container.xml")
    add("opf", "info", "OPF 路径", ep.opf_path)
    for key in ("title", "language", "identifier"):
        if not ep.dc(key):
            add("dc-" + key, "warning", "OPF 元数据缺少 dc:%s" % key)

    # 3. manifest 文件与 spine 引用
    missing_files, missing_refs = [], []
    for item in ep.manifest:
        p = item["path"]
        if not p or not ep.has(p):
            missing_files.append("%s -> %s" % (item["id"], p or "(空)"))
    for idref in ep.spine:
        if idref not in ep.by_id:
            missing_refs.append(idref)
    if missing_files:
        add("manifest-dangling", "error", "manifest 引用了不存在的文件",
            "; ".join(missing_files[:8]))
    if missing_refs:
        add("spine-idref", "error", "spine 的 idref 不在 manifest 中",
            ", ".join(missing_refs[:8]))
    if not ep.spine_docs():
        add("spine-empty", "error", "spine 里没有可读的 XHTML 章节")

    # 4. XHTML 与内部链接
    bad_xml, broken_links = [], []
    link_re = re.compile(r"\b(?:src|href)\s*=\s*[\"']([^\"']+)[\"']", re.I)
    for doc in ep.spine_docs():
        data = ep.read(doc["path"])
        try:
            ET.fromstring(data)
        except ET.ParseError as exc:
            bad_xml.append("%s (%s)" % (doc["path"], str(exc)[:60]))
        for href in link_re.findall(data.decode("utf-8", errors="replace")):
            p = norm_href(doc["path"], href)
            if p and not ep.has(p) and p not in broken_links:
                broken_links.append(p)
    if bad_xml:
        add("xhtml-xml", "warning", "部分 XHTML 不是严格 well-formed（多数阅读器仍可打开）",
            "; ".join(bad_xml[:5]))
    if broken_links:
        add("links-broken", "warning", "章节里存在指向缺失资源的链接",
            ", ".join(broken_links[:8]))

    # 5. 目录
    toc_count = 0
    nav, ncx = ep.nav_path(), ep.ncx_path()
    if nav and ep.has(nav):
        entries = parse_nav(ep.read(nav), nav)
        toc_count = len(entries)
        bad = [e["path"] for e in entries
               if e["path"] and not ep.has(e["path"])]
        if bad:
            add("nav-target", "warning", "nav.xhtml 有指向缺失文件的目录项",
                ", ".join(bad[:6]))
    if ncx and ep.has(ncx):
        entries2 = parse_ncx(ep.read(ncx), ncx)
        toc_count = max(toc_count, len(entries2))
        bad = [e["path"] for e in entries2
               if e["path"] and not ep.has(e["path"])]
        if bad:
            add("ncx-target", "warning", "toc.ncx 有指向缺失文件的目录项",
                ", ".join(bad[:6]))
    if not nav and not ncx:
        add("toc-missing", "warning", "既没有 nav.xhtml 也没有 toc.ncx")
    if toc_count == 0:
        add("toc-empty", "warning", "目录里没有条目")

    # 6. DRM
    if ep.protected():
        add("drm", "warning", "检测到加密标记，本技能不处理受 DRM 保护的电子书",
            "META-INF/encryption.xml")

    errors = [c for c in checks if c["level"] == "error"]
    warnings = [c for c in checks if c["level"] == "warning"]
    report = {
        "file": os.path.abspath(ep.path),
        "epub_version": ep.version,
        "toc_entries": toc_count,
        "spine_docs": len(ep.spine_docs()),
        "summary": {"errors": len(errors), "warnings": len(warnings),
                    "checks": len(checks)},
        "checks": checks,
        "verdict": "PASS" if not errors else "FAIL",
    }
    print("校验: %s  |  error %d  warning %d  |  目录 %d 项  |  章节 %d 个" %
          (report["verdict"], len(errors), len(warnings), toc_count,
           report["spine_docs"]))
    for c in errors + warnings:
        print("  [%s] %s: %s%s" % (c["level"], c["code"], c["message"],
                                    ("  ← " + c["detail"]) if c["detail"] else ""))
    if args.output:
        json_dump(args.output, report)
        result(args.output, verdict=report["verdict"])
    ep.close()
    if errors and args.strict:
        sys.exit(EXIT_FAIL)
    return 0


if __name__ == "__main__":
    sys.exit(main())
