#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""arc-batch：批量压缩 / 批量解压，单份失败不中断整批。"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arc_common as ac

ARCHIVE_EXT = tuple(ext for ext, _ in ac.EXT_FMT)


def main():
    ap = argparse.ArgumentParser(description="批量压缩 / 解压")
    ap.add_argument("--input-dir", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--direction", choices=("pack", "unpack"), default="pack")
    ap.add_argument("--format", default="zip", help="pack 时的输出格式")
    ap.add_argument("--level", type=int, default=6)
    ap.add_argument("--password")
    ap.add_argument("--on-conflict", choices=("rename", "overwrite", "skip"),
                    default="rename")
    args = ap.parse_args()

    try:
        ac.need_exists(args.input_dir)
        if not os.path.isdir(args.input_dir):
            ac.fail("--input-dir 必须是目录", ac.EXIT_IO)
        os.makedirs(args.output_dir, exist_ok=True)
        fmt = ac.normalize_fmt(args.format)
        names = sorted(os.listdir(args.input_dir))
        ok, failed = 0, []
        for name in names:
            src = os.path.join(args.input_dir, name)
            try:
                if args.direction == "pack":
                    if name.lower().endswith(ARCHIVE_EXT):
                        continue
                    out = os.path.join(args.output_dir,
                                       os.path.splitext(name)[0] + ac.ext_for(fmt))
                    out = ac.conflict_path(out, args.on_conflict)
                    if out is None:
                        continue
                    items = ac.collect_paths([src])
                    ac.write_members(out, ac.files_to_members(items), fmt=fmt,
                                     level=args.level, force_fmt=fmt)
                else:
                    if not (os.path.isfile(src) and name.lower().endswith(ARCHIVE_EXT)):
                        continue
                    outdir = os.path.join(args.output_dir, os.path.splitext(name)[0])
                    ac.extract_archive(src, outdir, ac.detect_format(src),
                                       args.password, on_conflict=args.on_conflict)
                ok += 1
                print("  [OK] %s" % name)
            except ac.ArchiveError as exc:
                failed.append((name, str(exc)))
                print("  [FAIL] %s -> %s" % (name, exc), file=sys.stderr)
            except Exception as exc:
                failed.append((name, str(exc)))
                print("  [FAIL] %s -> %s" % (name, exc), file=sys.stderr)
        ac.result(args.output_dir, 方向=args.direction, 成功=ok, 失败=len(failed))
        if failed:
            print("失败明细：" + "; ".join("%s(%s)" % (n, m) for n, m in failed[:5]))
        return 0 if ok else ac.EXIT_FAIL
    except ac.ArchiveError as exc:
        print("错误：%s" % exc, file=sys.stderr)
        return exc.code


if __name__ == "__main__":
    sys.exit(main())
