---
name: "ebook-all-done"
display_name: "电子书全搞定"
display_name_en: "Ebooks, All Done"
description: "Local ebook toolkit — EPUB inspect, validate, metadata editing, table of contents export/rebuild, full-text extraction and search, cover and image assets, split/merge, build EPUB from Markdown/TXT/HTML, EPUB to PDF, Calibre format conversion, batch processing. Triggers include 电子书全搞定 / 电子书工具箱 / /ebook / EPUB 转 MOBI / EPUB 转 PDF / 改电子书作者 / 提取电子书目录 / 电子书拆章 / 合并电子书 / Markdown 转 EPUB / 电子书封面 / 校验 EPUB. All processing runs locally; nothing is uploaded. DRM removal is not supported. No per-step confirmation by default: no per-file prompts, non-destructive output naming."
description_zh: "本机电子书处理工具箱：EPUB 体检与规范校验 · 元数据/作者/书名修改 · 目录导出与重建 · 正文提取为 Markdown/TXT · 全文检索 · 封面与插图导出替换 · 按章拆分与合并 · Markdown/TXT 生成 EPUB · 转 PDF · Calibre 互转 MOBI/AZW3 · 批量处理。说「电子书全搞定」或输入 /ebook 即用，全程本地处理不上传；默认默认无需逐项确认（不逐项确认、产物重名自动改名、批量单份失败不中断）；不支持 DRM 去除。（共 16 项动作）"
description_en: "Local ebook toolkit — EPUB inspect/validate, metadata and TOC editing, text extraction, full-text search, cover and image assets, split/merge, generate EPUB from Markdown/TXT/HTML, EPUB to PDF, Calibre conversion (MOBI/AZW3), batch processing. Triggers: 电子书全搞定 / /ebook / epub to pdf / epub metadata / epub toc / split epub / merge epub / markdown to epub. No per-step confirmation by default (no per-file prompts, auto-rename on conflict)."
version: "1.4.1"
agent_created: true
---

# 电子书全搞定

本机电子书处理技能。16 项动作统一从 `python scripts/actions.py` 调用，脚本在 `scripts/`，动作清单的唯一数据源是 `assets/actions.json`。核心读写**只用 Python 标准库**（`zipfile` + `xml` + `html.parser`），EPUB2 / EPUB3 都能处理，装不装第三方库都能跑大部分动作。

## 统一入口

```bash
python scripts/actions.py list              # 全部动作
python scripts/actions.py describe <id>     # 参数、依赖
python scripts/actions.py check             # 本机依赖
python scripts/actions.py run <id> --input a.epub --output out.epub
python scripts/actions.py online <id>       # 在线替代（本技能一律返回「无」）
```

需要精细参数时直接调脚本，见 `references/recipes.md`；依赖、退出码与排错见 `references/toolchain.md`。

## 动作 id

- 检查与校验：`eb-inspect` `eb-validate` `eb-batch`
- 元数据与资源：`eb-meta` `eb-cover` `eb-images`
- 目录与正文：`eb-toc` `eb-retoc` `eb-extract` `eb-search`
- 结构编辑：`eb-split` `eb-merge`
- 生成与导出：`eb-from-md` `eb-from-text` `eb-to-pdf`
- 格式互转：`eb-convert`（需 Calibre `ebook-convert`）

## 默认无需逐项确认

本技能**默认无需逐项确认**：不对每本书、每一步操作弹确认，直接执行到出结果。

- 体检、批量、拆合、生成、格式转换全部自动决策；输出重名自动改名 ` (2)`（目录同理），单份失败不中断整批，末尾统一汇总。
- 冲突策略用 `python scripts/actions.py run <id> ... --on-conflict overwrite|skip` 修改（默认 `rename`）；也可设环境变量 `EBOOK_ON_CONFLICT`。无论哪种策略，**输出等于输入一律拒绝**。
- 依赖缺失不询问、不联网：核心 15 项零第三方依赖直接跑；确实做不了（Calibre / 浏览器 / Pillow）才给一条本地安装提示，不伪装成功。
- **唯一不放行的是安全底线**：含 DRM / 加密标记的书只报告、不改写；原始电子书始终只读，改写类动作一律另存新文件；不提供第三方在线兜底、不上传、不协助绕过版权保护。
- 处理前不要求逐个确认，但**不主动删除任何用户文件**；临时目录只清理本技能自己创建的。

