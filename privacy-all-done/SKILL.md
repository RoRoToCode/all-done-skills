---
name: "privacy-all-done"
display_name: "隐私全搞定"
display_name_en: "Privacy, All Done"
description: "Local privacy and barcode toolkit - scan text for phone numbers, ID cards, emails, bank cards, IPs and similar patterns, redact with masks or placeholders, batch-process directories, render reports, list or load custom rules, read and strip metadata from JPEG/PNG/OOXML/PDF, generate and read QR codes, and draw Code128 barcodes. Triggers include 隐私全搞定 / 隐私工具箱 / /pv / 敏感信息扫描 / 手机号脱敏 / 身份证脱敏 / 清除 EXIF / 元数据清理 / 二维码生成 / 二维码识别 / 条形码. Fully local, nothing uploaded, no per-step confirmation by default."
description_zh: "本机隐私与条码工具箱：敏感信息扫描（手机号/身份证/邮箱/银行卡/IP 等，带校验位）· 掩码脱敏 · 目录批量 · 扫描报告 · 规则集管理 · JPEG/PNG/OOXML/PDF 元数据读取与清理 · 二维码生成识别 · 纯标准库 Code128 条形码。说「隐私全搞定」或输入 /pv 即用，全程本地不上传，默认无需逐项确认（输出另存、不覆盖原文件）。"
description_en: "Local privacy and barcode toolkit - scan/redact sensitive data (CN phone, ID card, email, bank card, IP), batch scan, reports, custom rules, read/strip JPEG/PNG/OOXML/PDF metadata, QR code make/read and Code128 barcode SVG. Triggers: 隐私全搞定 / /pv / redact / remove EXIF / qr code. Fully local, nothing uploaded, no per-step confirmation by default."
version: "1.4.1"
agent_created: true
---

# 隐私全搞定

本机隐私与条码处理技能。10 项动作统一从 `python scripts/actions.py` 调用，动作清单的唯一数据源是 `assets/actions.json`。扫描、脱敏、元数据读取与清理、Code128 条形码**只用 Python 标准库**；二维码生成/识别分别需要可选的 `qrcode` 与 `pyzbar`（或 `opencv-python`），缺失时如实给出本地安装指引，不伪装成功。

## 统一入口

```bash
python scripts/actions.py list                  # 全部动作
python scripts/actions.py list --json           # 机器可读清单
python scripts/actions.py describe <id>         # 参数、依赖、备注
python scripts/actions.py check                 # 解释器 + 依赖状态
python scripts/actions.py run <id> --input <in> --output <out>
python scripts/actions.py online <id>           # 在线替代（本技能一律返回「无」）
```

`run` 把其余参数原样透传给 `scripts/<id 下划线>.py`；也可直接调用单个脚本。
精细参数见 `references/recipes.md`；格式矩阵、退出码、依赖与排错见
`references/toolchain.md`。动作清单的唯一数据源是 `assets/actions.json`。

## 动作 id

- 扫描与脱敏：`pv-scan` `pv-redact` `pv-batch` `pv-report` `pv-rules`
- 元数据与条码：`pv-metadata` `pv-clean` `pv-barcode` `pv-qr-make` `pv-qr-read`

## 默认无需逐项确认

本技能**默认无需逐项确认**：不对每个文件、每一步操作弹确认，直接执行到出结果。

- 输出命名、重名避让（` (2)` / `-2`）、可选依赖降级、批量单份失败不中断，全部自动决策。
- 依赖缺失不询问、不联网：只给一条本地安装指引，不伪装成功。
- **唯一不放行的是安全底线**：输出不得覆盖输入、不删除或移动用户原文件、不执行任意命令、不上传任何云端或第三方服务器。
- 预览类动作（`--dry-run` / 默认预览）在不落盘的前提下给出完整计划，落盘需显式 `--apply` 或 `-o`。

## 约束

- 全程本地处理，原始文件与扫描结果不上传任何云端或第三方服务，**不提供在线兜底**（`online` 全为 null）。
- 脱敏产物一律另存新文件，输出不得覆盖输入（退出码 3）；产物重名自动加 `-2`/`-3`；原文件只读。
- 内置规则含基础校验（身份证校验位、银行卡 Luhn、手机号号段），但**不保证零误报**；`pv-report` 只汇总，不做合规性结论。
- 二维码动作缺可选依赖时返回退出码 2 并给一条本地安装指引，**不联网安装、不伪造结果**；`pv-qr-read` 需要系统 zbar 动态库或 opencv。
- `pv-clean` 对 PDF 采用保守的字符串级清理，生成新副本；无法安全改写的格式会在报告里标 `skipped` 并说明原因。
- 批量动作单份失败不中断整批，末尾汇总 `failed`；扫描结果默认不含命中内容的完整明文（`--context` 才附带少量上下文）。

## 路由边界

- 本技能只做**本地敏感信息发现与脱敏、元数据清理、条码生成识别**，不做加密、不做访问控制、不评估合规义务。
- **PDF 真删除文字**走 `pdf-workshop` 的 `pdf-redact`；**图片 EXIF 的查看与清除**也可用 `image-all-done` 的 `img-metadata`；**纯文本批量替换**走 `text-all-done`；**压缩包内文件**先走 `archive-all-done` 解压。
- 密码学加密、文件粉碎、水印取证、人脸识别与云端 DLP 不在范围内；需要跨技能串流程用 `pipeline-all-done`。

## 交付

给出产物路径与关键数字（扫描文件数、命中类型与条数、脱敏处数、清理项数、跳过项），缺依赖时附一条本地安装指引，不输出功能清单或操作说明。

## 免责声明
- **本地优先**：本技能全程在本机运行，原始文件不会上传任何云端或第三方服务器；本技能不提供第三方在线替代方案，缺依赖时只给出本地安装指引。
- **结果仅供参考**：正则扫描只覆盖已知模式，会有漏报与误报（例如普通数字串被判为证件号）；脱敏不可逆，掩码规则可能改变文本长度；元数据清理对 PDF 只处理常见的文档信息键，不保证清除所有隐藏层、注释、修订记录或嵌入对象，也不处理加密/DRM 文件。涉及合规交付请人工复核并保留原件。
- **依赖与第三方组件**：扫描、脱敏、元数据与条形码基于 Python 标准库；二维码生成可选 qrcode，识别可选 pyzbar 或 opencv-python（zbar 动态库另需系统安装）。相关组件的下载、许可与版权归各自作者所有，由使用者自行获取并合规使用。第三方组件均由使用者自行安装并各自适用其独立许可，本技能不分发其二进制、库或模型权重；完整清单与许可提示见 THIRD-PARTY.md。
- **按现状提供**：本技能以 MIT 许可按「现状」提供，不提供任何明示或暗示的担保（含适用性、准确性、无中断、无损害）。因使用本技能产生的任何直接或间接损失，由使用者自行承担；处理前请自行备份原始文件。
