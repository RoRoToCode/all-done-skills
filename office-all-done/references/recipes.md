# 任务配方与排错

所有命令都从技能根目录执行（`cd` 到 `office-all-done/`），或把 `scripts/...` 换成绝对路径。
用户给的文件路径用绝对路径最稳：动作分发器会把相对路径按**调用者的当前目录**解析，而不是按技能目录。

## 1. Word（docx）

```bash
python scripts/actions.py run docx-extract --input 合同.docx --output 合同.txt
python scripts/actions.py run docx-to-md   --input 合同.docx --output 合同.md
python scripts/actions.py run docx-fill    --input 模板.docx --output 已填.docx --data "客户=示例科技;金额=1,280,000"
python scripts/actions.py run docx-merge   --inputs a.docx b.docx c.docx --output 合集.docx --page-break
```

直接调脚本可拿到更细的参数：

```bash
python scripts/doc_extract.py 合同.docx -o 合同.txt
python scripts/doc_to_md.py   报告.docx -o 报告.md --images 报告.assets   # 同时导出图片文件
python scripts/doc_fill.py    模板.docx -o 已填.docx --data data.json
python scripts/doc_merge.py   a.docx b.docx -o 合集.docx --page-break
```

- **抽取**：标题按 `Heading N` 转成 `#`，列表保留 `-` 前缀，表格用制表符分隔并加 `<!-- table N -->` 包裹；超链接取链接文字。图片不进文本。
- **转 Markdown**：块与块之间留空行（否则渲染时会粘成一段）；`Title` 与 `Heading 1` 都映射成 `#`；列表按 `w:ilvl` 缩进，有序列表统一写 `1.` 交给渲染器自动编号；图片输出 `![](image1.png)` 占位，加 `--images DIR` 才落盘。
- **模板填充**：只认 `{{key}}`（允许 `{{ key }}`）。覆盖正文段落、表格单元格、页眉页脚。占位符被拆到多个 run 时，以第一个 run 的格式为准。产物是新文件，模板不会被改。
- **合并**：第一个文件提供页面设置、主题、页眉页脚；后续文件的样式表、列表编号定义（`w:numPr` / `numbering.xml`）、图片、外部超链接都会迁移过来。后续文件的 `sectPr` 会被丢弃，所以最终是一个节。脚注、尾注、批注、修订不合并。

## 2. Excel（xlsx）

```bash
python scripts/actions.py run xlsx-extract --input 台账.xlsx --output out/ --format csv
python scripts/actions.py run xlsx-extract --input 台账.xlsx --output out/ --format json
python scripts/actions.py run xlsx-extract --input 台账.xlsx --output out/ --format md
python scripts/actions.py run xlsx-merge   --inputs 一月.xlsx 二月.xlsx --output 上半年.xlsx
```

- `-o` 对 `xlsx-extract` 是**目录**，每张工作表一个文件，文件名取工作表名（`/` `\` 替换成 `_`）；空表跳过并打印提示。
- `csv` 带 BOM（Excel 双击不乱码）；`json` 以首行为表头转对象数组；`md` 出 GFM 表格。
- `data_only=True` 读取，公式取**缓存的计算结果**；从未在 Excel 里打开保存过的公式文件，结果可能是空字符串——这是 openpyxl 的限制，不是抽取失败。
- 合并保留列宽、行高、合并单元格、冻结窗格；同名工作表自动加 `_2`、`_3` 后缀。

## 3. PowerPoint（pptx）

```bash
python scripts/actions.py run pptx-extract --input 汇报.pptx --output 汇报.txt
python scripts/actions.py run pptx-merge   --inputs 1.pptx 2.pptx --output 合集.pptx
```

- 抽取按 `--- Slide N ---` 分节，顺序为标题占位符、正文文本框、表格行，最后附 `[备注]`。
- 合并时逐页深拷贝形状树，图片通过重建关系（`r:embed` → 新 rId）随幻灯片迁移；音视频、OLE 部件不复制，脚本会报数量。版式按源页版式名匹配，匹配不到用空白版式。

## 4. 转 PDF

```bash
python scripts/actions.py run docx-to-pdf --input 报告.docx --output 报告.pdf
python scripts/actions.py run xlsx-to-pdf --input 台账.xlsx --output 台账.pdf
python scripts/actions.py run pptx-to-pdf --input 汇报.pptx --output 汇报.pdf
```

- 统一走 `soffice --headless --convert-to pdf`，先转到临时目录再移动到目标路径（soffice 不允许指定输出文件名）。
- 缺 LibreOffice 时**不会假装成功**：打印「本机未安装 LibreOffice」加本地安装指引，退出码 1。不会自动下载安装包。
- 中文变方框说明系统缺 CJK 字体，与转换无关。
- `xlsx` 输出页数取决于打印区域与缩放，宽表常被切成多页；`pptx` 一页幻灯片对应一页 PDF，动画不保留。

## 常见故障

| 现象 | 原因 | 处理 |
|---|---|---|
| `缺少 python-docx / openpyxl / python-pptx` | 依赖没装 | `python scripts/bootstrap.py install`，之后用输出里的 venv python 跑脚本 |
| `missing dependencies: soffice` | 没装 LibreOffice | 装 LibreOffice，按提示在本机安装；也可 `SOFFICE=/path/to/soffice` 指定 |
| `refusing to overwrite an input file` | 输出路径与某个输入相同 | 换输出名；批量任务用独立目录 |
| 合并后页码、目录错乱 | 域不会自动重算 | 在 Word 里全选按 F9，或对目录右键「更新域」 |
| 合并后列表丢了编号 | 源文件用的是样式化列表，但目标缺该样式 | 确认样式已随合并迁移；仍有问题时在 Word 中重新套用列表样式 |
| Markdown 里图片是 `![](image1.png)` 但没有文件 | 默认只占位 | `--images DIR` 重新导出 |
| `--data 无法解析` | Windows 命令行吞掉了 JSON 的引号 | 改用 JSON 文件，或 `key=value`（多组用 `;` 分隔） |
| 提取结果漏字 / 顺序乱 | 文本框、艺术字、嵌套表格的解析局限 | 回看原文件；必要时先另存为 .docx 再抽 |
| Excel 公式列全空 | 公式从未被 Excel 计算过，无缓存值 | 用 Excel 打开另存一次，或用 `data_only=False` 自读公式 |