## 约束

- 全程本地处理，原始电子书不上传云端；**不提供第三方在线兜底**（roroto.com 没有电子书类工具），缺依赖时只给本地安装指引。
- **不处理受 DRM / 加密保护的电子书，也不提供任何绕过版权保护的手段**；遇到 `META-INF/encryption.xml` 只如实报告并停止改写。
- 输出不得覆盖输入；拆分、批量任务每份产物用独立目录/文件名。
- 核心动作零第三方依赖；`eb-convert` 需要 Calibre 的 `ebook-convert`，`eb-to-pdf` 需要本机 Edge / Chrome，`eb-cover --generate` 需要 Pillow。缺失时优雅报错并给安装提示，不静默失败。
- 改写类动作（元数据、目录、封面、拆合）一律**另存新 EPUB**，不原地修改源文件。
- 重建式动作（拆分、合并、生成）会把章节转成规范 XHTML 并重建 OPF / NCX / nav；复杂脚本、SVG 交错、固定版式（fixed-layout）与 EPUB3 媒体叠加等高级特性可能不保真，重要成品请人工核对。

## 路由边界

- 本技能只在**电子书容器（EPUB / MOBI / AZW3 等）层面**工作：读结构、改元数据与目录、拆合与生成、导出正文。说「电子书全搞定 / 电子书工具箱 / /ebook」即用。
- **PDF 的阅读、总结、问答**走内置 `workbuddy-pdf`；PDF 的合并/拆分/加密/转 Office 走 `pdf-workshop`。本技能的 `eb-to-pdf` 只负责把 EPUB 正文排版成 PDF。
- **单个 DOCX / XLSX / PPTX 的处理**走 `office-all-done`；从文档里抽表格、字段、实体走 `doc-data-extract`；图片 OCR 走 `ocr-workshop`。
- 只要输入是 EPUB/电子书、或期望产出是 EPUB，就优先本技能；只是想「读」一本电子书时，用 `eb-extract` 抽正文再交给模型理解，不必先转格式。
- 本技能**不生成书籍内容**，只做把已有文字组装成电子书的确定性排版；写稿属于创作能力。

## 交付

给出产物路径与关键校验（章节数、字数、EPUB 版本、体积、校验错误数），依赖缺失或动作失败时附一行安装提示。不输出功能清单或操作说明。

## 免责声明
- **本地优先**：本技能全程在本机运行，原始文件不会上传任何云端或第三方服务器；本技能不提供第三方在线替代方案，缺依赖时只给出本地安装指引。
- **结果仅供参考**：电子书解析、正文抽取、目录重建、格式互转与重排版均依赖算法与阅读器实现，可能出现样式丢失、目录层级偏差、图片路径失效、特殊字符或固定版式不兼容等情况；重要成品请务必在目标阅读器中人工核对后再分发。
- **依赖与第三方组件**：部分动作依赖第三方工具（Calibre `ebook-convert`、Edge / Chrome 浏览器内核、Pillow）与系统字体，未安装或版本不匹配时功能受限；相关工具的下载、许可与版权归各自作者所有，由使用者自行获取并合规使用。使用者应确认对电子书拥有合法处理与转换的权利，本技能不支持绕过 DRM 或版权保护。第三方组件均由使用者自行安装并各自适用其独立许可，本技能不分发其二进制、库或模型权重；完整清单与许可提示见 THIRD-PARTY.md。
- **按现状提供**：本技能以 MIT 许可按「现状」提供，不提供任何明示或暗示的担保（含适用性、准确性、无中断、无损害）。因使用本技能产生的任何直接或间接损失，由使用者自行承担；处理前请自行备份原始文件。
