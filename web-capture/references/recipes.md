# 常见任务配方

所有命令在技能根目录执行；`-o` 一律是**输出目录**。统一入口的精细参数走 `--extra`，且必须放最后。同一命令重跑时输出目录自动避让成 `<目录>-2`、`-3`，不会覆盖上次的产物（看 stdout 的 `output` 拿实际路径）。

## 1. 保存网页原文

```bash
python scripts/actions.py run web-fetch --input https://example.com -o out/fetch
python scripts/actions.py run web-fetch --input https://example.com -o out/fetch-assets \
  --extra --assets --max-assets 100
```

`page.html` 保持响应体原样，`meta.json` 记录最终 URL、状态码、编码、sha256、链接数。`--assets` 额外下载 CSS/JS/图片到 `assets/` 并生成引用已改写的 `page.local.html`。

## 2. 单文件离线存档

```bash
python scripts/actions.py run web-single --input page.html -o out/single \
  --extra --max-assets 120 --max-asset-bytes 5000000
```

CSS、JS、图片（含 CSS 内 `url()`）内联成 `data:` URI，`page.single.html` 可单独拷走。失败资源保留原外链并记在 `resources.json` / `manifest.json.warnings`。与浏览器「另存为 MHTML」不同，产物是普通 HTML，不是 `.mhtml`。

## 3. 整页截图 / 转 PDF

```bash
python scripts/actions.py run web-screenshot --input https://example.com -o out/shot \
  --extra --width 1280 --height 900 --wait 1.5
python scripts/actions.py run web-to-pdf --input ./page.html -o out/pdf \
  --extra --browser "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
```

`capture.json` 的 `engine=cdp` 才是精确整页；`degraded=true` 说明只截到视口。本地 HTML 可直接传路径，会转成 `file://` 再渲染。

## 4. 正文转 Markdown

```bash
python scripts/actions.py run web-to-md --input https://example.com/article -o out/md
python scripts/actions.py run web-to-md --input page.html -o out/md-all \
  --extra --all --no-frontmatter
```

`page.md` 带 YAML 元信息，标题层级在 `outline.json`。导航/广告被启发式剔除，抽错时用 `--all` 拿整页对照。

## 5. 抽链接、图片、表格、元数据

```bash
python scripts/actions.py run web-extract --input https://example.com -o out/extract
python scripts/actions.py run web-extract --input page.html -o out/links \
  --extra --kind links,tables
```

CSV 带 UTF-8 BOM，Excel 直接打开不乱码；`meta.json` 含 og:* / description / canonical / JSON-LD / 标题层级。

## 6. 批量采集

`urls.txt`（每行一个网址、`#` 注释）、`urls.json`（数组或 `{"urls":[...]}`）、`urls.csv`（含 `url` 列）均可：

```bash
python scripts/actions.py run web-batch --input urls.txt -o out/batch \
  --extra --format all --delay 1.0 --limit 100
```

每条一个 `NN-<slug>/` 子目录，总目录 `index.csv` 给出成功/失败与字节数；单条失败不影响其它条目。输入也可给含 `*.html` 的目录，直接批量转本地文件。

## 7. 站内浅层爬取

```bash
python scripts/actions.py run web-crawl --input https://example.com -o out/crawl \
  --extra --depth 2 --max-pages 40 --delay 1.0 --include "/docs/" --exclude "/print"
```

默认同域、遵守 robots.txt、跳过静态资源扩展名。产物 `pages/*.html|*.md` + `urls.csv` + `graph.json`（链接边）。`--cross-origin` 会放开域名限制，使用前务必确认授权。

## 8. 网页变更对比

```bash
python scripts/actions.py run web-diff -o out/diff \
  --extra --old old.html --new https://example.com
```

`--old` / `--new` 可以是网址、本地 HTML、含 `page.html` 的快照目录；也可以写成配置 JSON（`{"old":"...","new":"..."}`）传给 `--input`。`diff.md` 给人看，`diff.json` 给程序用（新增/删除链接、图片、标题、meta 与 unified diff）。加 `--strict` 后**有变化返回退出码 2**，适合定时任务判断。

## 9. 组合链路

```bash
# 存档 → 正文 → 结构化 → 截图，四份产物各自独立目录
python scripts/actions.py run web-fetch      --input https://example.com -o out/1-fetch
python scripts/actions.py run web-to-md      --input out/1-fetch/page.html -o out/2-md
python scripts/actions.py run web-extract   --input out/1-fetch/page.html -o out/3-extract
python scripts/actions.py run web-screenshot --input out/1-fetch/page.html -o out/4-shot
```

后续处理边界：PDF 相关走 `pdf-workshop`，截图 OCR 走 `ocr-workshop`，多格式文档字段抽取走 `doc-data-extract`。

## 边界

- 不生成可搜索 PDF、不打包成 `.mhtml`、不做定时监控（定时可用宿主自动化调用 `web-diff --strict`）。
- 不破解登录/付费墙/验证码，不处理无限滚动的交互加载，不抓取需授权的数据。
- roroto.com 没有网页类在线工具，本技能所有动作的 `online` 均为 `null`；依赖缺失时没有在线兜底，别给用户编链接。
