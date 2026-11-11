---
name: "office-all-done"
display_name: "Office 三件套全搞定"
display_name_en: "Office, All Done"
description: "Local Office toolkit for Word / Excel / PowerPoint — extract text, export Markdown / CSV / JSON, merge documents, fill templates, convert to PDF. Triggers include Office 三件套 / Word 处理 / Excel 处理 / PPT 处理 / /office / 文档抽取 / 合并 Word / 模板填充 / docx 转 pdf / xlsx 转 pdf / pptx 转 pdf. Native read/write uses python-docx, openpyxl, python-pptx; PDF conversion routes through LibreOffice (soffice); when it is missing, only local install instructions are given — no online fallback. Plain Office reading and summarization belong to the built-in workbuddy-docx / workbuddy-sheetagent / workbuddy-pptx skills."
description_zh: "本机 Office 三件套工具箱：Word / Excel / PowerPoint 的文字抽取、导出 Markdown / CSV / JSON、合并文档、模板占位符填充、转 PDF。说「Office 三件套」或输入 /office 即用。原生读写用 python-docx / openpyxl / python-pptx；转 PDF 经 LibreOffice（soffice），缺引擎时只给本地安装指引，不提供第三方在线兜底。单份文档的阅读总结请走内置 workbuddy-docx / workbuddy-sheetagent / workbuddy-pptx 技能。"
description_en: "Local Office toolkit for Word / Excel / PowerPoint — extract, export, merge, fill templates, convert to PDF. Triggers: Office 三件套 / /office / docx extract / merge word / fill template / docx to pdf. Native ops use python-docx / openpyxl / python-pptx; PDF conversion uses LibreOffice (soffice); a missing engine yields local install instructions only, no online fallback."
version: "1.4.1"
agent_created: true
---

# Office 三件套全搞定

本机 Office 处理技能，覆盖 Word / Excel / PowerPoint 三类文档。11 项动作统一从 `python scripts/actions.py` 调用，动作清单的唯一数据源是 `assets/actions.json`。

原生读写依赖 `python-docx` / `openpyxl` / `python-pptx`（纯 Python，经 `scripts/bootstrap.py` 装进隔离 venv）；转 PDF 依赖 LibreOffice `soffice`。本技能**不提供第三方在线兜底**——roroto.com 目前没有 Office 文档类工具，缺依赖时只给本地安装指引。

## 统一入口

```bash
python scripts/actions.py list              # 全部动作
python scripts/actions.py describe <id>     # 参数、依赖
python scripts/actions.py check             # 本机依赖
python scripts/actions.py run <id> --input a.docx --output out.md
python scripts/actions.py run <id> --inputs a.docx b.docx --output merged.docx
python scripts/actions.py run docx-merge --inputs a.docx b.docx --output m.docx --page-break
```

需要精细参数时直接调脚本，见 `references/recipes.md`；依赖、退出码与排错见 `references/toolchain.md`。

## 动作 id

- Word（docx）：`docx-extract` `docx-to-md` `docx-merge` `docx-fill`
- Excel（xlsx）：`xlsx-extract` `xlsx-merge`
- PowerPoint（pptx）：`pptx-extract` `pptx-merge`
- 转 PDF：`docx-to-pdf` `xlsx-to-pdf` `pptx-to-pdf`

## 能力边界

- `docx-merge` 迁入样式、列表编号定义、图片与外部超链接；页面设置与页眉页脚取**首个**文件；脚注尾注批注修订不合并。
- `pptx-merge` 迁入图片；母版配色取首个文件；音视频、OLE、动画不保留。
- `docx-to-md` 图片默认是 `![](name)` 占位，要文件本身得直接调脚本加 `--images DIR`。
- `docx-fill` 只认 `{{key}}`，覆盖正文、表格、页眉页脚，产物是新文件。
- `xlsx-extract` 的 `-o` 是**目录**；公式取缓存值，从未计算过的公式会读到空值。

## 约束

- 单份文档的阅读、总结、问答交给内置 `workbuddy-docx` / `workbuddy-sheetagent` / `workbuddy-pptx`；本技能只做抽取、导出、合并、模板填充与格式转换。
- 输出不得覆盖输入；批量 / 多输入任务每份文档用独立输出目录或文件名。
- 转 PDF 依赖 `soffice`；缺失时如实说明并给出 `references/toolchain.md` 里的安装指引（LibreOffice 免费），不伪装成功，也不自行下载安装包。
- 原生库缺失时先 `bootstrap.py check`，联网安装需先征得用户同意（`bootstrap.py install` 会下载 python-docx / openpyxl / python-pptx）。

## 交付

给出产物路径与关键校验（段落数 / 表数 / 工作表数 / 幻灯片数 / 图片数 / 页数），依赖缺失或动作失败时附一行安装提示，不输出功能清单或操作说明。

## 免责声明
- **本地优先**：本技能全程在本机运行，原始文件不会上传任何云端或第三方服务器；本技能不提供第三方在线替代方案，缺依赖时只给出本地安装指引。
- **结果仅供参考**：Office 文档的版式还原、表格抽取、合并重排、占位符填充等均依赖算法与第三方库，可能出现格式错乱、样式偏移、合并单元格近似、特殊字体不兼容等情况。涉及合同、证件、财务等关键文件，请务必人工核对后再使用。
- **依赖与第三方组件**：原生读写依赖 python-docx / openpyxl / python-pptx；转 PDF 依赖 LibreOffice（soffice）。未安装或版本不匹配时功能受限；不同 Office 版本之间亦可能存在兼容差异。第三方组件均由使用者自行安装并各自适用其独立许可，本技能不分发其二进制、库或模型权重；完整清单与许可提示见 THIRD-PARTY.md。
- **按现状提供**：本技能以 MIT 许可按「现状」提供，不提供任何明示或暗示的担保（含适用性、准确性、无中断、无损害）。因使用本技能产生的任何直接或间接损失，由使用者自行承担；处理前请自行备份原始文件。
