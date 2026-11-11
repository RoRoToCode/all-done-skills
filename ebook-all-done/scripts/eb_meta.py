#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""eb-meta：读取 / 改写 OPF 元数据，另存新 EPUB。"""
import argparse
import json
import os
import sys
from xml.etree import ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eb_common import (DC_NS, OPF_NS, Epub, edit_opf, meta_element,
                       result, rewrite_epub, setup_stdout, EXIT_USAGE)

DC_KEYS = {"title", "creator", "language", "identifier", "publisher",
           "description", "subject", "rights", "contributor", "date"}


def main():
    setup_stdout()
    ap = argparse.ArgumentParser(description="电子书元数据读取与修改")
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", help="另存为新的 EPUB")
    ap.add_argument("--show", action="store_true", help="只查看，不写文件")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE",
                    help="修改一项，可重复传入（如 title=新书名）")
    ap.add_argument("--spec", help="JSON 文件，形如 {\"title\": \"…\", \"creator\": [\"甲\",\"乙\"]}")
    args = ap.parse_args()

    ep = Epub(args.input)
    if args.show:
        print("书名: %s" % ep.title())
        for k, vals in ep.metadata.items():
            print("  %-14s %s" % (k, " | ".join(vals)))
        for attrs, text in ep.meta_tags:
            if attrs.get("name"):
                print("  meta:%-10s %s" % (attrs["name"], attrs.get("content") or text))
        ep.close()
        return 0

    changes = {}
    if args.spec:
        with open(args.spec, encoding="utf-8") as f:
            spec = json.load(f)
        for k, v in spec.items():
            changes[k] = v if isinstance(v, list) else [str(v)]
    for pair in args.set:
        if "=" not in pair:
            from eb_common import die
            die("--set 需要 key=value 形式：%s" % pair, EXIT_USAGE)
        k, v = pair.split("=", 1)
        k = k.strip().lower()
        if k not in DC_KEYS and k != "series":
            from eb_common import die
            die("未知元数据键 %s（可用：%s, series）" %
                (k, ", ".join(sorted(DC_KEYS))), EXIT_USAGE)
        changes.setdefault(k, []).append(v.strip())
    if not changes:
        from eb_common import die
        die("没有要修改的内容：给 --set / --spec，或用 --show 查看", EXIT_USAGE)
    if not args.output:
        from eb_common import die
        die("改写元数据需要 --output（本技能不原地修改源文件）", EXIT_USAGE)
    from eb_common import no_overwrite
    no_overwrite(args.input, args.output)

    def apply(root):
        md = meta_element(root)
        for key, values in changes.items():
            if key == "series":
                tag = "{%s}meta" % OPF_NS
                for child in list(md):
                    if child.tag == tag and child.get("name") == "calibre:series":
                        md.remove(child)
                el = ET.SubElement(md, tag, {"name": "calibre:series",
                                             "content": values[-1]})
                el.text = None
                continue
            tag = "{%s}%s" % (DC_NS, key)
            for child in list(md):
                if child.tag == tag:
                    md.remove(child)
            for value in values:
                el = ET.SubElement(md, tag)
                el.text = value

    new_opf = edit_opf(ep, apply)
    rewrite_epub(ep, args.output, replacements={ep.opf_path: new_opf})
    for k, v in changes.items():
        print("  %s = %s" % (k, " | ".join(v)))
    result(args.output, 修改项=len(changes))
    ep.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
