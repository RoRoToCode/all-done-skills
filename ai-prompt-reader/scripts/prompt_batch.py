"""prompt-batch：扫一个目录，汇总每张图读到的工具、参数与提示词摘要。"""
import argparse
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prompt_meta import MetaReadError          # noqa: E402
from prompt_parse import load                  # noqa: E402
from prompt_report import head_words, table_head, table_row  # noqa: E402

COLS = ["文件", "格式", "生成工具", "模型", "Seed", "Steps", "Sampler", "CFG",
        "画布", "生成尺寸", "正向字数", "正向提示词", "反向提示词", "备注"]


def collect(root, exts, recursive):
    if recursive:
        for d, _sub, files in os.walk(root):
            for fn in files:
                if os.path.splitext(fn)[1].lower() in exts:
                    yield os.path.join(d, fn)
    else:
        for fn in sorted(os.listdir(root)):
            p = os.path.join(root, fn)
            if os.path.isfile(p) and os.path.splitext(fn)[1].lower() in exts:
                yield p


def grab(params, *keys):
    low = {k.lower(): v for k, v in params}
    for k in keys:
        if k.lower() in low:
            return low[k.lower()]
    return ""


def main():
    ap = argparse.ArgumentParser(description="批量读取目录下的 AI 图片提示词")
    ap.add_argument("--input-dir", required=True)
    ap.add_argument("--recursive", action="store_true", help="含子目录")
    ap.add_argument("--ext", default="png,jpg,jpeg,webp", help="扩展名，逗号分隔")
    ap.add_argument("--output", default=None, help="CSV 输出路径；省略写 prompt-batch.csv 到当前目录")
    ap.add_argument("--no-csv", action="store_true", help="只看屏幕表格，不写 CSV")
    ap.add_argument("--preview", type=int, default=40, help="屏幕上前瞻提示词字数")
    args = ap.parse_args()

    if not os.path.isdir(args.input_dir):
        sys.stderr.write("目录不存在：%s\n" % args.input_dir)
        return 2

    exts = {"." + e.strip().lower().lstrip(".") for e in args.ext.split(",") if e.strip()}
    files = sorted(collect(args.input_dir, exts, args.recursive))
    if not files:
        sys.stderr.write("目录里没有 %s 文件。\n" % "/".join(sorted(exts)))
        return 2

    rows, hit, empty, broken = [], 0, 0, 0
    print(table_head())
    print("-" * 104)
    for p in files:
        rel = os.path.relpath(p, args.input_dir)
        try:
            meta, info = load(p)
        except MetaReadError as e:
            broken += 1
            rows.append([rel] + [""] * 12 + [str(e)])
            print(table_row(rel, "读取失败", "", "", str(e)[:30]))
            continue
        size = "%dx%d" % meta["size"] if meta["size"] else ""
        if not info["tool"]:
            empty += 1
            why = "无文字块（元数据已被剥离）" if not meta["blocks"] else "非 AI 参数格式"
            rows.append([rel, meta["format"]] + [""] * 6 + [size, "", "", "", "", why])
            print(table_row(rel, "读不出", "", "", why))
            continue
        hit += 1
        params = info["params"]
        seed = grab(params, "Seed")
        rows.append([rel, meta["format"], info["tool"], grab(params, "Model"), seed,
                     grab(params, "Steps"), grab(params, "Sampler", "Sampler name"),
                     grab(params, "CFG scale", "CFG"), size, grab(params, "Size"),
                     len(info["positive"] or ""), info["positive"] or "",
                     info["negative"] or "", "；".join(info.get("notes") or [])])
        print(table_row(rel, info["tool"], seed, grab(params, "Model"),
                        info["positive"] or "", args.preview))

    total = len(files)
    print("-" * 104)
    print("共 %d 张：读到 %d，读不出 %d，打不开 %d" % (total, hit, empty, broken))
    if empty:
        print("读不出的多半是被平台剥掉了元数据（转发、压缩、截图都会）。")
    if broken:
        print("打不开的检查格式：只支持 PNG / JPEG / WebP，AVIF / HEIC 需先转格式。")

    if not args.no_csv:
        out = args.output or os.path.join(os.getcwd(), "prompt-batch.csv")
        d = os.path.dirname(os.path.abspath(out))
        if d:
            os.makedirs(d, exist_ok=True)
        with open(out, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(COLS)
            w.writerows(rows)
        print("CSV：%s" % out)
    return 0 if hit else 3


if __name__ == "__main__":
    sys.exit(main())
