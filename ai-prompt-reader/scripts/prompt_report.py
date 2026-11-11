"""输出层：把解释结果排成人能看的文本。"""
import os
import unicodedata

from prompt_parse import head_words

_LABEL_W = 18


def _width(s):
    """中文占两格，按显示宽度算，标签才对得齐。"""
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)


def _pad(s, width):
    return s + " " * max(1, width - _width(s))


def _fit(s, width):
    """按显示宽度截断并补齐，中文不会把后面的列挤歪。"""
    s = s or ""
    out, w = "", 0
    for ch in s:
        cw = 2 if unicodedata.east_asian_width(ch) in "WF" else 1
        if w + cw > width - 1:
            break
        out += ch
        w += cw
    return _pad(out, width)


def _wrap(text, width=None):
    """按行前缀缩进，保留原有换行。"""
    if not text:
        return []
    body = text if not width else text[:width] + "…"
    return ["    " + ln.rstrip() for ln in body.split("\n") if ln.strip()]


def render(path, meta, info, max_chars=0):
    lines = [os.path.basename(path)]
    size = meta.get("size")
    dims = "%dx%d" % size if size else "尺寸未知"
    blocks = [b["name"] for b in meta["blocks"]]
    lines.append("  容器 %s  %s  元数据块 %d 个%s"
                 % (meta["format"], dims, len(blocks),
                    ("：" + ", ".join(blocks)) if blocks else "（无）"))

    if not info["tool"]:
        lines.append("  未识别到 AI 生成参数。")
        lines.extend(_hints(meta))
        return "\n".join(lines)

    lines.append("  生成工具 %s" % info["tool"])

    if info["positive"]:
        lines.append("")
        lines.append("  正向提示词")
        lines.extend(_wrap(info["positive"], max_chars))
    if info["negative"]:
        lines.append("")
        lines.append("  反向提示词")
        lines.extend(_wrap(info["negative"], max_chars))

    if info["params"]:
        lines.append("")
        lines.append("  参数")
        for k, v in info["params"]:
            if v in (None, ""):
                continue
            lines.append("    " + _pad(k, _LABEL_W) + v)

    for n in info.get("notes") or []:
        if n:
            lines.append("  注: %s" % n)
    if not info["positive"] and not info["negative"]:
        lines.extend(_hints(meta))
    return "\n".join(lines)


def _hints(meta):
    blocks = meta["blocks"]
    size = meta.get("size")
    out = []
    if not blocks:
        out.append("  原因：文件里没有任何文字块 —— 通常是社交平台 / 图床 / 聊天软件")
        out.append("  转发时压缩并剥掉了元数据，文件本身已经没有这些数据。")
        out.append("  可核对：原图是否还在、是否被截图或二次保存过。")
    else:
        out.append("  原因：有元数据块，但不是已知的 AI 参数格式（可能是相机 EXIF 或")
        out.append("  其他工具写入）。用 prompt-raw 看原始内容。")
    if size and min(size) < 512:
        out.append("  另注：%dx%d 偏小，像是缩略图或截图，原图参数多半已丢失。" % size)
    return out


def table_row(path, tool, seed, model, text, width=44):
    return " ".join([
        _fit(os.path.basename(path), 30),
        _fit(tool or "—", 14),
        _fit(seed or "—", 12),
        _fit(model or "—", 26),
        head_words(text, width),
    ])


def table_head():
    return " ".join([_fit("文件", 30), _fit("工具", 14), _fit("Seed", 12),
                     _fit("模型", 26), "正向提示词"])
