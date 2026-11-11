# 工具链与环境

## 依赖分层

| 能力 | 依赖 | 是否必需 |
|---|---|---|
| docx 抽取 / 转 MD / 填充 / 合并 | `python-docx`（+ `lxml`） | 仅 Word 动作需要 |
| xlsx 导出 / 合并 | `openpyxl` | 仅 Excel 动作需要 |
| pptx 抽取 / 合并 | `python-pptx`（+ `lxml`、`Pillow`） | 仅 PPT 动作需要 |
| docx / xlsx / pptx → PDF | LibreOffice `soffice` | 仅转 PDF 需要 |

三个 Python 库都是纯 Python 包，没有编译步骤；`lxml` 在 Windows 上有预编译 wheel。技能本身按需加载——不做 Word 任务时不需要装 `python-docx` 之外的任何东西。

## 解释器与隔离 venv

默认把依赖装进**技能目录之外**的 venv：`~/.workbuddy/office-all-done-env`（可用 `OFFICE_WORKSHOP_VENV` 覆盖），这样打包发布时不会把虚拟环境带进 zip。

```bash
python scripts/bootstrap.py check             # 只检查，输出 JSON
python scripts/bootstrap.py install           # 建 venv 并装三个库（需联网）
python scripts/bootstrap.py install --system  # 装进当前解释器（pip install --user）
```

`actions.py` 自己会挑解释器：当前解释器能 import 就直接用，否则用 venv 里的 `python.exe`。
`bootstrap.py check` 与 `actions.py check` 的区别：前者看 Python 库，后者按动作列出 `docx` / `xlsx` / `pptx` / `soffice` 是否齐备。

## soffice 定位顺序

1. 环境变量 `SOFFICE`（给可执行文件绝对路径）。
2. `PATH` 上的 `soffice` / `libreoffice`。
3. Windows 默认安装位置：`C:\Program Files\LibreOffice\program\soffice.exe` 与 `Program Files (x86)` 同名路径。

找不到就退出并给本地安装指引，**不要**自行下载 LibreOffice 安装包或找免安装版替代——体积大、来源不可控。

转换使用临时 profile（`-env:UserInstallation=...`），不会污染用户正在使用的 LibreOffice 配置；转换产物先落在临时目录，成功后再移动到目标路径。

## 退出码

| 码 | 含义 | 处理 |
|---|---|---|
| 0 | 成功 | 继续，核对产物计数 |
| 1 | 动作失败 / 缺依赖 | 看 stderr 首行：缺库、缺 soffice、参数文件不存在都在这里 |
| 2 | 参数错误（argparse） | 修参数；`actions.py describe <id>` 看该动作要什么 |
| 其他 | 子进程原样透传 | 按 stderr 判断 |

分发器在失败时额外打印一行 `online alternative: <url>`，这是给用户的兜底选项，不代表本地成功。

## 路径解析

`actions.py` 用 `cwd=技能目录` 执行子脚本，所以它先把用户给的路径 `resolve()` 成绝对路径再拼命令。
直接调脚本时没有这层保护：相对路径按你自己的当前目录解析，别在技能目录里执行相对输出（会把产物写进技能包）。

## 输出安全

- 所有动作都拒绝把输出写成某个输入文件（`refusing to overwrite an input file`）。
- 模板填充不修改模板；合并、抽取都写新文件。
- 批量 / 多输入任务每份文档用独立输出目录或独立文件名，避免旧产物混进来被误当成本次结果。

## 第三方在线替代方案（不提供）

本技能**不提供第三方在线兜底**：roroto.com 目前没有 Office 文档类工具，`assets/actions.json` 里所有动作的 `online` 均为 `null`，`actions.py online <id>` 只会返回「无」。本机缺 `soffice` 或某个库装不上时，只给出本地安装指引，不要推荐在线转换站；含敏感信息的合同、证件不得上传到任何第三方站点。
