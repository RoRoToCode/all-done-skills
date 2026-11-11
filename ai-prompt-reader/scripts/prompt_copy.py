"""prompt-copy：只吐提示词正文，方便直接粘到别的工具里。"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prompt_meta import MetaReadError          # noqa: E402
from prompt_parse import load                  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="导出可复制的提示词文本")
    ap.add_argument("--input", required=True)
    ap.add_argument("--part", choices=["positive", "negative", "both"], default="positive",
                    help="positive 只要正向（默认）；negative 只要反向；both 按 A1111 写法拼回一段")
    ap.add_argument("--output", default=None, help="写入文件；省略则打印到屏幕")
    args = ap.parse_args()

    if not os.path.isfile(args.input):
        sys.stderr.write("找不到文件：%s\n" % args.input)
        return 2
    try:
        _meta, info = load(args.input)
    except MetaReadError as e:
        sys.stderr.write("%s\n" % e)
        return 2

    pos, neg = info["positive"] or "", info["negative"] or ""
    if args.part == "positive":
        text = pos
    elif args.part == "negative":
        text = neg
    else:
        text = pos
        if neg:
            text = (pos + "\n\nNegative prompt: " + neg).strip()

    if not text.strip():
        sys.stderr.write("这张图读不出%s提示词。" % ("" if args.part == "both" else
                                                 "正向" if args.part == "positive" else "反向"))
        if not info["tool"]:
            sys.stderr.write("文件里没有可识别的 AI 元数据。")
        sys.stderr.write("\n")
        return 3

    if args.output:
        out_dir = os.path.dirname(os.path.abspath(args.output))
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(args.output, "w", encoding="utf-8", newline="\n") as f:
            f.write(text.rstrip() + "\n")
        print("已写入 %s  %d 字" % (args.output, len(text.strip())))
    else:
        sys.stdout.write(text.rstrip() + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
