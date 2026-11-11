# 依赖与排错

## 依赖矩阵

| 能力 | 依赖 | 是否必需 |
|---|---|---|
| `web-fetch` / `web-single` / `web-to-md` / `web-extract` / `web-batch` / `web-crawl` / `web-diff` | Python 3.9+ 标准库（`urllib` / `html.parser` / `difflib` / `csv`） | 必需，无需 pip 安装 |
| `web-screenshot` / `web-to-pdf` | 本机 Microsoft Edge 或 Google Chrome | 必需；不下载浏览器、不装 Playwright |
| 可选增强 | `beautifulsoup4` / `lxml` | 不需要，本技能未使用 |

刻意保持零 pip 依赖：网页技能的失败大多来自网络、编码与浏览器策略，加第三方解析器不会解决这些问题，反而让离线机器装不上。

## 自检

```bash
python scripts/bootstrap.py check                  # 标准库 / 浏览器 / 可选库状态
python scripts/bootstrap.py browser               # 浏览器路径与渲染引擎
python scripts/bootstrap.py probe https://example.com   # 连通性、编码、robots、标题
python scripts/actions.py check                   # 9 个动作逐项依赖
python scripts/actions.py browser                 # 同上，JSON 输出
```

`bootstrap.py check` 在浏览器缺失时返回退出码 2，文本类动作仍然可用。

浏览器查找顺序：`WEB_CAPTURE_BROWSER` 环境变量 → `--browser` 参数 → Edge/Chrome 的 Windows、Linux、macOS 默认安装路径 → `PATH` 中的 `msedge` / `chrome` / `chromium`。

## 渲染双通道

1. **CDP（首选）**：启动 `--headless=new --remote-debugging-port=0`，用内置的最小 WebSocket 客户端调用 `Page.navigate` / `Page.getLayoutMetrics` / `Page.captureScreenshot`（或 `Page.printToPDF`），先按内容高度重设设备尺寸再截图，得到真正的整页长图。
2. **命令行降级**：CDP 建连、握手或调用失败时，退回 `--screenshot=...` / `--print-to-pdf=... --virtual-time-budget=5000`，只覆盖 `--window-size` 视口。`capture.json` 里 `engine=cli`、`degraded=true`、`warnings` 会写明原因，**必须转达给用户**。

PDF 生成后会检查 `%PDF-` 文件头；截图不检查 PNG 内容（浏览器可能返回空白页），需要肉眼确认。

## 编码与 robots

- 编码优先级：HTTP `Content-Type` charset → BOM → `<meta charset>` → UTF-8 → GB18030 → Big5 → Latin-1。中国大陆站点的 GBK 页面会正确回退到 `gb18030`，`meta.json` 的 `encoding` 可核对。
- 只请求 `gzip, deflate`，不请求 brotli（标准库无解码器）。
- `robots.txt` 用 `urllib.robotparser` 解析，按 UA 判断 `can_fetch` 与 `crawl-delay`；404/不可达视为无限制并在 `warnings` 记录。渲染类动作也会先过 robots 关卡。
- 默认 UA 是浏览器字符串 + `web-capture/1.0` 后缀，可用 `--ua` 覆盖；不要伪装成搜索引擎爬虫。
- `meta.json` 只保留 `content-type` / `content-length` / `etag` 等安全头，Cookie 与 Authorization 一律不落盘。
- **输出重名自动避让**：`-o` 目录里已有 `manifest.json` 时，`unique_outdir()` 自动改用 `<目录>-2`、`-3`（批量/爬取/对比同样处理），不覆盖历史产物。stdout 的 `output` 与 manifest 里的路径才是实际落盘位置；`warnings` 会写明避让。要覆盖请换新目录或自行删除旧目录。

## 常见失败

| 现象 | 处理 |
|---|---|
| `robots.txt 不允许抓取该地址` | 确认有权后加 `--no-robots`；不要偷偷绕过 |
| `请求失败: ... Name or service not known` | 检查网址与网络；大陆网络对部分海外站点不可达，可改用本地 HTML 文件 |
| `未找到 Edge/Chrome 浏览器` | 设 `WEB_CAPTURE_BROWSER` 或 `--browser` 指向 msedge.exe / chrome.exe |
| `CDP 整页渲染不可用，已降级` | 看 `capture.json` 的原因；企业策略常禁用调试端口，CLI 视口截图仍可用 |
| 中文乱码 | 看 `meta.json.encoding`；若站点声明错误，可用 `--extra --ua` 换 UA 或直接存本地文件 |
| Markdown 只剩导航 | `--extra --all` 输出整页，或改用 `web-extract --kind links` 自己挑内容 |
| 单文件存档里图片还是外链 | 看 `resources.json` 的 `failed`；跨域资源被拒或超过 `--max-asset-bytes`（默认 3MB）时保留原链接 |
| 爬取页数远少于预期 | 站点用 JS 生成链接、需要登录，或 robots 限制；`web-fetch` 看原始 HTML 确认 |

## 退出码

| 码 | 含义 |
|---|---|
| 0 | 成功（可能带 `warnings`） |
| 1 | 参数错 / 网络失败 / 依赖缺失 / 动作异常 |
| 2 | `bootstrap.py check` 依赖缺失；`web-diff --strict` 检测到变化；`actions.py run` 原样透传 |
| 130 | 用户中断 |

## 安全与隐私

- 所有请求只发往用户给出的网址及其页面资源；不向第三方上传抓取结果。
- 不执行网页里的 JavaScript（CDP 渲染例外：浏览器会在沙箱内执行目标页面脚本，这是渲染的必要代价）。
- 单文件存档会把远程资源内联进 HTML，打开该 HTML 时其中的脚本可能运行；来源不明的页面请谨慎打开。
