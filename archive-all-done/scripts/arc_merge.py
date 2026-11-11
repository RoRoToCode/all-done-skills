#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""arc-merge：把多个压缩包（含分卷清单）的内容合并进一个新包。"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arc_common as ac


def expand(inputs):
    out = []
    for raw in inputs:
        p = os.path.abspath(raw)
        ac.need_exists(p)
        if p.lower().endswith(".manifest.json"):
            with open(p, encoding="utf-8") as f:
                man = json.load(f)
            for name in man.get("parts", []):
                q = os.path.join(os.path.dirname(p), name)
                ac.need_exists(q)
                out.append(q)
            print("清单展开 %s：%d 个分卷"
                  % (os.path.basename(p), len(man.get("parts", []))))
        else:
            out.append(p)
    return out


def main():
    ap = argparse.ArgumentParser(description="合并压缩包")
    ap.add_argument("--inputs", nargs="+", required=True,
                    help="多个压缩包，或 arc-split 生成的 .manifest.json")
    ap.add_argument("--output", required=True)
    ap.add_argument("--format", help="输出格式，默认按输出扩展名")
    ap.add_argument("--password", help="输入包密码（多个包共用）")
    ap.add_argument("--level", type=int, default=6)
    args = ap.parse_args()

    try:
        paths = expand(args.inputs)
        if not paths:
            ac.fail("没有可合并的压缩包", ac.EXIT_IO)
        for p in paths:
            ac.no_overwrite(p, args.output)
        out_fmt = ac.normalize_fmt(args.format) if args.format else ac.detect_format(args.output)
        merged, seen, renamed = [], set(), 0
        for p in paths:
            for e, data in ac.read_members(p, ac.detect_format(p), args.password):
                name = e.name
                if name in seen:
                    stem, ext = os.path.splitext(name)
                    i = 2
                    while "%s (%d)%s" % (stem, i, ext) in seen:
                        i += 1
                    name = "%s (%d)%s" % (stem, i, ext)
                    renamed += 1
                seen.add(name)
                merged.append((e._replace(name=name), data))
        ac.write_members(args.output, merged, fmt=out_fmt, level=args.level,
                         force_fmt=out_fmt)
        ac.result(args.output, 格式=out_fmt.upper(), 来源包=len(paths),
                  合并条目=len(merged), 自动改名=renamed)
        return 0
    except ac.ArchiveError as exc:
        print("错误：%s" % exc, file=sys.stderr)
        return exc.code
    except (json.JSONDecodeError, OSError) as exc:
        print("错误：读取清单或包体失败：%s" % exc, file=sys.stderr)
        return ac.EXIT_CORRUPT


if __name__ == "__main__":
    sys.exit(main())
