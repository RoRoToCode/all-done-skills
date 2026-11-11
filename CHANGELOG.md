# 变更记录（中文）

> English: this file is the version history for the 17 All Done skills,
> currently at **v1.4.1**. For an English overview see `README.md`.

遵循 [SemVer 2.0.0](https://semver.org/lang/zh-CN/)。17 个技能共用同一个版本号。

## 1.4.1 — 2026-11-10

1.4.0 的 42 个新动作当时只做了冒烟测试，这一轮把它们全部纳入真跑 + 内容断言，
因此又挖出 6 个只在"真串起来用"时才暴露的问题。

### 修复（流水线：模板给的东西跑不通）

- **模板产物不能直接喂给校验/执行**：`pipe-template` 输出的是 `{"名字": 定义}` 集合，
  而 `pipe-validate` / `pipe-run` 按单个定义解析，照文档"生成模板 → 校验 → 运行"走，
  第二步必然报 `steps 必须是非空数组`。现在单模板自动取出；多模板会明确列出可选名字。
- **内置模板有 3 处参数写错**：`txt-normalize`、`file-list`、`data-convert` 都只接受
  位置参数，模板却传了 `--input`，`scan2md` 与 `tidy2pdf` 一跑就
  `unrecognized arguments: --input`。
- **`{{input}}` 给相对路径必失败**：步骤子进程的 cwd 是 run_dir，用户在当前目录写的
  `--input report.pdf` 到步骤里就找不到了。现在替换变量时把输入折算成绝对路径。

### 修复（隐私：脱敏结果被悄悄改坏）

- **脱敏后凭空多出 BOM**：`read_text()` 用 `utf-8-sig` 探测，无 BOM 的普通 UTF-8 也命中，
  回写时 `encode("utf-8-sig")` 就加了个 BOM。原文件没 BOM，输出却有——
  下游脚本按字节比对会直接错。现在只在源文件真有 BOM 时才沿用该编码。
- **校验位不过的号码被静默吞掉**：随手编的身份证/卡号不会命中，但用户完全看不出
  是"没扫到"还是"被规则排除了"。`pv-scan` 新增 `rejected` 字段，按类型给出排除数。

### 修复（编码：中文错误信息被截成乱码）

- `main_guard()` 只放宽了 `errors` 没改编码，Windows 下被管道捕获时仍按 cp936 写字节，
  父进程按 UTF-8 解码就得到 `��支持的格式`。五个带公共层的新技能统一改为：
  接终端不动编码，被重定向时按 UTF-8 输出。流水线 `pipe-status` 里的失败原因因此可读。

### 修复（提示：镜像建议是错的）

- `img-bgremove` 失败时让用户 `set HF_ENDPOINT=https://hf-mirror.com`，但 rembg 2.x
  的 `u2net` / `bria-rmbg` 都是从 GitHub Release 拉，走 HF 镜像没用。改为说明
  两条真实可行路径（走代理，或手动把 `u2net.onnx` 放进 `~/.u2net/`），并支持
  `U2NET_HOME` 改目录。

### 新增（测试资产）

- `_aud_test/_make_pii.py`：含手机号/身份证/银行卡/邮箱/IP 的隐私样本，
  以及"有命中 / 干净 / GBK 编码"三份文件的批量目录。号码的校验位是真算过的，
  否则会被规则正确排除，看起来像功能坏了。
- `_func_test.py` 补齐 `privacy-all-done`（10）与 `pipeline-all-done`（8）的规格，
  覆盖 157 → 185 个动作。
- `_verify_outputs.py` 新增 16 项断言（脱敏真删字且不加 BOM、干净文件零命中、
  条码 SVG 有码线、二维码能读回原文、流水线第二步真吃到第一步产物等），
  62 → 78 项。

### 本次验证结果

| 范围 | 结果 |
|---|---|
| 17 个技能 / 185 个动作（逐个真跑） | **180 通过**、4 项缺外部程序、1 项需在线凭据 |
| 内容级断言 | **78/78 通过** |
| 口径对齐 | 17 技能 / 44 链接 / 98 处站点字样，问题 0；旧措辞残留 0 |

未通过的 5 项都不是代码问题：`docx-to-pdf` / `xlsx-to-pdf` / `pptx-to-pdf` 缺
LibreOffice，`eb-convert` 缺 Calibre，`av-sub-translate` 需要在线翻译凭据。
另 `av-transcribe`（Whisper 模型）与 `img-bgremove`（176MB 模型）需要从
GitHub/HuggingFace 下载权重，本机网络拉不动，未纳入本轮真跑。

## 1.4.0 — 2026-11-10

### 新增（4 个技能、42 个动作，全部完工）

四个技能补齐家族的三层结构性空白，全部沿用既有技能模式：8 字段 frontmatter（字符串值加引号）、
免责 4 条本地版、`actions.json` 顶层 7 字段、`scripts/actions.py` 统一入口 +
`<前缀>_common.py` 共享层 + 每动作一脚本、`references/recipes.md` 与 `toolchain.md`、
MIT LICENSE 与逐字节一致的 `THIRD-PARTY.md`、`默认无需逐项确认` / 约束 / 路由边界 /
交付四段说明。`online` 全为 null（roroto.com 无对应工具，不臆造在线兜底）。

- `file-all-done`（12 个动作）：目录清单/树、条件查找、批量重命名（默认预览，`--apply`
  才落盘并写 `rename-map.json`）、内容哈希查重（只报告不删除）、sha256 校验与复核、
  按类型/日期归类（只复制）、体积报告、目录比对、元数据、安全批量复制。纯标准库。
- `data-all-done`（12 个动作）：CSV/TSV/JSON/NDJSON/XML/YAML/TOML/Markdown 互转、
  格式校验、Schema 推断、合并、条件筛选（受限表达式，不用 eval）、字段映射、排序去重、
  嵌套扁平化、字段画像、两表比对、拆表。内部统一「记录列表」模型，零必需依赖。
- `pipeline-all-done`（8 个动作）：技能/动作发现、请求路由、4 个内置模板、定义校验、
  执行（每步独立目录 + manifest/state）、断点续跑、状态、MD/HTML/JSON 报告。
  只以参数数组调用各技能 `actions.py run`，不经过 shell、不执行任意命令。
- `privacy-all-done`（10 个动作）：11 条内置规则（手机号 / 身份证校验位 / 银行卡 Luhn /
  邮箱 / IPv4 / MAC / 车牌 / 护照 / QQ / 密钥 / URL 令牌）的扫描与脱敏、目录批量、报告、
  自定义规则、JPEG EXIF / PNG 文本块 / OOXML 属性 / PDF /Info 元数据读取与清理、
  二维码生成识别（可选依赖缺失时 rc=2 + 本地安装指引）、纯标准库 Code128-B 条形码 SVG。

三个此前缺公共模块的技能已补齐 `data_common.py` / `pipe_common.py` / `pv_common.py`，
`release_scope.py` 现判定 **17 个技能全部可发布**。

### 修复（真跑测试发现，145 个动作逐个执行并校验内容）

这一批问题用 `--dry-run` 冒烟测试查不出来——必须真出产物、再校验产物内容才会暴露。

**视频：ffmpeg 7+ 兼容（影响面最大）**

- **水印全部位置失效**：overlay 的 `tw`/`th` 变量在 ffmpeg 7 起已被移除，
  `W-tw-10` 直接报 `Undefined constant`，`vid-watermark` 输出 0 字节。改用 `w`/`h`。
- **三段以上素材的转场从来没成功过**：`xfade` 多段滤镜链之间漏了分号，
  ffmpeg 报 `Trailing garbage after a filter`；`vid-slideshow` / `vid-textcard`
  在 ≥3 张图时必失败。
- **单卡片文字视频报错**：只有一段素材时返回 `"[0:v]"` 当滤镜图，ffmpeg 报
  `No such filter: ''`；改为跳过 `-filter_complex` 并直接映射 `0:v`。
- **字幕烧录不认绝对路径**：`subtitles=F:/a/b.srt` 的盘符冒号被当滤镜参数分隔符，
  报 `Unable to parse "original_size"`。新增 `filter_path()` 统一转义。
- `vid-extract-frames` 的 `--output` 支持直接给目录；`vid-slideshow` 的 `--images`
  支持直接给目录。

**音视频：ffprobe 缺失时不该中断**

- `need_ffprobe()` 原来缺 ffprobe 就 `exit(2)`，使 `aud-split` / `aud-fade` /
  `aud-info` / `aud-compress --target-mb` 在"只有 ffmpeg"的机器上完全不可用；
  现在返回 None，由 `probe()` 走 ffmpeg 解析兜底。
- 兜底解析的正则此前被写坏（`\s`/`\d` 变成 `//s`/`//d`），时长永远解析成 None；
  已修正，`aud` / `vid` / `av` 三处均返回正确时长。

**压缩包：新版库 API 变更**

- `arc-encrypt` 在 pyzipper 0.4 上崩：`ZipFile.__init__() got an unexpected keyword
  argument 'nbits'`。去掉 `nbits`，`WZ_AES` 本身就是 AES-256。
- `arc-convert` / 7z 读取在 py7zr 1.x 上崩：`readall()` 已被移除，改为解到临时目录再读。
- 读 AES 加密 zip 用标准库报 `That compression method is not supported`；
  有密码且装了 pyzipper 时改用 `AESZipFile`。

**图片**

- `img-bgremove` 兼容 rembg 2.0：`remove()` 不再接受 `model_name` 关键字（报
  `got multiple values`），改为显式 `new_session(model)`；同时避开 2.0 默认的
  1GB `bria-rmbg`，仍用 176MB 的 `u2net`，失败时给出镜像与手动放置模型的指引。

**自检**

- `selftest.py` 新增两项：脚本语法检查、以及"脚本引用的同目录 `*_common.py`
  是否存在"。此前它会把缺公共模块的技能判成"结构 OK"——因为入口 `actions.py`
  不 import 业务模块，`list` 照样能跑。

### 新增（测试资产）

- `_aud_test/_make_fixtures.py`：docx / xlsx / pptx / pdf / 图片 / 音视频 / 文本 /
  压缩包 / EPUB / 目录树全套中文样本。
- `_aud_test/_func_test.py`：157 个动作逐个真跑，按"退出码 + 产物存在且非空"判定。
- `_aud_test/_verify_outputs.py`：62 项内容级断言（脱敏是否真删字、OCR 是否认出字、
  压缩是否变小、编码是否真转换、转场时长是否对得上……）。

### 变更（口径与工程）

- 版本号 **1.3.0 → 1.4.0**：17 个技能的 `SKILL.md` 与 `actions.json` 由 `align_release.py`
  统一；`online_registry.SKILLS` 13 → 17，新增 4 个技能在 `LINKS` 中为空字典。
  三轮对齐（版本 / 免责 / 合规）后旧措辞残留 0、`align_texts.py` 问题 0。
- 修正两处 frontmatter 动作数残留：`pdf-workshop` 的 `Fourteen` → `Twenty-three`、
  `ocr-workshop` 的 `Four actions` → `Five actions`。
- 新增 `release_file.py` / `release_data.py` / `release_pipeline.py` / `release_privacy.py`
  四个独立发布脚本（与 `release_text.py` 同构）；`_gen_specs_a.py` / `_gen_specs_b.py` /
  `_gen_new_skills.py` 为可复跑的规格表与骨架生成器；`README.md` 更新为 17 技能 / 187 动作。

### 本次验证结果

| 范围 | 结果 |
|---|---|
| 14 个可运行技能 / 157 个动作（补齐前的历史结果） | 145 通过、6 项缺外部依赖、1 项需在线凭据 |
| 内容级断言 | 62/62 通过 |
| 4 个新技能 / 42 个动作（收尾复测） | `_new_skills_test/` 13 + 17 + 12 + 16 = **58 项全 PASS** |
| 口径对齐 | `align_texts.py` 17 技能 / 44 链接 / 98 处站点字样，问题 0 |
| 发布一致性 | 17 个单包 + bundle 585.2 KB，校验 0 问题；同步 318 文件，源码↔zip↔安装副本 0 差异 |
| 六类只读审计 | 结构 0 / 运行态 0 / 网址 0 / YAML 0 / 已安装 0 / 合规 0 |
| 未完工技能 | 无（17 个技能全部可发布） |

6 项缺依赖的动作：`docx-to-pdf` / `xlsx-to-pdf` / `pptx-to-pdf`（需 LibreOffice）、
`eb-convert`（需 Calibre）、`av-transcribe`（需 Whisper）、`img-bgremove`
（需下载 176MB 模型）。

## 1.3.1 — 2026-11-10

（未发布，内容已并入 1.4.0）

## 1.3.0 — 2026-11-09

### 新增

- **`text-all-done`（文本全搞定，新技能，7 个动作）**：编码嗅探与互转、换行/空白规范化、
  按行去重、正则批量替换、两文件 diff、统计与词频、按行/字符/字节切分。纯标准库零依赖。
- **`pdf-workshop` 14 → 23 个动作**：`pdf-compress`（结构无损 + 图片有损）、`pdf-rotate`、
  `pdf-delete-pages`、`pdf-crop`、`pdf-page-number`、`pdf-info`、`pdf-form-list`、
  `pdf-form-fill`、`pdf-redact`（真删除文字，不是画白块）。
- **`ocr-workshop` 4 → 5 个动作**：`ocr-searchable-pdf`，原图不动、只叠不可见文字层，
  实测与原图逐像素一致（0 像素差），可搜索/选中/复制。
- **安装后自检 `selftest.py`**：解压 bundle 即可运行，检查注册表、脚本引用、入口与依赖状态。

### 修复（可用性）

- **依赖自愈**：所有技能的 `check` 先打印当前解释器路径——"包装在 A、技能用 B 解释器跑"
  是此前动作凭空失败的主因。`ffmpeg` 解析顺序改为 `环境变量 → PATH → ~/.workbuddy/bin →
  imageio-ffmpeg`，并在 `ffprobe` 缺失时用 `ffmpeg -i` 解析兜底（时长、分辨率、采样率）。
- `image-all-done` 的 `img-ocr` 改为 **RapidOCR 优先、Tesseract 兜底**，不再要求外部二进制。
- `office-all-done` 缺 soffice 时给出正确的安装提示（此前误报为 pip 安装）。

### 修复（交付与工程）

- 补齐缺失的 `ai-prompt-reader.zip` 与 `archive-all-done.zip`；单包与合集重新生成。
- 去掉 `image-all-done` / `video-all-done` / `av-transcribe` 三个 `actions.py` 的 UTF-8 BOM。
- `ai-prompt-reader` 的 SKILL.md 补动作数声明，13 个技能的声明口径一致。
- 结构审计遇到缺包不再整体崩溃，改为记为问题后继续。
- `sync_installed.py` / `release_all.py` 的技能清单改读 `online_registry`，不再各维护一份。
- 新增 `README.md`、`CHANGELOG.md`；`run_skill_test.py` 重写为通用冒烟测试。

### 变更

- 版本号 1.2.1 → 1.3.0；在线链接 34 → 44 条（新增动作统一指向站点首页，不臆造具体工具页）。

## 1.2.1 — 2026-11-09

- 版本号改为合法 SemVer（`1.0.2.1` → `1.2.1`），`online_registry.py` 增加 SemVer 正则断言。
- 合规修复：LICENSE 版权人统一为 `Copyright (c) 2026 RoRoTo`；13 个技能补 `THIRD-PARTY.md`；
  免责第 3 条统一指向该文件；"全自动放行" 改为中性的"默认无需逐项确认"。
- 修复 `align_compliance.py` / `align_disclaimer.py` 的换行处理（曾产生 `\r\r\n`），
  改为二进制读写，并给 `align_texts.py` 增加 CRCRLF 检测。

## 1.2.0 — 2026-11-09

- 恢复第三方在线网址口径，`online_registry.py` 成为唯一口径源（版本、链接、免责、措辞）。
- 12 个技能统一 frontmatter 8 字段与 `actions.json` 顶层 7 字段。
- 修正 `web-capture` frontmatter 中未加引号导致的 YAML 解析错误（`mapping values are not allowed`）。

## 1.1.0 — 2026-11-08

- 新技能：`ocr-workshop`、`ai-prompt-reader`、`archive-all-done`、`ebook-all-done`、
  `audio-all-done`、`web-capture` 陆续加入；`pdf-workshop` 打通第三条 OCR 通道（RapidOCR）。
- `office-all-done` 补齐缺失的 `xls_to_pdf.py` / `ppt_to_pdf.py`，修复 `ppt_merge`、`doc_merge`、
  `doc_to_md`、`xls_merge` 的多处缺陷。
- `doc-data-extract` 动作 8 → 11，修 `check_dependencies` 的 pip 名/模块名映射问题。

## 1.0.0 — 2026-11-08

- 首批 6 个技能：`pdf-workshop`、`image-all-done`、`video-all-done`、`av-transcribe`、
  `office-all-done`、`doc-data-extract`；统一入口、免责 4 条、MIT 许可、合集打包。
