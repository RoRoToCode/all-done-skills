---
name: "web-capture"
display_name: "网页全搞定"
display_name_en: "Web Capture, All Done"
description: "Capture, archive and convert web pages locally. Nine actions — save raw HTML with metadata, pack a single-file offline HTML, full-page screenshot, URL to PDF, readable Markdown, structured link/image/table/metadata extraction, batch capture, polite shallow crawl and page diff. Triggers include 网页全搞定 / 网页截图 / 整页截图 / 网页转 PDF / 网页转 Markdown / 保存网页 / 离线网页 / 抓取网页 / 抽取链接 / 批量抓网页 / 爬取网站 / 网页变更对比 / web capture / url to pdf / web screenshot. Standard library for all text actions; Edge/Chrome headless only for rendering. Local-first, robots.txt respected, no upload to third parties."
description_zh: "本机网页采集与转换：原样保存 HTML、单文件离线存档、整页截图、网页转 PDF、正文转 Markdown、链接/图片/表格/元数据抽取、批量采集、站内浅层爬取、网页变更对比。九个动作统一入口，文本类纯标准库零依赖，渲染类用本机 Edge/Chrome headless。默认遵守 robots.txt，不上传第三方；说「网页全搞定」「网页截图」「网页转 PDF」「网页转 md」即用。"
description_en: "Local web capture toolkit with nine actions: save HTML, single-file offline archive, full-page PNG, URL to PDF, readable Markdown, structured extraction, batch capture, shallow crawl and page diff. Text actions need only the Python standard library; rendering uses local Edge/Chrome headless. Robots-aware, local-first, no third-party uploads."
version: "1.4.1"
agent_created: true
---

# 网页全搞定

本机网页采集与转换技能。9 项动作统一从 `python scripts/actions.py` 调用，动作清单的唯一数据源是 `assets/actions.json`。文本类动作**零第三方依赖**（标准库 HTTP + `html.parser`），只有截图 / 转 PDF 需要本机 Edge 或 Chrome。

## 统一入口

```bash
python scripts/actions.py list              # 全部动作
python scripts/actions.py describe <id>     # 参数、依赖、在线替代
python scripts/actions.py check             # 各动作依赖是否就绪
python scripts/actions.py browser           # 浏览器路径与渲染引擎状态
python scripts/actions.py run <id> --input <URL或文件> -o out/
python scripts/actions.py online <id>       # 对应的在线工具（本站没有，返回「无」）
```

`--input` 接受 http(s) 网址、本地 HTML 文件、URL 列表文件（`web-batch`）或快照目录（`web-diff`）；`--url` 是它的别名。精细参数用 `--extra` 原样透传给动作脚本，**必须放在命令最后**；`--width` / `--depth` / `--max-pages` / `--kind` / `--timeout` / `--browser` 也可直接作为 `run` 的参数，同一参数重复出现时自动只保留最后一个值：

```bash
python scripts/actions.py run web-screenshot --input https://example.com -o out/ \
  --extra --width 1280 --height 900 --wait 1.5

python scripts/actions.py run web-diff -o diff/ \
  --extra --old old.html --new https://example.com --strict
```

更多配方见 `references/recipes.md`；编码、robots、浏览器与降级排查见 `references/toolchain.md`。

## 动作 id

| 组 | 动作 |
|---|---|
| 采集 | `web-fetch`（原样保存 + meta）、`web-single`（单文件离线 HTML） |
| 渲染 | `web-screenshot`（整页 PNG）、`web-to-pdf`（打印 PDF） |
| 转换 | `web-to-md`（正文 Markdown）、`web-extract`（链接/图片/表格/元数据） |
| 批量 | `web-batch`（URL 列表）、`web-crawl`（同域浅层爬取） |
| 分析 | `web-diff`（两次快照对比） |

## 输出约定

每个动作一个**输出目录**，`manifest.json` 记录来源、产物清单与 `warnings`；批量/爬取再给 `index.csv` / `urls.csv`。

| 动作 | 主要产物 |
|---|---|
| `web-fetch` | `page.html`、`meta.json`；`--assets` 时另有 `assets/`、`resources.json`、`page.local.html` |
| `web-single` | `page.single.html`、`resources.json` |
| `web-screenshot` | `page.png`、`capture.json`（engine / full_page / degraded） |
| `web-to-pdf` | `page.pdf`、`capture.json` |
| `web-to-md` | `page.md`、`outline.json` |
| `web-extract` | `extract.json`、`links.csv`、`images.csv`、`tables/table-NNNN.csv`、`meta.json`（CSV 为 UTF-8-BOM） |
| `web-batch` | `NN-<slug>/page.html|page.md|extract.json`、`index.csv`、`manifest.json` |
| `web-crawl` | `pages/*.html|*.md`、`urls.csv`、`graph.json`、`manifest.json` |
| `web-diff` | `diff.md`、`diff.json` |

