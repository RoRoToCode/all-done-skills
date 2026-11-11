"""prompt-raw：列原始元数据块，核对或处理未知格式时用。"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prompt_meta import MetaReadError, read_meta   # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="展开原始元数据块")
    ap.add_argument("--input", required=True)
    ap.add_argument("--name", default=None, help="只看某个块，如 parameters / prompt / Comment")
    ap.add_argument("--full", action="store_true", help="打印块全文（默认只显示开头）")
    ap.add_argument("--limit", type=int, default=400, help="不加 --full 时每个块显示多少字")
    args = ap.parse_args()

    if not os.path.isfile(args.input):
        sys.stderr.write("找不到文件：%s\n" % args.input)
        return 2
    try:
        meta = read_meta(args.input)
    except MetaReadError as e:
        sys.stderr.write("%s\n" % e)
        return 2

    blocks = meta["blocks"]
    if args.name:
        blocks = [b for b in blocks if b["name"].lower() == args.name.lower()]

    size = meta.get("size")
    print("%s  %s  %s  元数据块 %d 个"
          % (os.path.basename(args.input), meta["format"],
             "%dx%d" % size if size else "尺寸未知", len(blocks)))
    if not blocks:
        print("  没有匹配的元数据块。")
        return 3

    for b in blocks:
        print("\n[%s]  来源 %s  %d 字" % (b["name"], b["source"], len(b["text"])))
        body = b["text"] if args.full else b["text"][:args.limit]
        print(body.rstrip())
        if not args.full and len(b["text"]) > args.limit:
            print("…（余下 %d 字，加 --full 看全文）" % (len(b["text"]) - args.limit))
    return 0


if __name__ == "__main__":
    sys.exit(main())
