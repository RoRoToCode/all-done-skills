# 工具链与环境

## 依赖分层

| 能力 | 依赖 | 是否必需 |
|---|---|---|
| 15 项核心动作（体检、校验、元数据、目录、正文、封面、拆合、生成、批量） | Python 3.9+ 标准库 `zipfile` / `xml.etree` / `html.parser` | 必需，且已内置 |
| `eb-to-pdf` | 本机 Edge / Chrome（无头打印） | 该动作必需 |
| `eb-convert` | Calibre `ebook-convert` 二进制 | 该动作必需 |
| `eb-cover --generate` | `Pillow` | 仅生成封面需要 |
| `eb-to-pdf` 页数回填 | `pypdf` | 可选，缺了只报体积 |

`python scripts/actions.py check` 会逐个探测并标注「必需 / 可选」。核心动作不联网、不装包、不上传。

## 为什么不用 ebooklib

EPUB 本质是一个 ZIP：`mimetype` + `META-INF/container.xml` + OPF（清单 / 顺序 / 元数据）+ XHTML 章节 + NCX 或 nav 目录。
标准库足以完整读写这个容器，且能精确控制 `mimetype` 必须**第一个条目且为 STORED 不压缩**（ebooklib 等库在部分版本会破坏这一点，导致阅读器拒绝打开）。本技能自己处理 ZIP 与命名空间，因此 EPUB2 / EPUB3、中文路径、非规范 OPF 都能读。

## 安装可选依赖

- **Edge / Chrome**：Windows 10/11 自带 Edge；Linux 可 `sudo apt install chromium`，macOS 装 Chrome。也可用 `EBOOK_BROWSER=/path/to/browser` 指定。
- **Calibre**：到 https://calibre-ebook.com 下载安装；Windows 默认在 `C:\Program Files\Calibre2\ebook-convert.exe`，macOS 在 `/Applications/calibre.app/Contents/MacOS/ebook-convert`。安装后在终端执行一次 `ebook-convert --version` 确认可用。
- **Pillow**：`pip install Pillow`（如本机解释器无网，先征得用户同意再安装）。

本技能**不提供第三方在线替代方案**：缺依赖时只给本地安装指引，不要推荐在线转换站。

## 退出码

| 码 | 含义 | 处理 |
|---|---|---|
| 0 | 成功 | 继续 |
| 2 | 用法错误 / 缺依赖（含浏览器或 ebook-convert） | 看 stderr 的安装提示 |
| 3 | 输入/输出错误（路径不存在、输出=输入、目录冲突） | 检查路径与权限 |
| 4 | 文件格式错误（不是 ZIP / 没有 container.xml / OPF 损坏 / 受 DRM 保护） | 换一本来源合法、未加密的 EPUB |
| 5 | 处理失败（浏览器没出 PDF、Calibre 返回非 0、校验严格模式有 error） | 看 stderr 与产物报告 |

## 默认无需逐项确认与冲突策略

默认 `EBOOK_ON_CONFLICT=rename`：主产物（EPUB / PDF / JSON / 图片）已存在时自动改名 ` (2)`、目录已存在且非空时自动改名 ` (2)`；`overwrite` 直接覆盖，`skip` 跳过并正常退出。策略经统一入口的 `--on-conflict` 或环境变量传给所有 16 个动作，脚本本身不需要逐个加参数。

不放行的只有安全底线：输出等于输入（3）、DRM / 加密书（4）、原始电子书原地改写（一律另存）。处理过程不弹确认、不联网询问、不删用户文件；临时目录只清理技能自己创建的。

## EPUB 读写约定

- 读：`META-INF/container.xml` → `full-path` 找 OPF → OPF 的 `<manifest>`（id→href、media-type、properties）与 `<spine>`（idref 顺序）→ 章节 XHTML；目录优先 `nav.xhtml`（`properties` 含 `nav`），其次 `toc.ncx`。
- 写：`mimetype` 恒为第一条且 `ZIP_STORED`，其余条目 `ZIP_DEFLATED`；改写类动作总是另存新文件，不碰源文件。
- 生成：输出 EPUB3 + `nav.xhtml` + 兼容用 `toc.ncx` + `style.css`；章节为 well-formed XHTML（`html.escape` 转义、标签全闭合），中文用 UTF-8。
- 图片：相对路径按 OPF / 章节文件所在目录用 `posixpath.normpath` 解析；`http(s):` / `data:` / `#锚点` 一律跳过，不当作缺失资源。
- 编码：先 UTF-8（含 BOM），失败回退 GB18030，再回退 Latin-1；老式 TXT 可用 `--encoding` 显式指定。

## 已知边界

- **DRM**：`META-INF/encryption.xml` 存在且含实质加密条目时，`eb-inspect` / `eb-validate` 会报告，所有改写动作直接拒绝；本技能不做解密。
- **固定版式 / EPUB3 媒体叠加**：拆分、合并、生成走「重建式」，会规范化 XHTML，SVG 交错、区域放大、音视频叠加、复杂 CSS 可能不保真；这类书建议只用只读动作（体检 / 目录 / 提取 / 检索）。
- **目录重建**：`--toc` 条目按顺序映射 spine 文档，若原书一个 XHTML 里含多个章节（单文件长篇），请用 `| 文件名.xhtml#锚点` 或先拆分再重建。
- **格式互转**：MOBI / AZW3 / KFX 的读写完全依赖 Calibre，能否转换取决于本机 Calibre 版本与输入是否合法。
- **PDF**：`eb-to-pdf` 是「正文重排」不是像素级还原，分页位置与原 EPUB 阅读器不同；需要精排请改用 Calibre 的 `ebook-convert` 或专业排版工具。
