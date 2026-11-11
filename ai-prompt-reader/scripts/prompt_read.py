"""prompt-read：读一张图的提示词与参数，排成可读文本。"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prompt_meta import MetaReadError          # noqa: E402
from prompt_parse import load                  # noqa: E402
from prompt_report import render               # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="读取 AI 图片里的提示词与生成参数")
    ap.add_argument("--input", required=True, help="图片路径（PNG / JPEG / WebP）")
    ap.add_argument("--max", type=int, default=0, help="提示词截断字数，0 为完整显示")
    args = ap.parse_args()

    if not os.path.isfile(args.input):
        sys.stderr.write("找不到文件：%s\n" % args.input)
        return 2
    try:
        meta, info = load(args.input)
    except MetaReadError as e:
        sys.stderr.write("%s\n" % e)
        return 2

    print(render(args.input, meta, info, args.max))
    return 0 if info["tool"] else 3


if __name__ == "__main__":
    sys.exit(main())
