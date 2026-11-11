# 工具链与环境

## 三层依赖

| 能力 | 依赖 | 是否必需 |
|---|---|---|
| 文本/表格/结构提取、merge、split、docx/pptx/xlsx/dxf/png 转换 | 宿主的 `workbuddy-pdf` CLI | 必需，由 `wb_pdf.py` 定位 |
| encrypt / decrypt | `pypdf` | Windows 版官方 CLI 不能写加密文档（PDFium 限制），统一走 `pdf_ops.py` |
| Markdown / HTML → PDF | 本机 Edge 或 Chrome | 必需，零 Python 依赖 |
| rotate / delete / reorder / crop / 页码 / 水印 / 按页提取 | `pypdf` | 仅页面编辑需要；`extract_pages.py` 会校验产物，不一致返回 3 |
| 扫描件 OCR | Tesseract（含语言包）/ PaddleOCR；均缺失时回退 `rapidocr_onnxruntime` | 仅扫描件需要；RapidOCR 纯 Python，模型随包离线可用，用 `bootstrap.py install --ocr` 安装 |
| 压缩 / 脱敏 | `pymupdf`（PyMuPDF） | 仅这两项需要；`python -m pip install pymupdf`（或 `bootstrap.py install --pdf`） |
| 表单字段读写 | `pypdf` | 仅 `pdf-form-list` / `pdf-form-fill` 需要 |

依赖自检：`python scripts/actions.py check` 会先打印**当前解释器**，再逐个动作报依赖；`python scripts/bootstrap.py check` 输出 `pypdf` 与 `ocr` 两组状态，缺什么会给出对应安装命令。`pypdf` 默认装进隔离 venv（`~/.workbuddy/pdf-workshop-env`，可用 `PDF_WORKSHOP_VENV` 覆盖），`ocr` 装在当前解释器——因为 `ocr_pdf.py` 必须能 import 到它。

中文渲染走系统字体（Windows：微软雅黑 / 宋体；macOS：PingFang；Linux：Noto Sans CJK），无需自带字体文件。

## wb_pdf.py 的定位顺序

1. 环境变量 `WORKBUDDY_PDF`：直接指向 CLI 可执行文件。
2. `PATH` 上的 `workbuddy-pdf`。
3. 环境变量 `WORKBUDDY_PDF_SKILL_DIR` 指向的内置 skill 目录下的 `scripts/run.sh` 或 `run.ps1`。
4. 常见安装根目录下 glob 匹配 WorkBuddy 内置 `workbuddy-pdf/scripts/run.*`。

Windows 用 `powershell -NoProfile -ExecutionPolicy Bypass -File run.ps1` 转发，其他平台用 `sh run.sh`。

**不要**自行下载、搜索或拼接同名二进制替代。CLI 由宿主按需下载，来源不可控的替代物会破坏一致性。

## 退出码

| 码 | 含义 | 处理 |
|---|---|---|
| 0 | 成功 | 继续 |
| 2 | 用法错误 | 修参数 |
| 3 | 输入/输出错误 | 检查路径、目录、权限 |
| 4 | PDF 无法读取 | 检查加密与文件完整性 |
| 5 | 转换失败 | 换格式或换读取方式 |
| 6 | 其他异常 | 看 stderr |
| 69 | 组件尚未就绪（宿主占位程序） | 等几秒重试同一命令，`wb_pdf.py` 已自动重试 3 次；不要 pip install 替代 |
| 127 | 本机确实没有该 CLI | 说明限制，或设置 `WORKBUDDY_PDF` |

## 官方 CLI 速查（经 wb_pdf.py 转发）

```
read     <input> -o <out> -f md|md-plain|txt|structure|table [--image-dir D] [--table-format json|csv] [-p PWD]
merge    <a.pdf> <b.pdf> ... -o <out.pdf>
split    <input> -o <dir>
convert  <input> -o <out> -f docx|pptx|xlsx|dxf [--sheet-split continuous|page|auto]
render   <input> -o <dir> -f png|jpg [--dpi 144] [--jpeg-quality 85]
raw      <任意原始参数>
```

目录型输出：`table` / `png` / `jpg` / `split` 的 `-o` 必须是目录。每份文档用独立目录，避免旧产物混入。

`encrypt` / `decrypt` 虽然也在 CLI 帮助里，但 Windows 构建会返回退出码 5 并提示 PDFium 无法写加密文档，因此不要经 CLI 转发；改用 `pdf_ops.py encrypt|decrypt`（pypdf 实现）。AES-128 / AES-256 需要额外安装 `cryptography`，默认 RC4-128 无额外依赖。

## 浏览器定位

`md_to_pdf.py` 依次查 `PDF_BROWSER` 环境变量 → PATH 上的 msedge/chrome/chromium → 常见安装路径。生成命令使用 `--headless --no-pdf-header-footer --print-to-pdf`，临时 profile 与 HTML 放在临时目录，不污染用户配置。

## pypdf 安装

`bootstrap.py check` 返回 `missing` 时，先告知用户将联网安装一个纯 Python 包，再运行：

```bash
python scripts/bootstrap.py install          # 隔离 venv: ~/.workbuddy/pdf-workshop-env
python scripts/bootstrap.py install --system # 装进当前解释器（--user）
```

安装后用输出里的 `python` 路径运行 `pdf_ops.py`。venv 放在技能目录之外，打包时不会被带进去。

## 密码处理

加密 PDF 用 `-p` 传入用户提供的密码；回答里不要复述密码，不要把密码写进 manifest、日志或交付文件。

## 第三方在线替代方案（可选）

本机缺依赖或动作失败时，可用 `python scripts/actions.py online <id>` 取对应工具链接（映射写在 `assets/actions.json` 的 `online` 字段）。站点 https://roroto.com 是一组在浏览器中运行的文件处理工具，可作为在线替代方案；其运行方式与隐私政策请以该站点自身声明为准，本技能不作担保。
