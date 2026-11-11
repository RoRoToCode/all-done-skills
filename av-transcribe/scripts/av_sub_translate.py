#!/usr/bin/env python3
"""av-sub-translate：字幕翻译，保留原时间轴。

对接任何 OpenAI 兼容的 chat/completions 接口：
  - 默认指向本地 Ollama（http://localhost:11434/v1），全程不出本机；
  - 也可用 --endpoint / --api-key 指向远程服务。
源文件读入 SRT/VTT，逐批翻译文本、原样沿用时间戳，再按目标格式写出。
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from av_common import no_overwrite, ensure_parent, result
from av_sub_convert import parse, write_out

LANG = {
    "zh": "中文", "zh-cn": "简体中文", "zh-tw": "繁體中文",
    "en": "English", "ja": "日本語", "ko": "한국어", "fr": "Français",
    "de": "Deutsch", "es": "Español", "ru": "Русский", "pt": "Português",
    "it": "Italiano", "ar": "العربية", "th": "ไทย", "vi": "Tiếng Việt",
}


def lang_name(code):
    if not code:
        return "自动识别"
    return LANG.get(code.lower(), code)


def chat(endpoint, api_key, model, messages, timeout=180):
    url = endpoint.rstrip("/") + "/chat/completions"
    body = json.dumps({"model": model, "messages": messages,
                       "temperature": 0}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    if api_key:
        req.add_header("Authorization", "Bearer " + api_key)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:300]
        sys.stderr.write("翻译服务返回 HTTP %s：%s\n" % (e.code, detail))
        sys.exit(5)
    except urllib.error.URLError as e:
        sys.stderr.write(
            "无法连接翻译服务（%s）。\n"
            "默认需本地 Ollama：先 `ollama serve` 并 `ollama pull qwen2.5`；"
            "或用 --endpoint 指定其它 OpenAI 兼容服务。\n" % e.reason)
        sys.exit(5)
    try:
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        sys.stderr.write("翻译服务响应格式异常。\n")
        sys.exit(5)


def batch_prompt(source, target, items):
    numbered = "\n".join("%d: %s" % (i + 1, t) for i, t in enumerate(items))
    sys_msg = ("你是专业字幕翻译。把下面每条编号字幕翻译成%s，保留原意、语气自然。"
               "只输出同样数量的编号行，格式「N: 译文」，不要任何解释或空行。") % target
    usr_msg = "源语言：%s\n%s" % (source, numbered)
    return [{"role": "system", "content": sys_msg},
            {"role": "user", "content": usr_msg}]


_RESP = re.compile(r"^\s*(\d+)\s*[:.)、]\s*(.*)$")


def parse_response(text, n):
    got = {}
    for line in text.splitlines():
        m = _RESP.match(line)
        if m:
            idx = int(m.group(1))
            if 1 <= idx <= n:
                got[idx] = m.group(2).strip()
    if len(got) == n:
        return [got[i] for i in range(1, n + 1)]
    return None  # 数量不符，交给调用方回退


def translate_segments(segs, args):
    source = lang_name(args.source)
    target = lang_name(args.target)
    n = len(segs)
    out = [None] * n
    size = max(1, args.batch_size)
    for start in range(0, n, size):
        chunk = segs[start:start + size]
        items = [s["text"].strip() for s in chunk]
        resp = chat(args.endpoint, args.api_key, args.model,
                    batch_prompt(source, target, items))
        parsed = parse_response(resp, len(items))
        if parsed is None:
            # 批量子句数量对不上：逐条翻译兜底，保证一一对应
            parsed = []
            for it in items:
                msgs = [{"role": "system",
                         "content": "把下面这句字幕翻译成%s，只输出译文本身。" % target},
                        {"role": "user", "content": it}]
                parsed.append(chat(args.endpoint, args.api_key, args.model, msgs).strip())
        for j, txt in enumerate(parsed):
            out[start + j] = txt
        sys.stderr.write("  已翻译 %d/%d 条\n" % (min(start + size, n), n))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="源字幕 SRT/VTT")
    ap.add_argument("--output", required=True, help="译文输出，扩展名决定格式")
    ap.add_argument("--target", required=True, help="目标语言代码：zh/en/ja/ko/...")
    ap.add_argument("--source", default=None, help="源语言代码，留空自动")
    ap.add_argument("--to", default=None, help="输出格式 srt/vtt/lrc/txt/ass，默认同输入")
    ap.add_argument("--endpoint",
                    default=os.environ.get("AV_TRANSLATE_ENDPOINT", "http://localhost:11434/v1"),
                    help="OpenAI 兼容接口 base url，默认本地 Ollama")
    ap.add_argument("--model", default=os.environ.get("AV_TRANSLATE_MODEL", "qwen2.5"),
                    help="模型名，默认 qwen2.5（Ollama）")
    ap.add_argument("--api-key", default=os.environ.get("AV_TRANSLATE_API_KEY", ""),
                    help="密钥，本地 Ollama 可留空")
    ap.add_argument("--batch-size", type=int, default=20, help="每次请求送入的条数")
    args = ap.parse_args()

    no_overwrite(args.input, args.output)
    ensure_parent(args.output)

    segs = parse(args.input)
    if not segs:
        sys.stderr.write("未从源文件解析到字幕条目，请确认是 SRT/VTT 格式。\n")
        sys.exit(3)

    translated = translate_segments(segs, args)
    out_segs = [{"start": s["start"], "end": s["end"], "text": (t or "").strip()}
                for s, t in zip(segs, translated)]

    fmt = (args.to or os.path.splitext(args.output)[1].lower().lstrip(".")).lower()
    if fmt not in ("srt", "vtt", "lrc", "txt", "ass"):
        fmt = "srt"
    write_out(out_segs, args.output, fmt)
    result(args.output)
    print("  段数=%d  目标语言=%s  格式=%s" % (len(out_segs), args.target, fmt))


if __name__ == "__main__":
    main()
