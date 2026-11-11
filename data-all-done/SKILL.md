---
name: "data-all-done"
display_name: "数据全搞定"
display_name_en: "Structured Data, All Done"
description: "Local structured-data toolkit - convert between CSV/TSV/JSON/NDJSON/XML/YAML/TOML/Markdown tables, validate syntax and field consistency, merge, filter, select and rename fields, sort, deduplicate, profile fields, diff two tables, infer JSON Schema, split and flatten nested records. Triggers include 数据全搞定 / 数据工具箱 / /data / CSV 转 JSON / JSON 转 CSV / 表格转 Markdown / 合并表格 / 筛选数据 / 字段映射 / 数据校验 / 数据去重 / 字段统计 / 推断 schema / 嵌套 JSON 扁平化. Pure stdlib, fully local, nothing uploaded, no per-step confirmation by default."
description_zh: "本机结构化数据工具箱：CSV/TSV/JSON/NDJSON/XML/YAML/TOML/Markdown 表格互转 · 语法与字段一致性校验 · 多表合并 · 条件筛选 · 字段选择与重命名 · 排序去重 · 字段画像 · 两表比对 · 推断 JSON Schema · 拆表 · 嵌套 JSON 扁平化。说「数据全搞定」或输入 /data 即用，纯标准库零依赖，全程本地不上传，默认无需逐项确认（输出不覆盖输入、重名自动避让）。"
description_en: "Local structured-data toolkit - convert CSV/TSV/JSON/NDJSON/XML/YAML/TOML/Markdown tables, validate, merge, filter, select/rename fields, sort, dedupe, profile, diff, infer JSON Schema, split and flatten nested JSON. Triggers: 数据全搞定 / /data / csv to json / merge tables / filter rows / schema. Pure stdlib, fully local, no per-step confirmation by default."
version: "1.4.1"
agent_created: true
---

# 数据全搞定

本机结构化数据处理技能。12 项动作统一从 `python scripts/actions.py` 调用，动作清单的唯一数据源是 `assets/actions.json`。**全部动作只用 Python 标准库**：内部统一为「记录列表（list[dict]）」模型，各格式只负责读写适配。装了 `PyYAML` 时 YAML 读写自动增强，没有也能跑（内置极简 YAML 子集）。

## 统一入口

```bash
python scripts/actions.py list                  # 全部动作
python scripts/actions.py list --json           # 机器可读清单
python scripts/actions.py describe <id>         # 参数、依赖、备注
python scripts/actions.py check                 # 解释器 + 依赖状态
python scripts/actions.py run <id> --input <in> --output <out>
python scripts/actions.py online <id>           # 在线替代（本技能一律返回「无」）
```

`run` 把其余参数原样透传给 `scripts/<id 下划线>.py`；也可直接调用单个脚本。
精细参数见 `references/recipes.md`；格式矩阵、退出码、依赖与排错见
`references/toolchain.md`。动作清单的唯一数据源是 `assets/actions.json`。

## 动作 id

- 读写与校验：`data-convert` `data-validate` `data-schema`
- 变换：`data-merge` `data-filter` `data-select` `data-sort` `data-dedupe` `data-flatten`
- 分析与输出：`data-stats` `data-diff` `data-split`

## 默认无需逐项确认

本技能**默认无需逐项确认**：不对每个文件、每一步操作弹确认，直接执行到出结果。

- 输出命名、重名避让（` (2)` / `-2`）、可选依赖降级、批量单份失败不中断，全部自动决策。
- 依赖缺失不询问、不联网：只给一条本地安装指引，不伪装成功。
- **唯一不放行的是安全底线**：输出不得覆盖输入、不删除或移动用户原文件、不执行任意命令、不上传任何云端或第三方服务器。
- 预览类动作（`--dry-run` / 默认预览）在不落盘的前提下给出完整计划，落盘需显式 `--apply` 或 `-o`。

## 约束

- 全程本地处理，数据文件不上传任何云端或第三方服务，**不提供在线兜底**（`online` 全为 null）。
- 输出不得覆盖输入（退出码 3）；所有动作默认另存新文件，产物重名自动加 `-2`/`-3`。
- 内部模型是**记录列表**：`data-convert` 对深层嵌套的任意 JSON 只能保真转 JSON/NDJSON，转 CSV/Markdown 前请先用 `data-flatten`。
- 内置 YAML/TOML 只支持记录列表与扁平标量；`--from` / `--to` 可显式指定格式，不给时按扩展名推断。
- `--where` 的表达式只解析 `字段 运算符 值` 这一种受限语法，**不使用 eval**、不执行任意代码；字符串比较默认区分大小写。
- 批量与拆分动作单份失败不中断，末尾汇总 `failed`；超大文件不做流式处理，读入内存后一次性输出。

## 路由边界

- 本技能只处理**结构化记录表**：格式互转、行列筛选、字段变换、画像与比对。
- **从 PDF / Office / 网页里抽取表格**走 `doc-data-extract` / `ocr-workshop`；**纯文本编码、去重、替换、diff** 走 `text-all-done`；**Excel 工作簿的编辑与另存**走 `office-all-done`。
- 数据库查询、SQL 执行、爬虫与可视化图表不在范围内；需要跨技能串流程用 `pipeline-all-done`。

## 交付

给出产物路径与关键数字（记录数、字段数、命中/过滤条数、空值率、差异条数），失败时给出退出码含义与一条具体修复建议，不罗列功能清单。

## 免责声明
- **本地优先**：本技能全程在本机运行，原始文件不会上传任何云端或第三方服务器；本技能不提供第三方在线替代方案，缺依赖时只给出本地安装指引。
- **结果仅供参考**：跨格式转换会丢失类型与顺序信息（例如 CSV 全是字符串、XML 属性与文本节点可能合并、TOML 不支持 null）；内置 YAML 子集只覆盖「标量 + 扁平映射/列表」，复杂锚点、多行块与嵌套结构建议安装 PyYAML；编码与分隔符靠启发式嗅探，重要数据请先备份并人工抽查产物。
- **依赖与第三方组件**：核心功能只用 Python 标准库；可选增强依赖 PyYAML（YAML 完整解析）。相关组件的下载、许可与版权归各自作者所有，由使用者自行获取并合规使用。第三方组件均由使用者自行安装并各自适用其独立许可，本技能不分发其二进制、库或模型权重；完整清单与许可提示见 THIRD-PARTY.md。
- **按现状提供**：本技能以 MIT 许可按「现状」提供，不提供任何明示或暗示的担保（含适用性、准确性、无中断、无损害）。因使用本技能产生的任何直接或间接损失，由使用者自行承担；处理前请自行备份原始文件。
