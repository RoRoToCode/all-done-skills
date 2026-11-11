#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""arc-test：完整性校验（zip CRC + 全格式逐条读到底）。"""
import argparse
import os
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arc_common as ac


def main():
    ap = argparse.ArgumentParser(description="校验压缩包完整性")
    ap.add_argument("--input", required=True)
    ap.add_argument("--password", help="加密包密码")
    ap.add_argument("--format", help="强制指定输入格式")
    args = ap.parse_args()

    try:
        ac.need_exists(args.input)
        fmt = ac.normalize_fmt(args.format) if args.format else ac.detect_format(args.input)
        bad = []
        if fmt == "zip":
            with zipfile.ZipFile(args.input) as z:
                # testzip() 内部不给密码，加密包必须由下面的逐条 read 校验 CRC
                if not any(i.flag_bits & 0x1 for i in z.infolist()):
                    hit = z.testzip()
                    if hit:
                        bad.append(hit)
        count = total = 0
        for e, data in ac.read_members(args.input, fmt, args.password):
            if not e.is_dir:
                count += 1
                total += len(data or b"")
        if bad:
            print("校验失败：损坏条目 %s" % ", ".join(bad))
            return ac.EXIT_CORRUPT
        ac.result(args.input, 格式=fmt.upper(), 校验="通过",
                  已读条目=count, 原始字节=ac.human(total))
        return 0
    except ac.ArchiveError as exc:
        print("错误：%s" % exc, file=sys.stderr)
        return exc.code
    except Exception as exc:
        print("校验失败：包体损坏或无法完整读取：%s" % exc, file=sys.stderr)
        return ac.EXIT_CORRUPT


if __name__ == "__main__":
    sys.exit(main())
