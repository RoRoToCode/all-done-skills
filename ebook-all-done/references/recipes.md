# 电子书全搞定 · 用法配方

统一入口 `python scripts/actions.py run <id> -- <参数>`，也可直接 `python scripts/<id 下划线>.py ...`。
下文用简写；所有路径都支持中文与空格。核心动作零第三方依赖。

## 默认无需逐项确认

默认不逐项确认、不覆盖用户已有产物：输出文件重名自动改名 ` (2)`，输出目录已存在且非空时同理；批量里单份失败不中断，末尾统一汇总。

```bash
python scripts/actions.py run eb-inspect --input book.epub --output inspect.json      # 已存在则写 inspect (2).json
python scripts/actions.py run eb-split --input book.epub --output split --on-conflict overwrite
python scripts/actions.py run eb-batch --input D:\books --output D:\out --action inspect --on-conflict skip
```
直接调子脚本时用环境变量：`EBOOK_ON_CONFLICT=overwrite`（Windows PowerShell：`$env:EBOOK_ON_CONFLICT='overwrite'`）。
任何策略下输出等于输入都会被拒绝；含 DRM 的书只报告不改写。

## 检查与校验

### eb-inspect 电子书体检
```bash
python scripts/eb_inspect.py --input book.epub --output inspect.json
python scripts/eb_inspect.py --input book.epub                     # 只打印摘要
```

### eb-validate 规范校验
```bash
python scripts/eb_validate.py --input book.epub --output validate.json
python scripts/eb_validate.py --input book.epub --strict          # 有 error 时退出码 5
```
检查项：mimetype 首项且未压缩、`META-INF/container.xml` 指向的 OPF 存在、dc:title/language/identifier、manifest 悬空文件、spine idref、XHTML well-formed、NCX/nav 与图片链接、加密标记。

### eb-batch 批量处理
```bash
python scripts/eb_batch.py --input D:\books --output D:\out --action inspect
python scripts/eb_batch.py --input D:\books --output D:\out --action validate --pattern "*.epub"
python scripts/eb_batch.py --input D:\books --output D:\out --action extract --format md
```
每个文件一个子目录，汇总写 `<output>/manifest.json`；单个文件失败不影响其余文件。

## 元数据与资源

### eb-meta 元数据
```bash
python scripts/eb_meta.py --input book.epub --show
python scripts/eb_meta.py --input book.epub --output out.epub --set title=新书名 --set creator=张三
python scripts/eb_meta.py --input book.epub --output out.epub --spec meta.json --set language=zh-CN
```
`--set` 可用 `key=value`，重复传入改多项；键为 dc 名（title / creator / language / publisher / identifier / description / subject / rights / contributor / date）或 `series`。`meta.json` 形如 `{"title": "…", "creator": ["甲", "乙"]}`。`--show` 只读不写。

### eb-cover 封面
```bash
python scripts/eb_cover.py --input book.epub --output cover.jpg                 # 提取
python scripts/eb_cover.py --input book.epub --replace new.jpg --output out.epub  # 替换
python scripts/eb_cover.py --generate --title "书名" --author "作者" --output out.epub --input book.epub
```
`--generate` 需要 Pillow；替换会补齐 OPF 的 `cover-image` 声明，不改原书其它内容。

### eb-images 插图资源
```bash
python scripts/eb_images.py --input book.epub --output images-dir
python scripts/eb_images.py --input book.epub --list                     # 只列清单
```
输出 `images/`（图片）、`fonts/`、`styles/` 与 `assets.json`（原始路径、media-type、尺寸、体积）。

## 目录与正文

### eb-toc 目录导出
```bash
python scripts/eb_toc.py --input book.epub --output toc-dir
```
输出 `toc.md`（缩进列表 + 章节链接）与 `toc.json`（level / title / href / path）。优先 EPUB3 `nav.xhtml`，其次 EPUB2 `toc.ncx`，都没有时从各章首个标题生成。