## 路由边界

- 只想**读取/总结某个网页内容**、不需要落盘产物 → 用内置网页读取能力，不要启动本技能。
- 已经下载好的 **PDF**（合并、加水印、OCR、转 Word）→ `pdf-workshop`；扫描件识别 → `ocr-workshop`。
- **多格式文档**（Word/Excel/PPT/PDF/HTML）的字段、表格、实体抽取与跨文档检索 → `doc-data-extract`；本技能只面向**在线网页与网页存档**。
- 截图得到的 PNG 要裁剪/压缩/OCR → `image-all-done` / `ocr-workshop`。
- 需要登录态、付费墙、验证码、无限滚动后加载的内容、JavaScript 登录后数据 → 本技能不绕过，`web-crawl` 与 `web-fetch` 只看服务端返回的原始 HTML；渲染类动作可见 JS 执行结果，但不做交互。

## 默认无需逐项确认

一句话下任务就跑完，过程中不逐项确认；但安全底线不自动放行。

- **不逐项确认**：抓取、存档、渲染、批量、爬取、对比各一次调用完成，缺参数就地用默认值（宽 1440、深度 1、爬取上限 20 页、批量上限 50 条）。
- **自动降级**：CDP 不可用退到命令行视口渲染并标注 `degraded`；编码声明不对自动回退 `gb18030`；单个资源下载失败保留原外链；批量/爬取单条失败不中断，照常写 `index.csv` / `urls.csv` 与 `warnings`。
- **重名自动避让**：输出目录里已有 `manifest.json` 时自动改用 `<目录>-2`、`-3`，不覆盖上一次产物；实际路径写在 stdout 与 `manifest.json`。想重跑同一目录，换新目录或自行删除旧目录即可。
- **不放行安全底线**：默认遵守 `robots.txt`、限速与深度/页数上限，只抓公开页面，不绕登录、付费墙、验证码与反爬；输出不得覆盖输入，不上传第三方，不采集需授权的数据。

## 约束

- **只抓公开页面**：默认遵守 `robots.txt`，`--no-robots` 需用户明确要求；不绕过登录、付费墙、验证码与反爬机制，不用于采集个人信息；使用者须自行遵守目标站点的 robots.txt、服务条款、著作权与数据合规要求，被抓取站点的版权与条款由使用者自行负责。
- **克制请求**：爬取默认同域、限速 0.5s、深度 1、上限 20 页；批量默认上限 50、间隔 0.6s。调大参数前先确认目标站点允许。
- **不上传第三方**：除用户给定的目标站点（及其 robots.txt / 页面资源）外，不向任何服务发送数据；访问用户指定的网址本身会向该站点发出请求，其记录、存储与隐私以该站点自身声明为准；roroto.com 没有网页类在线工具，依赖缺失时如实说明，不要编造在线替代链接。
- 输出不得覆盖输入；每个任务独立输出目录；`meta.json` 只保留安全响应头，不记录 Cookie / Authorization。
- 结果带证据：`warnings`（robots 拒绝、资源下载失败、正文抽取退化、CDP 降级、编码回退）必须写进结论；`capture.json` 的 `degraded=true` 表示只截到视口、**不是整页长图**，必须点名。
- 网页是动态内容：正文抽取是可读性启发式，导航、广告、脚本渲染内容可能漏抽或多抽；涉及合同、公告、价格、法务等请人工核对原文。

## 交付

给出产物路径与关键校验（页数/字节数/链接数/抓取页数/变更行数），点名 `warnings` 与降级情况。失败时给出具体原因（HTTP 状态、robots 拒绝、缺浏览器、编码回退）和一行修复建议，不输出功能清单或操作说明。

## 免责声明
- **本地优先**：本技能全程在本机运行，原始文件不会上传任何云端或第三方服务器；本技能不提供第三方在线替代方案，缺依赖时只给出本地安装指引。
- **结果仅供参考**：正文抽取、表格还原、Markdown 转换与渲染截图均依赖启发式算法与浏览器实现，可能出现错漏、版式偏移或内容缺失；动态渲染、字体、地域与登录态差异会改变结果。关键内容务必人工核对原始页面。
- **依赖与第三方组件**：文本类动作仅依赖 Python 标准库；截图与 PDF 依赖本机 Microsoft Edge / Google Chrome（CDP 与 headless 命令行接口），未安装、版本过旧或被系统策略禁用时功能受限或降级。第三方组件均由使用者自行安装并各自适用其独立许可，本技能不分发其二进制、库或模型权重；完整清单与许可提示见 THIRD-PARTY.md。
- **按现状提供**：本技能以 MIT 许可按「现状」提供，不提供任何明示或暗示的担保（含适用性、准确性、无中断、无损害）。因使用本技能产生的任何直接或间接损失，由使用者自行承担；处理前请自行备份原始文件。
