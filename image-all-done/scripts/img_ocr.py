"""img-ocr：从图片提取文字。引擎顺序 rapidocr → tesseract，可用 --engine 强制。

rapidocr 自带模型、无需外部二进制，中文效果通常优于缺语言包的 Tesseract；
Tesseract 作为兜底，只在装了二进制与 chi_sim 时才可用。两个引擎都拿不到时
明确报错并给安装命令，不静默输出空文件。
"""
import argparse
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from img_common import need_pillow, no_overwrite, guard_import


def _rapidocr_text(path, min_score):
    from rapidocr_onnxruntime import RapidOCR
    engine = RapidOCR()
    result, _ = engine(str(path))
    items = []
    for box, text, score in result or []:
        text = (text or "").strip()
        if not text or float(score) < min_score:
            continue
        ys = [float(p[1]) for p in box]
        xs = [float(p[0]) for p in box]
        items.append({"text": text, "y": min(ys), "h": max(ys) - min(ys),
                      "x": min(xs), "score": float(score)})
    if not items:
        return "", 0, 0.0
    heights = sorted(i["h"] for i in items)
    tol = max(6.0, heights[len(heights) // 2] * 0.6)
    items.sort(key=lambda i: (i["y"], i["x"]))
    lines, current = [], [items[0]]
    for item in items[1:]:
        anchor = sum(i["y"] for i in current) / len(current)
        if abs(item["y"] - anchor) <= tol:
            current.append(item)
        else:
            lines.append(current)
            current = [item]
    lines.append(current)
    rows = []
    for line in lines:
        line.sort(key=lambda i: i["x"])
        rows.append(" ".join(i["text"] for i in line))
    mean = sum(i["score"] for i in items) / len(items)
    return "\n".join(rows), len(items), mean


def _tesseract_text(path, lang):
    if shutil.which("tesseract") is None:
        raise SystemExit(
            "缺少 Tesseract 二进制：Windows 用官方 installer 安装并加入 PATH，"
            "中文需额外装 chi_sim 语言包；或改用 rapidocr 引擎。")
    pytesseract = guard_import("pytesseract", "pip install pytesseract")
    from PIL import Image
    with Image.open(path) as img:
        return pytesseract.image_to_string(img, lang=lang)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", default=None, help="输出 txt 路径，省略则打印到终端")
    ap.add_argument("--lang", default="chi_sim+eng", help="Tesseract 语言，如 chi_sim+eng")
    ap.add_argument("--engine", default="auto", choices=("auto", "rapidocr", "tesseract"))
    ap.add_argument("--min-score", type=float, default=0.0)
    args = ap.parse_args()

    need_pillow()
    if args.output:
        no_overwrite(args.input, args.output)

    text, engine, detail = "", None, ""
    if args.engine in ("auto", "rapidocr"):
        try:
            text, count, mean = _rapidocr_text(args.input, args.min_score)
            engine, detail = "rapidocr", "blocks=%d mean=%.4f" % (count, mean)
        except ImportError:
            if args.engine == "rapidocr":
                raise SystemExit(
                    "缺少 rapidocr：%s -m pip install rapidocr-onnxruntime"
                    % sys.executable)
        except SystemExit:
            raise
        except Exception as exc:  # noqa: BLE001 - engine failure, fall through
            detail = "rapidocr 失败：%s" % exc

    if not text and args.engine in ("auto", "tesseract"):
        text = _tesseract_text(args.input, args.lang)
        engine = "tesseract"
        detail = "lang=%s" % args.lang

    if not text.strip():
        sys.stderr.write("没有识别到文字（引擎=%s）%s\n"
                         % (engine, ("；" + detail) if detail else ""))
        sys.exit(1)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(text)
        print("已识别 %d 字符（引擎 %s，%s），写入 %s"
              % (len(text), engine, detail, args.output))
    else:
        print(text)


if __name__ == "__main__":
    main()
