#!/usr/bin/env python3
"""文本统计：字符 / 行 / 段落 / 中英文构成 / 高频词。

中文没有分词依赖，所以词频只统计「拉丁词 + 数字」以及「单个汉字」，不做
伪分词——宁可给出可复现的字频，也不猜词边界。
"""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import txt_common as C  # noqa: E402

C.main_guard()

CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
LATIN_WORD = re.compile(r"[A-Za-z][A-Za-z0-9'’\-]*")
NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
CJK_PUNCT = re.compile(r"[\u3000-\u303f\uff00-\uffef]")
SPACE = re.compile(r"\s")


def main():
    p = argparse.ArgumentParser(description="文本统计与字频/词频")
    p.add_argument("input")
    p.add_argument("-o", "--output", help="JSON 报告路径，默认打印到 stdout")
    p.add_argument("--top", type=int, default=20, help="高频项数量，默认 20")
    p.add_argument("--from", dest="source_encoding")
    p.add_argument("--stopwords", help="停用词文件，每行一个（默认不过滤）")
    ns = p.parse_args()

    text, info = C.read_text(ns.input, ns.source_encoding)
    lines = text.splitlines()
    paragraphs = [block for block in re.split(r"\n\s*\n", text) if block.strip()]
    chars = len(text)
    no_space = len(SPACE.sub("", text))

    cjk_chars = CJK.findall(text)
    latin_words = [w.lower() for w in LATIN_WORD.findall(text)]
    numbers = NUMBER.findall(text)

    stop = set()
    if ns.stopwords:
        for line in Path(ns.stopwords).read_text(encoding="utf-8").splitlines():
            token = line.strip()
            if token:
                stop.add(token)

    word_counts = Counter(w for w in latin_words if w not in stop)
    char_counts = Counter(ch for ch in cjk_chars if ch not in stop)
    longest = max(lines, key=len) if lines else ""

    payload = {
        "input": str(Path(ns.input).resolve()),
        "encoding": info["encoding"],
        "bytes": info["bytes"],
        "chars": chars,
        "chars_no_space": no_space,
        "lines": len(lines),
        "non_empty_lines": sum(1 for line in lines if line.strip()),
        "paragraphs": len(paragraphs),
        "cjk_chars": len(cjk_chars),
        "latin_words": len(latin_words),
        "numbers": len(numbers),
        "cjk_punct": len(CJK_PUNCT.findall(text)),
        "digits": sum(ch.isdigit() for ch in text),
        "mean_line_chars": round(no_space / len(lines), 1) if lines else 0,
        "longest_line_chars": len(longest),
        "reading_minutes_zh": round(len(cjk_chars) / 300.0, 1),
        "top_words": word_counts.most_common(ns.top),
        "top_cjk_chars": char_counts.most_common(ns.top),
    }
    body = json.dumps(payload, ensure_ascii=False, indent=2)
    if ns.output:
        target = Path(ns.output).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
        return C.emit({"output": str(target), "chars": chars, "lines": len(lines),
                       "cjk_chars": len(cjk_chars),
                       "top_word": payload["top_words"][0] if payload["top_words"] else None})
    print(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
