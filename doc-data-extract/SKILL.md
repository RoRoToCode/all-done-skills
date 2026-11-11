---
name: "doc-data-extract"
display_name: "文档数据抽取"
display_name_en: "Document Data Extract"
description: "Local multi-format document processing and structured data extraction. Ingest PDF / Word / Excel / PPT / HTML / Markdown / CSV / TXT, then extract text, tables, fields, key-value pairs, layout structure, named entities and template-defined values, run cross-document search and comparison, and export to Markdown / CSV / XLSX / JSON. Triggers include 文档数据抽取 / 文档处理 / 数据抽取 / 字段抽取 / 表格抽取 / 实体抽取 / 模板抽取 / 版面结构化 / 跨文档检索 / 文档对比 / doc extract / extract fields."
description_zh: "本机多格式文档处理与结构化数据抽取：读取 PDF / Word / Excel / PPT / HTML / Markdown / CSV / TXT，抽取正文、表格、字段、键值对、版面结构与命名实体，支持模板化抽取、跨文档检索与对比，导出 Markdown / CSV / XLSX / JSON。说「文档数据抽取」或输入 /doc 即用，全程本地处理不上传。"
description_en: "Local multi-format document processing and structured data extraction — text, tables, fields, key-value, layout structure, entities, template extraction, cross-document search/compare, export to MD/CSV/XLSX/JSON."
version: "1.4.1"
agent_created: true
---

# 文档数据抽取

本机多格式文档处理与数据抽取技能。11 项动作统一从 `python scripts/actions.py` 调用，动作清单的唯一数据源是 `assets/actions.json`。

与同目录姊妹技能的关系：

- `pdf-workshop`（PDF 全搞定）：只做 **单格式 PDF** 的生成、编辑、转换与批量处理。
- `image-all-done`（图片全搞定）：只做 **图片** 处理。
- 本技能：面向 **多种文档格式** 的 **结构化数据抽取**（字段、表格、键值对、实体）与跨文档检索/对比，是「数据抽取」专项。

单份 PDF 的纯阅读、总结、问答仍交给内置 `workbuddy-pdf`；本技能只做抽取、转换、检索、对比与导出。

## 统一入口

```bash
python scripts/actions.py list              # 全部动作
python scripts/actions.py describe <id>     # 参数、依赖、在线链接
python scripts/actions.py check             # 本机依赖
python scripts/actions.py run <id> --input a.pdf --output out.md
python scripts/actions.py online <id>       # 对应的在线工具
```

需要精细参数时直接调脚本，见 `references/recipes.md`；依赖、退出码与排错见 `references/toolchain.md`。

## 动作 id

- 基础转换：`doc-to-text` `doc-convert`
- 内容抽取：`extract-tables` `extract-fields` `extract-kv` `doc-structure` `extract-entities` `template-extract`
- 批量处理：`batch-extract`
- 检索分析：`doc-search` `doc-compare`

四种抽取的取舍：字段固定且能用正则描述 → `extract-fields`；版式固定、字段由业务方定义 → `template-extract`；只知道要找什么类型（人名、金额、证件号）→ `extract-entities`；需要章节层级与页码定位 → `doc-structure`。

```bash
# 模板抽取：模板是 JSON，字段支持 patterns / label / between
python scripts/actions.py run template-extract \
  --input 发票.pdf --template tpl.json --output 发票-tpl.json

# 版面结构化：按页输出 block + 大纲
python scripts/actions.py run doc-structure --input 合同.pdf --output 合同-structure.json

# 实体抽取：可按类型过滤
python scripts/actions.py run extract-entities --input 合同.docx --output 合同-entities.json
```

## 约束

- 全程本地处理，原始文档不上传云端。
- 输出不得覆盖输入；批量任务每份文档用独立输出目录。
- 依赖缺失时如实说明并给出安装建议或在线替代，不做长篇解释。
- 在线替代只在 roroto.com 确有对应工具时给出（PDF 类动作有，字段 / 键值 / 实体 / 模板 / 批量抽取没有）；`actions.py online <id>` 返回「无」就表示该站没有替代。
- 正则 / 模板命中的字段只是候选，单位、表头与上下文必须回看原文档核对；涉及合同、证件、财务等关键文件请人工复核后再使用。
- 不同生成器导出的文档版式差异较大，表格与版面为近似还原。

## 交付

给出产物路径与关键校验（条数、字段、文件数），依赖缺失或动作失败时附一行对应在线工具链接。不输出功能清单或操作说明。

## 免责声明
- **本地优先**：本技能默认在本机运行，原始文件不会主动上传任何第三方服务器。仅当你主动打开文档中列出的第三方在线工具（如 roroto.com）时，相关文件的上传、处理、存储与隐私均以该站点自身声明与条款为准，本技能不对其可用性、安全性或结果作任何担保。
- **结果仅供参考**：文字识别、表格抽取、版面还原、字段匹配均依赖算法与第三方库，可能出现错漏、格式错乱或版式偏移。关键文件务必人工核对。
- **依赖与第三方组件**：部分动作依赖第三方库（pypdf / python-docx / openpyxl / python-pptx / bs4），未安装时功能受限；不同文档生成器与阅读器之间可能存在兼容差异。第三方组件均由使用者自行安装并各自适用其独立许可，本技能不分发其二进制、库或模型权重；完整清单与许可提示见 THIRD-PARTY.md。
- **按现状提供**：本技能以 MIT 许可按「现状」提供，不提供任何明示或暗示的担保（含适用性、准确性、无中断、无损害）。因使用本技能产生的任何直接或间接损失，由使用者自行承担；处理前请自行备份原始文件。
