#!/usr/bin/env python3
"""把扫描版 PDF 变成可搜索 PDF：原图不动，叠一层不可见文字。

流程：按 dpi 渲染每页 → OCR 拿到文字框（像素坐标）→ 换算成 PDF 点 → 用
render_mode=3（不可见）写入文字层。这样原版式 100% 保留，选中/搜索/复制却有字。

取舍：
- 文字层用 PyMuPDF 内置 CJK 字体（china-s），不依赖系统装了哪套中文字体。
- 一个框里的文字放不下时逐级缩小字号，仍放不下就退回单点写入（可能略微超出
  框宽），宁可位置略有偏差也不丢字——可搜索性优先于像素级对齐。
- 旋转页用 derotation_matrix 反变换，避免文字层与原图错位。
"""

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ocr_core  # noqa: E402


def load_pymupdf():
    try:
        import pymupdf
        return pymupdf
    except ImportError:
        try:
            import fitz as pymupdf
            return pymupdf
        except ImportError:
            raise SystemExit(
                "缺少 PyMuPDF，无法写回文字层：python scripts/bootstrap.py install --pdf")


def insert_block(page, rect, text, pymupdf):
    """Try shrinking font sizes until the text fits, then fall back to a point."""
    height = max(1.0, rect.height)
    for factor in (0.82, 0.7, 0.58, 0.46, 0.36):
        size = max(3.0, height * factor)
        try:
            leftover = page.insert_textbox(rect, text, fontsize=size,
                                           fontname="china-s", render_mode=3,
                                           align=0)
        except Exception:  # noqa: BLE001 - fall through to the point writer
            break
        if leftover >= 0:
            return "box", size
    try:
        page.insert_text((rect.x0, rect.y1 - 1.0), text, fontsize=max(3.0, height * 0.8),
                         fontname="china-s", render_mode=3)
        return "point", max(3.0, height * 0.8)
    except Exception:  # noqa: BLE001 - last resort: skip this block
        return "skipped", 0.0


def process(path, ns):
    pymupdf = load_pymupdf()
    source = Path(path).resolve()
    doc = pymupdf.open(str(source))
    if doc.needs_pass and not (ns.password and doc.authenticate(ns.password)):
        raise SystemExit("PDF 已加密，需要正确的 --password")

    rendered = ocr_core.render_pdf(source, Path(ns.workdir) / "png", dpi=ns.dpi,
                                   pages=ns.pages, password=ns.password)
    if not rendered:
        raise SystemExit("没有可处理的页面（检查 --pages）")

    scale = 72.0 / float(ns.dpi)
    pages, total_blocks, scores = [], 0, []
    existing_text_pages = []
    for page_no, png in rendered:
        blocks, backend = ocr_core.recognize(png, ns.engine, ns.min_score)
        page = doc[page_no - 1]
        if page.get_text().strip():
            existing_text_pages.append(page_no)
        inserted = 0
        for block in blocks:
            box = block.get("box")
            if not box:
                continue
            rect = pymupdf.Rect(box[0] * scale, box[1] * scale,
                                box[2] * scale, box[3] * scale)
            if page.rotation:
                rect = rect * page.derotation_matrix
            rect.normalize()
            if rect.width < 1 or rect.height < 1:
                continue
            mode, size = insert_block(page, rect, block["text"], pymupdf)
            if mode != "skipped":
                inserted += 1
        total_blocks += inserted
        score = ocr_core.mean_score(blocks)
        if score is not None:
            scores.append(score)
        pages.append({"page": page_no, "blocks": len(blocks), "inserted": inserted,
                      "mean_score": score, "engine": backend})

    target = Path(ns.output).resolve()
    if target == source:
        raise SystemExit("输出不能覆盖输入：%s" % target)
    target.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(target), garbage=4, deflate=True)
    page_count = doc.page_count
    doc.close()

    warnings = []
    if existing_text_pages:
        warnings.append("这些页原本就有文字层，叠加后可能出现重复文本：%s"
                        % ",".join(str(p) for p in existing_text_pages[:20]))
    return {
        "output": str(target), "pages": page_count, "pages_processed": len(rendered),
        "blocks_inserted": total_blocks, "dpi": ns.dpi,
        "mean_score": round(sum(scores) / len(scores), 4) if scores else None,
        "detail": pages,
        "bytes": target.stat().st_size,
        "warnings": warnings,
    }


def main():
    p = argparse.ArgumentParser(description="扫描 PDF → 可搜索 PDF（不可见文字层）")
    p.add_argument("input")
    p.add_argument("-o", "--output", required=True)
    p.add_argument("-p", "--password")
    p.add_argument("--dpi", type=int, default=200)
    p.add_argument("--engine", default="auto", choices=("auto", "rapidocr", "tesseract"))
    p.add_argument("--min-score", type=float, default=0.0)
    p.add_argument("--pages", help="1-based 页码范围，如 3-5,7")
    p.add_argument("--workdir",
                   help="临时渲染目录，默认系统临时目录下的 ocr-searchable-<文件名>")
    ns = p.parse_args()

    if not ns.workdir:
        ns.workdir = str(Path(tempfile.gettempdir()) / "ocr-searchable"
                         / Path(ns.input).stem)
    Path(ns.workdir).mkdir(parents=True, exist_ok=True)
    print(json.dumps(process(ns.input, ns), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
