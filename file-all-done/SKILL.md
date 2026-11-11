---
name: "file-all-done"
display_name: "文件全搞定"
display_name_en: "Files, All Done"
description: "Local file management toolkit - directory inventory and tree, name/size/date search, batch rename with dry-run, content-hash duplicate detection, sha256 checksums and verification, safe copy and classification by type or date, large/empty file reports, file metadata and two-directory comparison. Triggers include 文件全搞定 / 文件工具箱 / /file / 批量重命名 / 文件去重 / 查重复文件 / 目录清单 / 文件树 / 计算 sha256 / 校验文件 / 按类型整理 / 大文件 / 文件比对 / 安全复制. Pure stdlib, fully local, nothing uploaded, no per-step confirmation by default."
description_zh: "本机文件管理工具箱：目录清单与文件树 · 按名称/大小/时间查找 · 批量重命名（默认预览）· 内容哈希查重 · sha256/md5 校验与复核 · 按类型/日期归类 · 大文件与空文件报告 · 文件元数据 · 两目录比对 · 安全批量复制。说「文件全搞定」或输入 /file 即用，纯标准库零依赖，全程本地不上传，默认无需逐项确认（重名自动避让、绝不删除或移动原文件）。"
description_en: "Local file management toolkit - inventory, tree, search, batch rename (dry-run by default), content-hash dedupe, sha256 checksums and verification, safe copy, classification by type/date, large/empty file reports, metadata and directory diff. Triggers: 文件全搞定 / /file / batch rename / duplicate files / checksum / organize by type. Pure stdlib, fully local, no per-step confirmation by default."
version: "1.4.1"
agent_created: true
---

# 文件全搞定

本机文件管理层技能。12 项动作统一从 `python scripts/actions.py` 调用，动作清单的唯一数据源是 `assets/actions.json`。**全部动作只用 Python 标准库**，不需要安装任何第三方包，也不需要联网。家族里其它技能处理文件内容，本技能处理**文件本身**：命名、清单、查重、校验、归类与复制。

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

- 清单与查找：`file-list` `file-tree` `file-find`
- 命名与归类：`file-rename` `file-organize`
- 查重与校验：`file-dedupe` `file-hash` `file-verify`
- 度量与比对：`file-size` `file-compare` `file-metadata` `file-copy`

## 默认无需逐项确认

本技能**默认无需逐项确认**：不对每个文件、每一步操作弹确认，直接执行到出结果。

- 输出命名、重名避让（` (2)` / `-2`）、可选依赖降级、批量单份失败不中断，全部自动决策。
- 依赖缺失不询问、不联网：只给一条本地安装指引，不伪装成功。
- **唯一不放行的是安全底线**：输出不得覆盖输入、不删除或移动用户原文件、不执行任意命令、不上传任何云端或第三方服务器。
- 预览类动作（`--dry-run` / 默认预览）在不落盘的前提下给出完整计划，落盘需显式 `--apply` 或 `-o`。

## 约束

- 全程本地处理，文件路径与内容不上传任何云端或第三方服务，**不提供在线兜底**（`online` 全为 null）。
- **绝不删除、绝不移动用户原文件**：`file-rename` 与 `file-organize` 默认只输出预览计划，必须显式 `--apply` 才落盘；`file-organize` 与 `file-copy` 只复制不移动；`file-dedupe` 只报告重复组，不做任何清理。
- 所有写操作产出新文件或新目录，输出重名自动加 `-2`/`-3`；输出等于输入、输出落在输入目录内部且会造成递归自包含的场景一律拒绝（退出码 3）。
- 符号链接默认不跟随；`file-list` / `file-find` 的扫描深度与条目数有上限，超大目录会截断并在报告里标记 `truncated`。
- `file-rename --apply` 会写一份 `rename-map.json`，记录原名→新名映射，便于人工回退；本技能不提供自动撤销命令。

## 路由边界

- 本技能只处理**文件与目录层面**的清点与组织，不解析文件内容的语义。
- **压缩包内部条目**走 `archive-all-done`；**PDF / 图片 / 音视频 / Office 文档**的转换与编辑走各自技能；**纯文本内容的清洗与比较**走 `text-all-done`；**CSV/JSON 等结构化数据的内容处理**走 `data-all-done`。
- 需要跨多个技能串成流程（如「整理目录 → 批量转 PDF → 抽取」）用 `pipeline-all-done`；需要扫描文件内容里的敏感信息用 `privacy-all-done`。

## 交付

给出产物路径与关键数字（文件数、总体积、重复组数、校验通过/失败数、重命名条数），失败时给出退出码含义与一条具体修复建议，不罗列功能清单。

## 免责声明
- **本地优先**：本技能全程在本机运行，原始文件不会上传任何云端或第三方服务器；本技能不提供第三方在线替代方案，缺依赖时只给出本地安装指引。
- **结果仅供参考**：文件哈希用于判重与校验，不保证识别内容相同但字节不同的文件；按扩展名归类依据文件名而非内容嗅探；重命名与归类涉及路径变更，预览结果与正式执行可能因目录状态变化而有差异。重要目录请先备份并人工核对预览清单。
- **依赖与第三方组件**：本技能只使用 Python 标准库，不依赖第三方二进制或模型；若使用者在同一解释器中另装了其它包，相关组件的许可与版权归各自作者所有，由使用者自行合规使用。第三方组件均由使用者自行安装并各自适用其独立许可，本技能不分发其二进制、库或模型权重；完整清单与许可提示见 THIRD-PARTY.md。
- **按现状提供**：本技能以 MIT 许可按「现状」提供，不提供任何明示或暗示的担保（含适用性、准确性、无中断、无损害）。因使用本技能产生的任何直接或间接损失，由使用者自行承担；处理前请自行备份原始文件。