### eb-retoc 目录重建
```bash
python scripts/eb_retoc.py --input book.epub --toc toc.txt --output out.epub
```
`toc.txt` 每行一条：前导空格（或 Tab）决定层级，行内可用 `| 文件名.xhtml` 显式指定目标，否则按出现顺序依次对应 spine 章节。例如：
```
第一部 缘起 | chapter-001.xhtml
  第一章 初见
  第二章 山行
第二部 征程 | chapter-003.xhtml
  第三章 风雨
```
会同时重建 `toc.ncx` 与 `nav.xhtml`，并补齐 OPF 的 manifest / spine 引用。

### eb-extract 正文提取
```bash
python scripts/eb_extract.py --input book.epub --output out-dir
python scripts/eb_extract.py --input book.epub --output out-dir --format txt --no-images
```
输出 `full.md`（或 `full.txt`）、`chapters/chapter-NNN.md`、`images/`、`manifest.json`（章节标题、字数、原路径）。Markdown 保留标题 / 段落 / 列表 / 引用 / 表格 / 代码 / 图片。

### eb-search 全文检索
```bash
python scripts/eb_search.py --input book.epub --query 长安 --output hits.json
python scripts/eb_search.py --input book.epub --query 长安 --output hits.md --context 40
python scripts/eb_search.py --input book.epub --regex "第[一二三]章" --ignore-case --output hits.json
```
`--query` 与 `--regex` 二选一；输出命中章节、字符偏移、上下文与总命中数。

## 结构编辑

### eb-split 按章拆分
```bash
python scripts/eb_split.py --input book.epub --output split-dir                  # 按目录顶层分卷
python scripts/eb_split.py --input book.epub --output split-dir --by chapters   # 每章一本
python scripts/eb_split.py --input book.epub --output split-dir --by count --per 5
```
每本独立 EPUB3，带自己的目录与封面（沿用原书封面）；输出 `manifest.json` 记录分卷范围。

### eb-merge 多本合并
```bash
python scripts/eb_merge.py --inputs "a.epub,b.epub,c.epub" --output all.epub --title 合集
python scripts/eb_merge.py --input-dir D:\books --output all.epub
```
书名作一级目录、原章节作二级；图片等资源重映射到 `images/book-N/` 避免同名冲突。

## 生成与导出

### eb-from-md Markdown 生成 EPUB
```bash
python scripts/eb_from_md.py --input book.md --output book.epub --title "书名" --author "作者"
python scripts/eb_from_md.py --input book.md --output book.epub --split-level 2 --cover cover.jpg
python scripts/eb_from_md.py --input page.html --output book.epub --html
```
默认按一级 `#` 切章；`--split-level 2` 连二级 `##` 也切。生成的 EPUB3 同时带 `nav.xhtml` 与 `toc.ncx`，兼容老阅读器。

### eb-from-text 纯文本生成 EPUB
```bash
python scripts/eb_from_text.py --input novel.txt --output novel.epub --title "书名"
python scripts/eb_from_text.py --input novel.txt --output novel.epub --pattern "^第[零一二三四五六七八九十百千\\d]+章"
```
默认正则覆盖「第X章 / 第X回 / Chapter N / 卷X」；`--encoding gb18030` 可处理老式 TXT。

### eb-to-pdf 转 PDF
```bash
python scripts/eb_to_pdf.py --input book.epub --output book.pdf
python scripts/eb_to_pdf.py --input book.epub --output book.pdf --page-size A5 --no-images
```
用本机 Edge / Chrome 无头打印，中文走系统字体（微软雅黑 / 黑体 / Noto Sans CJK）。可用 `EBOOK_BROWSER` 环境变量指定浏览器路径。

## 格式互转

### eb-convert Calibre 互转
```bash
python scripts/eb_convert.py --input book.epub --output book.mobi
python scripts/eb_convert.py --input book.epub --output book.pdf --extra "--pdf-page-numbers --margin-left 40"
python scripts/eb_convert.py --input book.azw3 --output book.epub
```
输出格式按扩展名推断，也可 `--to epub3` 显式指定。需要 Calibre 的 `ebook-convert` 在 PATH；未安装时给出安装指引。**含 DRM 的输入不在支持范围内**。
