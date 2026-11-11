---
name: "text-all-done"
display_name: "文本全搞定"
display_name_en: "Text, All Done"
description: "Local text toolkit — encoding detection and conversion, newline and whitespace normalisation, line de-duplication, regex find-and-replace, unified diff, statistics with word/character frequency, and splitting large files by lines, characters or bytes. Triggers include 文本全搞定 / 文本工具箱 / /text / 转编码 / GBK转UTF-8 / 乱码 / 文本去重 / 批量替换 / 文本比对 / diff / 文本切分 / 字数统计. Pure standard library, runs entirely locally, nothing is uploaded. No per-step confirmation by default: no prompts, non-destructive output naming."
description_zh: "本机文本工具箱：编码嗅探与互转（UTF-8/GBK/GB18030/BIG5/UTF-16）· 换行与空白规范化 · 按行去重 · 正则批量替换 · 两文件 diff · 字数与词频统计 · 按行/字符/字节切分大文件。说「文本全搞定」或输入 /text 即用，纯标准库零依赖，全程本地不上传；默认无需逐项确认（不逐项确认、产物重名自动避让、输出不覆盖输入）。（共 7 项动作）"
description_en: "Local text toolkit — encoding detection/conversion (UTF-8, GBK, GB18030, BIG5, UTF-16), newline and whitespace normalisation, line de-duplication, regex replace, unified diff, text statistics with word and character frequency, and splitting by lines/characters/bytes. Triggers: 文本全搞定 / /text / encoding convert / garbled text / dedupe lines / find and replace / diff / split text. Standard library only, no per-step confirmation."
version: "1.4.1"
agent_created: true
---

# 文本全搞定

本机文本处理技能。7 项动作统一从 `python scripts/actions.py` 调用，动作清单的唯一数据源是 `assets/actions.json`。**全部动作只用 Python 标准库**，不需要安装任何第三方包，也不需要联网。

## 统一入口

```bash
python scripts/actions.py list              # 全部动作
python scripts/actions.py describe <id>     # 说明与依赖
python scripts/actions.py check             # 解释器 + 依赖
python scripts/actions.py run <id> --input a.txt --output out.txt
python scripts/actions.py online <id>       # 在线替代（本技能一律返回「无」）
```

需要精细参数时直接调脚本，见 `references/recipes.md`；退出码与排错见 `references/toolchain.md`。

## 动作 id

- 编码与排版：`txt-convert` `txt-normalize`
- 清洗与修改：`txt-dedupe` `txt-replace`
- 比较与度量：`txt-diff` `txt-stats`
- 拆分：`txt-split`

## 默认无需逐项确认

本技能**默认无需逐项确认**：不逐步询问，直接执行到出结果。

- 编码嗅探、规范化、去重、替换、diff、统计、切分全部自动决策；输出重名自动加序号（`-2`/`-3`），不覆盖历史产物。
- **输出等于输入一律拒绝**（退出码 3）；所有动作默认另存新文件，原始文本只读。
- 依赖缺失不询问、不联网：本技能没有第三方依赖，不存在"装不上就跑不了"的情况。
- **唯一不放行的是安全底线**：不上传原始文本、不提供第三方在线兜底、不做不可逆的原地改写；`txt-replace` 默认必须给 `-o` 才落盘，否则按 `--dry-run` 处理。

## 约束

- 全程本地处理，原始文本不上传云端；**不提供第三方在线兜底**，也不推荐把整份文件粘到网页工具里。
- 编码探测顺序：BOM → 严格 UTF-8 → GB18030（GBK 超集）→ BIG5 → Latin-1 兜底。**Latin-1 兜底不会失败**，所以探测结果永远带有"可能是错的"风险：转换前建议先跑 `--check` 看探测结果，重要文件用 `--from` 显式指定源编码。
- 换行风格按 `--newline keep|lf|crlf|cr` 处理，`keep` 表示原样保留；写盘时不做平台二次转换。
- `txt-diff` 是行级 diff，不做字符级；重排段落会产生较大噪声，重要对比建议先 `txt-normalize`。
- `txt-split` 只在行边界切分，不会把一行劈开；单行超过阈值时独立成一份并在报告中标记 `oversized`。
- 词频统计只统计拉丁词与单个汉字，**不做中文分词**（无依赖、可复现），需要分词请交给其它工具。

## 路由边界

- 本技能只处理**纯文本层面的读写与比较**：编码、换行、去重、替换、diff、统计、切分。
- **PDF 的读取与转换**走 `pdf-workshop`；**扫描件与图片识别成文字**走 `ocr-workshop`；**从 DOCX/XLSX/PPTX 抽正文与表格**走 `doc-data-extract`；**Office 文件的编辑与另存**走 `office-all-done`。
- 已经拿到文本、只是要"整理成能用的文本"，才用本技能。涉及结构化抽取（表格、字段、实体）不属于这里。

## 交付

给出产物路径与关键数字（输入/输出行数、替换处数、差异行数、切分份数、编码）。失败时给出退出码含义与一条具体修复建议，不罗列功能清单。

## 免责声明
- **本地优先**：本技能全程在本机运行，原始文件不会上传任何云端或第三方服务器；本技能不提供第三方在线替代方案，缺依赖时只给出本地安装指引。
- **结果仅供参考**：编码探测、去重键归一化、正则替换、diff 与词频统计均依赖启发式规则，可能出现误判编码、误删重复行、替换范围超出预期等情况；重要文件请先备份并用 `--dry-run`/`--check` 确认，再对产物人工抽查。
- **依赖与第三方组件**：本技能只使用 Python 标准库，不依赖第三方二进制或模型；若使用者在同一解释器中另装了其它包，相关组件的许可与版权归各自作者所有，由使用者自行合规使用。第三方组件均由使用者自行安装并各自适用其独立许可，本技能不分发其二进制、库或模型权重；完整清单与许可提示见 THIRD-PARTY.md。
- **按现状提供**：本技能以 MIT 许可按「现状」提供，不提供任何明示或暗示的担保（含适用性、准确性、无中断、无损害）。因使用本技能产生的任何直接或间接损失，由使用者自行承担；处理前请自行备份原始文件。
