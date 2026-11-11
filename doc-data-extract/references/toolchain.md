# 依赖、退出码与排错

## 依赖清单

| 依赖 | 用途 | 缺失影响 |
|---|---|---|
| 宿主 workbuddy-pdf CLI | PDF 高保真文本/表格抽取 | PDF 退化为 pypdf，表格抽取不可用 |
| `pypdf` | PDF 兜底文本抽取 | 无法读取 PDF |
| `python-docx` | DOCX 文本与表格 | 无法读取 Word |
| `openpyxl` | XLSX 读取与表格导出 | 无法读取 Excel |
| `python-pptx` | PPTX 文本与表格 | 无法读取 PowerPoint |
| `bs4` | HTML 文本与表格 | 无法读取网页 |

CSV 汇总与 JSON 导出全部用标准库（`csv` / `json`），**不需要 pandas**。

一键安装（均非必需，按需装）：

```bash
pip install python-docx openpyxl python-pptx beautifulsoup4 pypdf
```

`actions.py check` 会把 pip 包名映射到真实模块名（`python-docx`→`docx`、`python-pptx`→`pptx`）后再检测；缺失只是**软警告**，不会阻断纯文本/Office 之外的动作。

## 退出码

- `0`：成功
- `1`：参数错误或动作明确失败（如 doc-convert --to pdf 未实现）
- `2`：`template-extract --strict` 存在必填字段缺失
- `69`：宿主 PDF 组件仍在下载，可重试
- `127`：宿主 PDF CLI 不存在

## 环境约定

- PDF 组件定位顺序：`WORKBUDDY_PDF` → PATH `workbuddy-pdf` → `~/.workbuddy/external-packages/pdf-cli` → 宿主插件 `run.ps1/run.sh`。
- 不下载任何替代二进制；缺依赖时如实说明并给出在线替代链接。
- 输出不覆盖输入；批量任务每份文档用独立输出目录。
- 密码 / 凭据只经参数传入，不写日志或回答。
