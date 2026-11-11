命令都在技能根目录执行；`<in>` / `<out>` 换成实际路径，路径含空格要加引号。

## 1. 先扫一遍，看命中了什么

```bash
python scripts/pv_scan.py <in>.txt -o findings.json
python scripts/pv_rules.py -o rules.json
python scripts/pv_report.py findings.json -o privacy-report.html --format html
```

默认按类型汇总，结果里命中值已做掩码；`--context 20` 才附带少量上下文，便于人工定位。
`--rules myrules.json` 可加载自定义规则。

## 2. 脱敏另存

```bash
python scripts/pv_redact.py <in>.txt -o <out>.txt --mode mask
python scripts/pv_redact.py <in>.txt -o <out>.txt --mode placeholder --types phone_cn,email
python scripts/pv_redact.py <in>.txt --mode mask --dry-run
```

`mask` 保留首尾若干字符（如 `138****8000`），`placeholder` 换成 `<手机号>`，
`remove` 直接删除命中串。不带 `-o` 只打印计划，不落盘。

## 3. 目录批量

```bash
python scripts/pv_batch.py docs/ -o scan-out/ --mode scan --pattern "*.txt" --recursive
python scripts/pv_batch.py docs/ -o clean-out/ --mode redact --apply
```

批量扫描产物是 `report.json` + 每份文件的独立结果；批量脱敏默认预览，`--apply` 才写文件。

## 4. 元数据读取与清理

```bash
python scripts/pv_metadata.py photo.jpg contract.docx -o meta.json
python scripts/pv_clean.py photo.jpg -o photo-clean.jpg
python scripts/pv_clean.py report.pdf -o report-clean.pdf --dry-run
```

支持 JPEG（EXIF/APP 段）、PNG（文本块）、OOXML（core.xml/app.xml）、PDF（常见 /Info 键）。
PDF 是保守清理，报告里的 `skipped` 要看一眼；重要文件请保留原件并人工复核。

## 5. 二维码与条形码

```bash
python scripts/pv_barcode.py "ABC-123456" -o code.svg --height 60
python scripts/pv_qr_make.py "https://example.com" -o qr.png
python scripts/pv_qr_read.py qr.png -o decoded.json
```

Code128-B 条形码是纯标准库生成 SVG，开箱即用；二维码需要先装
`qrcode`（生成）与 `pyzbar`/`opencv-python`（识别），缺了会明确提示安装命令。

## 组合流水线

```bash
python scripts/pv_scan.py raw.txt -o found.json && \
python scripts/pv_redact.py raw.txt -o safe.txt --mode mask && \
python scripts/pv_report.py found.json -o report.md
```
