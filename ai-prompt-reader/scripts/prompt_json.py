"""prompt-json：整份元数据导出为 JSON，便于脚本二次处理。"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prompt_meta import MetaReadError          # noqa: E402
from prompt_parse import load                  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="导出结构化 JSON")
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", default=None, help="写入文件；省略则打印到屏幕")
    ap.add_argument("--raw", action="store_true", help="附带原始元数据块全文")
    ap.add_argument("--indent", type=int, default=2)
    args = ap.parse_args()

    if not os.path.isfile(args.input):
        sys.stderr.write("找不到文件：%s\n" % args.input)
        return 2
    try:
        meta, info = load(args.input)
    except MetaReadError as e:
        sys.stderr.write("%s\n" % e)
        return 2

    blocks = []
    for b in meta["blocks"]:
        item = {"name": b["name"], "source": b["source"], "chars": len(b["text"])}
        if args.raw:
            item["text"] = b["text"]
        blocks.append(item)

    doc = {
        "file": os.path.abspath(args.input),
        "format": meta["format"],
        "size": list(meta["size"]) if meta["size"] else None,
        "tool": info["tool"],
        "positive": info["positive"],
        "negative": info["negative"],
        "params": {k: v for k, v in info["params"] if k},
        "blocks": blocks,
        "notes": info.get("notes") or [],
    }
    text = json.dumps(doc, ensure_ascii=False, indent=args.indent) + "\n"

    if args.output:
        d = os.path.dirname(os.path.abspath(args.output))
        if d:
            os.makedirs(d, exist_ok=True)
        with open(args.output, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        print("已写入 %s  %d 字节" % (args.output, len(text.encode("utf-8"))))
    else:
        sys.stdout.write(text)
    return 0 if info["tool"] else 3


if __name__ == "__main__":
    sys.exit(main())
