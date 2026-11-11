# 全搞定（All Done）本地技能包

**纯本地、零上传、诚实地失败。**

一组在本地运行的文档 / 媒体 / 图像 / 数据 / 压缩 / 隐私处理技能，共 **17 个技能、187 个动作**，当前版本 **1.4.1**。
所有处理默认在本机完成，不上传原始文件；缺依赖时给本地安装指引，不伪装成功。

可选在线工具链见 **https://roroto.com/**：仅在本地依赖缺失时作为备选参考列出，**不会自动调用**，不作担保、不从中获利。详见 [关于外部引用](#关于外部引用)。

> **快照声明**：本仓库是源码快照。主维护在 WorkBuddy 技能市场，这里提出的 Issue **不保证**会得到回复。

## 技能一览

| 技能 | 动作 | 做什么 | 额外依赖 |
| --- | --- | --- | --- |
| `pdf-workshop` | 23 | PDF 转 Office/图片、抽取、OCR、检索、合并拆分、压缩、旋转裁边、删页、页码、表单、脱敏、水印、加解密、MD→PDF | 官方 PDF CLI（宿主自带）、`pypdf`、`pymupdf`、OCR 引擎 |
| `ocr-workshop` | 5 | 图片/扫描 PDF 识别成 Markdown、JSON、表格 CSV，转可搜索 PDF | `rapidocr-onnxruntime`（或 Tesseract）、`pymupdf` |
| `image-all-done` | 12 | 格式转换、压缩、改尺寸、裁剪、水印、旋转、拼图、抠图、放大、OCR、批量、清 EXIF | `Pillow`；可选 `rembg`、`realesrgan` |
| `video-all-done` | 13 | 转码、压缩、剪辑、拼接、改尺寸、旋转、水印、抽音频/帧、GIF、字幕、幻灯片、文字卡 | `ffmpeg`、`Pillow` |
| `av-transcribe` | 5 | 本地 Whisper 转写、硬字幕、字幕互转、字幕翻译、抽音轨 | `ffmpeg`、`openai-whisper` |
| `office-all-done` | 11 | DOCX/XLSX/PPTX 抽取、转 MD、合并、填充、转 PDF | `python-docx`、`openpyxl`、`python-pptx`；转 PDF 需 LibreOffice |
| `doc-data-extract` | 11 | 文档转文本/CSV、抽表格、字段、KV、实体、模板抽取、结构、批量、检索、比对 | `python-docx`、`openpyxl`、`python-pptx`、`beautifulsoup4` |
| `archive-all-done` | 13 | 压缩包创建、解压、列表、测试、增删、格式互转、加解密、分卷、合并、批量 | 无（7z 需 `py7zr`，rar 只读需 `rarfile`） |
| `ebook-all-done` | 16 | EPUB 体检/校验、元数据、目录、正文、检索、拆合、生成、转 PDF、Calibre 互转 | 无（转 PDF 需 Edge/Chrome，互转需 Calibre） |
| `audio-all-done` | 15 | 转码、压缩、重采样、剪辑、拼接、切分、变速、音量、响度、降噪、淡入出、混音、信息、波形、抽音轨 | `ffmpeg` |
| `web-capture` | 9 | 抓网页、整页截图、转 PDF/Markdown、正文抽取、批量、爬取、差异比对 | 无（渲染需 Edge/Chrome） |
| `ai-prompt-reader` | 5 | 从 AI 生成的图片里反读提示词、种子、采样器、模型 | 无（纯标准库） |
| `text-all-done` | 7 | 编码互转、规范化、按行去重、正则替换、diff、统计、切分 | 无（纯标准库） |
| `file-all-done` | 12 | 目录清单/树、条件查找、批量重命名（默认预览）、内容哈希查重、校验和复核、归类、体积报告、目录比对、元数据、安全复制 | 无（纯标准库） |
| `data-all-done` | 12 | CSV/TSV/JSON/NDJSON/XML/YAML/TOML/Markdown 互转、校验、合并、筛选、字段映射、排序去重、画像、比对、Schema、拆表、嵌套扁平化 | 无（YAML 可选 `PyYAML`） |
| `pipeline-all-done` | 8 | 技能与动作发现、请求路由、流水线模板、定义校验、执行、断点续跑、状态、报告 | 无（纯标准库） |
| `privacy-all-done` | 10 | 敏感信息扫描/脱敏/批量/报告/规则集、JPEG/PNG/OOXML/PDF 元数据读取与清理、二维码、Code128 条形码 | 无（二维码需可选 `qrcode` / `opencv-python`） |

## 安装

把技能目录拷进 agent 的技能目录，重启会话即可：

```bash
# WorkBuddy（默认）
cp -r <技能名>/ ~/.workbuddy/skills/<技能名>/

# 其它读取 SKILL.md 的 agent（Claude Code、Codex CLI、Cursor、Gemini CLI、Cline 等）
cp -r <技能名>/ <agent-skills-dir>/<技能名>/
```

或从 **Releases** 页面下载某个技能的 `.zip`，解压到技能目录。见 `RELEASE_NOTES.md`。

## 兼容性

`SKILL.md` 遵循开放的 Agent Skills 规范，任何按 `SKILL.md` 加载技能的 agent 都能用。
在 WorkBuddy 上设计验证；其它 agent 触发词同样能加载，但可能需要显式调用。

`pdf-workshop` 与 `doc-data-extract` 的部分 PDF 动作会调用宿主自带的 `workbuddy-pdf` CLI。
非 WorkBuddy 环境设 `WORKBUDDY_PDF` 环境变量指向任意兼容 PDF CLI，或直接跳过那些动作即可。
其余技能纯标准库 / pip，Python 3.10+ 即可运行。

## 关于外部引用

本快照为 WorkBuddy 设计，因此有少量引用指向仓库之外：

- **`roroto.com`**：部分技能在 `actions.json`（`online` 字段）与 `SKILL.md` 中把
  roroto.com 列为*可选*的第三方在线替代。这些链接只在本地依赖缺失时由
  `python scripts/actions.py online <id>` 给出，且仅对站点上确有对应工具的动作
  才非空（其余为 `null`）。技能默认绝不自动调用它。这仅供信息参考，本仓库不作
  担保、也不从中获利。所有处理默认本地完成——只有*你*主动打开该链接时，相关文件
  才会上传到第三方，并以该站点自身条款为准。
- **`workbuddy-*` 内置技能**：`office-all-done` 把单份文档的阅读/总结路由到
  WorkBuddy 内置的 `workbuddy-docx` / `workbuddy-sheetagent` / `workbuddy-pptx`。
  它们不在本仓库内；非 WorkBuddy 环境的 agent 直接忽略该路由建议，使用本仓库提供的
  抽取/导出动作即可。

## 许可

MIT，版权 `Copyright (c) 2026 RoRoTo`。第三方组件各自适用其独立许可，本仓库不分发其二进制、
库或模型权重，详见各技能的 `THIRD-PARTY.md`。变更记录见 `CHANGELOG.md`。
