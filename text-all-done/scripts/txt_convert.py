#!/usr/bin/env python3
"""转换文本编码与换行风格，源编码可自动嗅探。

不带 -o 时写到 <stem>-<目标编码>.txt，绝不覆盖输入；只想看清楚源文件是什么
编码就加 --check，不会产生任何文件。
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import txt_common as C  # noqa: E402

C.main_guard()


def main():
    p = argparse.ArgumentParser(description="文本编码 / 换行转换")
    p.add_argument("input")
    p.add_argument("-o", "--output")
    p.add_argument("--to", default="utf-8",
                   help="目标编码，默认 utf-8；支持 utf-8-bom/gb18030/big5/utf-16/utf-16be/latin-1")
    p.add_argument("--from", dest="source_encoding", help="强制指定源编码，默认自动嗅探")
    p.add_argument("--newline", default="keep", choices=("keep", "lf", "crlf", "cr"))
    p.add_argument("--strict", action="store_true", help="解码失败直接报错，不静默替换")
    p.add_argument("--check", action="store_true", help="只探测，不写文件")
    ns = p.parse_args()

    text, info = C.read_text(ns.input, ns.source_encoding, ns.strict)
    detected_newline = C.detect_newline(text)
    if ns.check:
        return C.emit({"file": str(Path(ns.input).resolve()), "encoding": info["encoding"],
                       "bom": info["bom"], "bytes": info["bytes"], "lines": info["lines"],
                       "newline": detected_newline, "check_only": True})

    target = ns.output or C.derive_output(ns.input, "-" + ns.to.replace("/", "-"))
    source, target = C.guard_paths(ns.input, target)
    written = C.write_text(target, text, ns.to, ns.newline or detected_newline)
    return C.emit({"output": str(written), "from_encoding": info["encoding"],
                   "to_encoding": C.normalise_encoding(ns.to),
                   "newline": ns.newline, "bytes_in": info["bytes"],
                   "bytes_out": written.stat().st_size,
                   "bom": C.normalise_encoding(ns.to) == "utf-8-sig"})


if __name__ == "__main__":
    sys.exit(main())
