# 常见任务配方

## 1. 单张图片

```bash
python scripts/ocr_cli.py shot.png -o out/
```

产物：`out/shot.md`、`out/shot.json`、`out/manifest.json`。

## 2. PDF / 扫描件

```bash
python scripts/ocr_cli.py scan.pdf -o out/ --dpi 300
```

- 页范围：`--pages 3-5,8`
- 加密文件：`--password ****`
- 产物：`out/scan.md`（带 `<!-- page N -->`）、`out/scan.json`、`out/pages/page-0001.txt…`

扫描件模糊或小字号时把 `--dpi` 提到 300；1600px 宽以上的整页图 200 dpi 通常够用。

## 3. 批量

```bash
python scripts/ocr_cli.py ./inbox -o out/batch
```

每个文件一个子目录（`out/batch/<文件名>/`），总目录 `manifest.json` 汇总份数、页数、平均置信度。

## 4. 表格 → CSV

```bash
python scripts/ocr_cli.py table.png -o out/ --table
python scripts/ocr_cli.py scan.pdf  -o out/ --table
```

`out/tables/page-0001.csv`（UTF-8-BOM）。表格必须**有框线或清晰列间距**，否则会被当成普通文本行。

## 5. 强制引擎 / 过滤低置信度

```bash
python scripts/ocr_cli.py scan.pdf -o out/ --engine tesseract
python scripts/ocr_cli.py poor.jpg -o out/ --min-score 0.6
```

`--min-score` 直接丢弃低于阈值的块，适合去掉噪点误识别；但印章、水印区域的文字也会一起丢掉。

## 6. 二次处理 JSON

`<stem>.json` 结构：

```json
{
  "source": "scan.pdf", "engine": "rapidocr", "dpi": 200,
  "page_count": 3, "mean_score": 0.9937,
  "pages": [
    {"page": 1, "image": "...page-0001.png", "text": "...",
     "blocks": [{"text": "合同编号", "score": 0.999, "box": [x0, y0, x1, y1]}]}
  ]
}
```

典型用法：按 `box[1]` 排序取首行当标题、按 `box[0]` 右半区取数字列、用 `score` 挑出需要人工复核的块。

## 7. 只看引擎状态

```bash
python scripts/bootstrap.py check
python scripts/actions.py engines --json
```

## 边界

- 有文字层的 PDF 不要跑 OCR：`pdf-workshop` 的 `pdf-extract`（`-f md-plain`）更快更准。
- 需要 Word/Excel/PPT：识别完用 `office-all-done` 或 `pdf-workshop` 的转换动作接手。
- 需要「带隐形文字层的可搜索 PDF」：本技能不生成，用 `ocrmypdf`（依赖 Tesseract + Ghostscript）。
