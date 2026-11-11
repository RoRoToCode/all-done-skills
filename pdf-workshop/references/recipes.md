# 任务配方与排错

## 1. 生成 / 导出 PDF

```bash
python scripts/md_to_pdf.py report.md -o report.pdf --title "季度报告"
python scripts/md_to_pdf.py page.html -o page.pdf --html
python scripts/md_to_pdf.py report.md -o wide.pdf --landscape --css my.css
```

- Markdown 支持标题、段落、有序/无序列表、GFM 表格、围栏代码块、引用、分隔线、行内粗斜体/代码/链接/图片、`<!-- pagebreak -->` 手动分页。
- 样式来自 `assets/report.css`，可复制一份用 `--css` 覆盖；`@page` 尺寸由脚本注入。
- Markdown 已含一级标题时不要再传 `--title`，否则标题会重复。
- 图片请用相对路径且和 Markdown 同目录，或先转成绝对路径；浏览器以 `file://` 打开 HTML。
- 长文档先看产物大小和页数；若出现空白页，检查 HTML 里是否有多余的分页 div。

## 2. 编辑与批量处理

```bash
python scripts/pdf_ops.py info input.pdf
python scripts/pdf_ops.py rotate input.pdf -o out.pdf --angle 90 --pages 1,3-5
python scripts/pdf_ops.py delete input.pdf -o out.pdf --pages 2,7
python scripts/pdf_ops.py reorder input.pdf -o out.pdf --order 3,1,2
python scripts/pdf_ops.py crop input.pdf -o out.pdf --box 20,20,20,20
python scripts/pdf_ops.py page-numbers input.pdf -o out.pdf --position br --format "{n}/{total}"
python scripts/pdf_ops.py watermark input.pdf -o out.pdf --text "内部资料" --opacity 0.12
python scripts/pdf_ops.py merge a.pdf b.pdf -o merged.pdf
python scripts/pdf_ops.py split input.pdf -o pages/
python scripts/pdf_ops.py encrypt input.pdf -o locked.pdf --new-password <pwd>
python scripts/pdf_ops.py decrypt locked.pdf -o plain.pdf -p <pwd>
python scripts/pdf_ops.py batch ./invoices/ -o ./done/ --op watermark --text "已归档"
python scripts/extract_pages.py input.pdf -o excerpt.pdf --pages 3-5
python scripts/extract_pages.py input.pdf -o excerpt.pdf --pages 1,3-5,8
```

- `extract_pages.py` 只保留指定页另存（1 起算，支持 `3-5` / `1,3-5`）；越界会报错并给出总页数，校验页数、逐页文字与页面尺寸，不一致就删除输出。加密 PDF 先 `decrypt`。
- 页码用 ASCII 字体绘制，只支持数字与英文；需要中文标注请用 `watermark`。
- 水印通过浏览器生成一层透明 PDF 再叠加，支持中文，按页面尺寸缓存，A4 混合横竖页也能处理。
- `--box` 是四边内缩点数（pt），不是绝对坐标。
- 批量处理会写 `batch-manifest.json`，逐文件记录成功/失败；失败不要当成整批完成。
- 批量 `delete` 必须显式给 `--pages`，脚本会拒绝空值以免误删全部页面。
- 输出不要覆盖输入文件，尤其是批量任务；先写新目录，核对后再替换。
- 加解密走 pypdf，不经官方 CLI：Windows 版 CLI 不能写加密文档。AES 算法需 `cryptography`，默认 RC4-128 无额外依赖。

## 3. 扫描件 OCR 与表格还原

```bash
python scripts/ocr_pdf.py scan.pdf -o out/ --lang chi_sim+eng --dpi 200 --tables
```

产物：`layout.md`（CLI 版面识别）、`tables/`（CSV）、`pages/`（逐页 txt）、`ocr.md`（带 `<!-- page N -->` 标记）、`manifest.json`。

引擎检查顺序：

1. CLI `-f md-plain` 自动检测扫描页，能保留归组后的正文和表格；`-f table` 输出 CSV。
2. Tesseract 兜底：逐页渲染 PNG → `tesseract -l chi_sim+eng --psm 3` → 逐页文本。
3. RapidOCR 兜底（无需外部二进制）：逐页渲染 PNG → `rapidocr_onnxruntime` 识别 → 按文字框纵坐标聚成行、横坐标排序，3 列以上且连续的行自动升格为 Markdown 表格。
4. 三者都不可用：明确告知用户「本机缺 OCR 引擎」，不要报「文件是空白的」；给出在线替代方案 `https://roroto.com/tools/pdf-ocr/`（请以该站点自身声明为准）。

安装与环境变量：

