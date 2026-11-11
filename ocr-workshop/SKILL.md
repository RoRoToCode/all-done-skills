---
name: "ocr-workshop"
display_name: "OCR 全搞定"
display_name_en: "OCR, All Done"
description: "Turn images and scanned PDFs into searchable Markdown, plain text, structured JSON, table CSV, and searchable PDF with an invisible text layer. Five actions — image OCR, PDF OCR, batch OCR, table OCR, searchable PDF. Triggers include OCR / 文字识别 / 图片转文字 / 扫描件识别 / 截图识别 / 表格识别 / ocr-image / ocr-pdf. Local-first, no upload; document conversion and editing belong to pdf-workshop."
description_zh: "图片与扫描件文字识别，输出 Markdown 全文、纯文本、带坐标置信度的 JSON、表格 CSV，以及保留原版式的可搜索 PDF（不可见文字层）。五个动作：单图识别 / PDF 识别 / 批量识别 / 表格识别 / 扫描件转可搜索 PDF。说「OCR」「文字识别」「图片转文字」「扫描件识别」即用；PDF 转换、合并、加水印等请走 pdf-workshop。"
description_en: "OCR for images and scanned PDFs into Markdown, text, structured JSON and CSV tables. Five actions — image, PDF, batch, table and searchable PDF. Local-first; PDF conversion and editing live in pdf-workshop."
version: "1.4.1"
agent_created: true
---

# OCR 全搞定

本机 OCR 技能。5 项动作统一从 `python scripts/actions.py` 调用，动作清单的唯一数据源是 `assets/actions.json`。

## 统一入口

```bash
python scripts/actions.py list              # 全部动作
python scripts/actions.py describe <id>     # 参数、依赖、在线链接
python scripts/actions.py check             # 各动作依赖是否就绪
python scripts/actions.py engines           # 当前可用引擎与语言包
python scripts/actions.py run <id> --input a.png --output out/
python scripts/actions.py online <id>       # 对应的在线工具
```

精细参数（页范围、DPI、置信度阈值、强制指定引擎）直接调 `scripts/ocr_cli.py`，见 `references/recipes.md`；依赖与排错见 `references/toolchain.md`。

## 动作 id

- 识别：`ocr-image` `ocr-pdf` `ocr-batch`
- 结构化：`ocr-table`
- 回写 PDF：`ocr-searchable-pdf`（原图不动，只叠不可见文字层）

## 输出约定

每次运行在输出目录留下：

| 文件 | 内容 |
|---|---|
| `<stem>.md` | 全文；PDF 带 `<!-- page N -->` 页标记，连续多列自动还原成 Markdown 表格 |
| `<stem>.json` | 每页每块的文本、置信度、坐标框，供二次处理 |
| `pages/page-NNNN.txt` | PDF 逐页纯文本 |
| `tables/page-NNNN.csv` | 检测到表格时输出（UTF-8-BOM） |
| `manifest.json` | 输入、引擎、页数、平均置信度、告警 |

## 约束

- 只做识别，不做转换与编辑：PDF 转 Word / 合并 / 拆分 / 水印走 `pdf-workshop`；已有文字层的 PDF 直接抽文字也走 `pdf-workshop` 的 `pdf-extract`，不要白跑 OCR。
- 引擎优先级 RapidOCR > Tesseract；缺引擎先 `python scripts/bootstrap.py install --ocr`，不要直接 `pip install rapidocr-onnxruntime`（会去拉 44MB 的 opencv-python，慢网必卡）。
- 结果必须带证据：告警（缺语言包、渲染失败、低置信度）要写进结论，不要把识别失败说成「空白页」。
- 输出不得覆盖输入；批量任务每份文档一个子目录；PDF 密码只经参数传入，不写日志、manifest 或回答。
- 扫描件倾斜、噪点、印章遮挡会掉准确率；涉及合同、证件、财务数字，务必人工复核。

## 交付

给出产物路径、页数与平均置信度；低置信度（<0.9）或降级（引擎回退、缺语言包）必须点名说明。依赖缺失时附一行在线替代链接。

## 免责声明
- **本地优先**：本技能默认在本机运行，原始文件不会主动上传任何第三方服务器。仅当你主动打开文档中列出的第三方在线工具（如 roroto.com）时，相关文件的上传、处理、存储与隐私均以该站点自身声明与条款为准，本技能不对其可用性、安全性或结果作任何担保。
- **结果仅供参考**：文字识别依赖第三方引擎，倾斜、噪点、印章、艺术字、符号与数字易出现错漏；涉及合同、证件、财务等关键文件，请务必人工核对后再使用。
- **依赖与第三方组件**：需 `rapidocr_onnxruntime`（或 Tesseract + 语言包）；PDF 输入另需 `pymupdf`。未安装或版本不匹配时功能受限。第三方组件均由使用者自行安装并各自适用其独立许可，本技能不分发其二进制、库或模型权重；完整清单与许可提示见 THIRD-PARTY.md。
- **按现状提供**：本技能以 MIT 许可按「现状」提供，不提供任何明示或暗示的担保（含适用性、准确性、无中断、无损害）。因使用本技能产生的任何直接或间接损失，由使用者自行承担；处理前请自行备份原始文件。
