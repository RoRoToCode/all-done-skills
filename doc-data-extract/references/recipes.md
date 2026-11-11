# 任务配方与排错

## 1. 文档转文本 / 格式转换

```bash
python scripts/doc_to_text.py report.pdf -o report.md
python scripts/doc_to_text.py 合同.docx -o 合同.md
python scripts/doc_convert.py data.xlsx -o data.csv --to csv
python scripts/doc_convert.py page.html -o page.txt --to txt
```

- 多格式统一入口在 `scripts/ingest.py`：`extract(path)` 返回 `{text, pages, warnings, format}`。
- PDF 优先用宿主 `workbuddy-pdf` CLI，缺失时退化为 `pypdf`（版式较弱）。
- Office / HTML 走对应库（python-docx / openpyxl / python-pptx / bs4），缺库时如实说明。
- `doc-convert --to pdf` 需要本机浏览器或 Office，未实现，改用 pdf-workshop 或在线替代。

## 2. 内容抽取

```bash
python scripts/extract_tables.py budget.xlsx -o budget-tables
python scripts/extract_tables.py scan.pdf -o scan-tables
python scripts/extract_fields.py 合同.pdf -o 合同-fields.json --preset contract
python scripts/extract_fields.py 发票.jpg.pdf -o 发票.json --preset invoice
python scripts/extract_kv.py 表单.docx -o 表单-kv.json
```

- `extract-fields` 预设：`general`（日期/金额/百分比/邮箱/URL/手机号）、`contract`（甲方乙方/金额/签署日期/违约金）、`finance`（营收/净利/总资产/同比）、`invoice`（发票号/金额/购销方/税号）。
- `extract-kv` 识别「键：值」「键=值」「Key: Value」同行结构；表单、配置、票据类优先。
- 正则命中只是候选，必须回看原文档确认单位、表头与上下文。

## 3. 版面结构、实体与模板抽取

```bash
python scripts/doc_structure.py 合同.pdf -o 合同-structure.json
python scripts/extract_entities.py 合同.docx -o 合同-entities.json
python scripts/extract_entities.py 合同.docx -o 合同-entities.json --csv 合同-entities.csv --types org,person
python scripts/template_extract.py 发票.pdf -o 发票.json --template tpl.json --strict
```

- `doc-structure` 按页输出 block（heading / paragraph / list / table / quote）+ `outline`，每块带 `page` 与 `index` 可回溯。标题识别为启发式：Markdown `#`、`第X章/节`、`一、`、`（一）`、`1.2.3`。
- **PDF 的结构化看不到表格**：宿主 CLI 转 Markdown 会丢掉表格竖线，表格请用 `extract-tables`（走 `-f table`）单独抽取；脚本检测到该情况会在 `warnings` 里提示。
- `extract-entities` 类型：`date money percent email phone id_card uscc bank_account url org person address`，另可用 `--dict` 加自定义词典（每行 `词` 或 `词,类型`）。重叠冲突按 `id_card > uscc > email > url > phone > bank_account > date > percent > money > address > person > org` 保留，结果含页码、计数与上下文。
- 人名与机构是**规则候选**：机构靠后缀（公司/银行/医院/大学…），人名靠「联系人/法定代表人」等线索与「先生/女士」称谓，可能漏抽或误抽，务必回看原文。

模板 JSON 三种写法都接受：

```json
{"id": "purchase-contract-v1",
 "fields": [
   {"name": "party_a", "label": "甲方", "required": true},
   {"name": "sign_date", "patterns": ["(20\\d{2}年\\d{1,2}月\\d{1,2}日)"]},
   {"name": "amount", "between": ["合同总金额：", "，"]},
   {"name": "penalty", "patterns": ["违约金[^。]{0,20}"], "multiple": true}
 ]}
```

- `label`：取「标签：值」，遇到连续空格或「电话/邮箱/地址」等下一字段线索自动截断。
- `patterns`：正则列表，有捕获组取第 1 组，否则取整段。
- `between`：`[起始串, 结束串]` 之间的内容。
- `required: true` 的字段缺失会列入 `missing_required`；`--strict` 时以退出码 2 结束，可直接用于校验。
- 输出含 `coverage`（找到字段占比）与 `required_coverage`，批量票据可先跑 `--strict` 做准入检查。

## 4. 批量与检索分析

```bash
python scripts/batch_extract.py ./invoices/ -o result --preset invoice
python scripts/doc_search.py "违约金" a.pdf b.pdf -o search.json
python scripts/doc_search.py "第[一二三]条" ./docs/ -o search.json --regex
python scripts/doc_compare.py v1.docx v2.docx -o compare.json
```

- `batch-extract` 输出 `fields.csv`（每行为一条字段）与 `fields.json`（含每文件汇总与警告）；失败文件单独记录，不计入汇总。
- `doc-search` 建立轻量内存索引后检索，保留来源文件名与位置（页码或工作表名）；`--regex` 打开正则。
- `doc-compare` 做行级 `SequenceMatcher` 相似度 + 内容集合 Jaccard，列出仅出现在某一方的行；适合版本差异，不适合语义等价判断。

## 常见故障

| 现象 | 原因 | 处理 |
|---|---|---|
| `cli_not_found` | 宿主 PDF 组件未就绪 | 等待或设置 `WORKBUDDY_PDF` / `WORKBUDDY_PDF_CLI_DIR` |
| 退出码 69 | 后台下载未完成 | 已自动重试 3 次，仍失败说明组件未就绪 |
| `ModuleNotFoundError` | 缺可选依赖 | `pip install python-docx openpyxl python-pptx beautifulsoup4 pypdf` |
| PDF 表格为空 | 宿主 CLI 不可用 | 改用 `extract-tables` 在线替代或先装 pypdf |
| 结构里没有表格 | PDF 转 Markdown 丢竖线 | 用 `extract-tables` 单独抽，勿据此判断文档无表 |
| 模板字段抓太多 | label 后无分隔 | 加 `patterns` 精确限定，或调整 `between` 的结束串 |
| 抽取漏字 / 顺序乱 | 版面识别局限 | 回看原文档核对，必要时用 PDF 渲染图 |
| 批量混入旧文件 | 复用输出目录 | 每批用新目录，检查 `fields.json` 的 warnings |
