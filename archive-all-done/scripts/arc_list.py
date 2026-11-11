#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""arc-list：不解压列出包内条目。zip 走 infolist，可列出加密条目而无需密码。"""
import argparse
import json
import os
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arc_common as ac


def main():
    ap = argparse.ArgumentParser(description="查看压缩包清单")
    ap.add_argument("--input", required=True)
    ap.add_argument("--password", help="非 zip 加密包需要")
    ap.add_argument("--format", help="强制指定输入格式")
    ap.add_argument("--limit", type=int, default=0, help="只显示前 N 条，0=全部")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    args = ap.parse_args()

    try:
        ac.need_exists(args.input)
        fmt = ac.normalize_fmt(args.format) if args.format else ac.detect_format(args.input)
        if fmt == "zip":
            with zipfile.ZipFile(args.input) as z:
                entries = [ac.Entry(i.filename, i.file_size, i.compress_size,
                                    i.date_time, i.is_dir(),
                                    bool(i.flag_bits & 0x1), i.CRC)
                           for i in z.infolist()]
        else:
            entries = ac.list_entries(args.input, fmt, args.password)
        if args.json:
            print(json.dumps({"format": fmt, "count": len(entries),
                              "entries": [e._asdict() for e in entries]},
                             ensure_ascii=False, indent=2))
        else:
            ac.print_entries(entries, args.limit or None)
            print("共 %d 条 | 格式 %s | 原始合计 %s"
                  % (len(entries), fmt.upper(),
                     ac.human(sum(e.size for e in entries if not e.is_dir))))
        return 0
    except ac.ArchiveError as exc:
        print("错误：%s" % exc, file=sys.stderr)
        return exc.code
    except (zipfile.BadZipFile, OSError, EOFError) as exc:
        print("错误：无法读取压缩包：%s" % exc, file=sys.stderr)
        return ac.EXIT_CORRUPT


if __name__ == "__main__":
    sys.exit(main())