- RapidOCR：`python scripts/bootstrap.py install --ocr`（装进当前解释器；模型随包，离线可用）。**不要**直接 `pip install rapidocr-onnxruntime`——它会连带解析出 44MB 的 `opencv-python`，网速差时长时间卡住；bootstrap 在 `cv2/numpy/onnxruntime/PIL/yaml/shapely/pyclipper/six` 都可导入时走 `--no-deps`，只补真正缺的包。
- Tesseract：`tesseract --list-langs` 确认有 `chi_sim` / `eng`；中文需额外语言包。
- 非默认路径用 `TESSERACT` 或 `PDF2DOCX_TESSERACT` 指向可执行文件；PaddleOCR 用 `PDF2DOCX_PADDLEOCR`、`PDF2DOCX_PADDLE_PYTHON`；语言用 `PDF2DOCX_OCR_LANG`。
- 扫描表格的行列与合并跨度为近似识别，结论必须回看原页 PNG 核对。
- 本脚本产出的是可检索文本，不是「带隐形文字层的 PDF」。需要后者时另装 `ocrmypdf`（依赖 Tesseract + Ghostscript），或说明该限制。

## 4. 跨文档检索、对比与字段抽取

```bash
python scripts/cross_doc.py index a.pdf b.pdf ./archive/ -o index.json
python scripts/cross_doc.py search "违约金" -i index.json --context 80
python scripts/cross_doc.py search "第[一二三]条" -i index.json --regex
python scripts/cross_doc.py compare -i index.json --top 20
python scripts/cross_doc.py fields -i index.json --preset contract
```

- `index` 用 CLI `-f md` 抽取，按 `<!-- page N -->` 切页；无页码标记时整篇记为第 1 页并写入 `warnings`。回答引用 PDF 文件页序，印刷页码不同时注明。
- `search` 返回文件、页号、命中词和上下文片段；`--regex` 打开正则。
- `compare` 做行级 `SequenceMatcher` 相似度 + 内容集合 Jaccard，并列出仅出现在某一方的行。适合版本差异，不适合语义等价判断。
- `fields` 预设：`general`（日期、金额、百分比、邮箱、URL、手机号）、`contract`（甲方/乙方、金额、签署/生效日期、违约金）、`finance`（营收、净利润、总资产、同比）。正则命中只是候选，必须回看原页确认单位、表头与上下文。

## 5. 页面整理：旋转 / 裁边 / 删页 / 页码

```bash
python scripts/pdf_ops.py rotate a.pdf -o rot.pdf --angle 90 --pages 1,3-5
python scripts/pdf_ops.py crop a.pdf -o crop.pdf --box 20,20,20,20     # 左,下,右,上（pt）
python scripts/pdf_ops.py delete a.pdf -o del.pdf --pages 2,7-9
python scripts/pdf_ops.py page-numbers a.pdf -o num.pdf --start 5 --position br
```

经统一入口时，额外参数放在 `--extra` 之后（它右侧的所有内容原样透传给脚本）：

```bash
python scripts/actions.py run pdf-rotate --input a.pdf --output rot.pdf --angle 180
python scripts/actions.py run pdf-page-number --input a.pdf --output num.pdf --extra --start 5 --position bl
```

## 6. 压缩与脱敏

```bash
python scripts/pdf_compress.py big.pdf -o small.pdf --level balanced   # 结构无损 + 图片有损
python scripts/pdf_compress.py big.pdf -o small.pdf --no-images        # 完全无损
python scripts/pdf_redact.py a.pdf -o clean.pdf --text 张三 --text 13800138000
python scripts/pdf_redact.py a.pdf -o clean.pdf --pattern '\d{18}' --pages 1-3 --fill white
```

压缩报告里的 `images_reencoded` / `lossless` 是判断"有没有画质损失"的依据；`saved_percent` 为 0 或负数时脚本会明确告警，说明原文件已优化或图片占比很低。

脱敏是**真删除**文字对象，不是叠加白块（白块下的文字仍可复制）；扫描件没有文字层，命中 0 处时会告警——这种情况要先 `pdf-ocr` 或 `ocr-searchable-pdf`。

## 7. 表单字段

```bash
python scripts/pdf_forms.py list form.pdf -o fields.json
python scripts/pdf_forms.py fill form.pdf -o filled.pdf --data "姓名=张三;日期=2026-11-09"
python scripts/pdf_forms.py fill form.pdf -o filled.pdf --fields values.json
```

复选框传 `true` / `false`，脚本会映射成文件里声明的导出状态（通常 `/Yes`、`/Off`）。写值不扁平化，产物仍可编辑；需要只读版本时再打印成 PDF。

## 常见故障

| 现象 | 原因 | 处理 |
|---|---|---|
| `cli_not_found` | 组件未下载或安装路径非标准 | 等待后重试；或设置 `WORKBUDDY_PDF` / `WORKBUDDY_PDF_SKILL_DIR` |
| 退出码 69 | 后台下载未完成 | 已自动重试 3 次，仍失败就说明组件未就绪，不要装替代二进制 |
| 浏览器生成 0 字节 | 浏览器被策略拦截 / 路径错误 | 用 `PDF_BROWSER` 指定；检查 stderr；确认 `--headless` 可用 |
| 中文变方框 | 系统缺 CJK 字体 | 安装中文字体，或改 `assets/report.css` 的 font-family |
| `ModuleNotFoundError: pypdf` | 未装可选依赖 | `bootstrap.py check` → `bootstrap.py install` |
| 提取结果漏字 / 顺序乱 | 版面识别局限 | 换 `md-plain` / `structure`，并用 `render` 出 PNG 回看原页 |
| 批量产物混入旧文件 | 复用了输出目录 | 每批用新目录，检查 manifest |
