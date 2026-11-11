---
name: "archive-all-done"
display_name: "压缩包全搞定"
display_name_en: "Archives, All Done"
description: "Local archive toolkit — create, extract, list, verify, add/remove entries, convert between zip/tar/tar.gz/tar.bz2/tar.xz/gz/bz2/xz, password-protect, split volumes, merge, batch, inspect stats. Triggers include 压缩包全搞定 / 压缩工具箱 / /arc / 解压 / 压缩文件 / 打包 / 分卷压缩 / 加密压缩 / 合并压缩包 / 压缩包转格式 / 查看压缩包 / 校验压缩包 / 批量解压. Runs fully local on Python stdlib with no upload; no per-step confirmation by default."
description_zh: "本机压缩包工具箱：创建 · 解压 · 看清单 · 完整性校验 · 追加/删除条目 · zip 与 tar 系列格式互转 · 加密压缩/带密码解压 · 分卷压缩 · 合并分卷 · 批量压缩解压 · 包信息统计。说「压缩包全搞定」或输入 /arc 即用。纯 Python 标准库可跑通全部 13 项动作，全程本地不上传，默认无需逐项确认。"
description_en: "Local archive toolkit — create, extract, list, test, add/remove entries, convert zip/tar/tgz/tbz2/txz/gz/bz2/xz, encrypt/decrypt, split/merge volumes, batch, inspect. Triggers: 压缩包全搞定 / /arc / unzip / zip files / split archive / password zip / batch extract. Pure stdlib, fully local, no per-step confirmation by default."
version: "1.4.1"
agent_created: true
---

# 压缩包全搞定

本机压缩包处理技能。13 项动作统一从 `python scripts/actions.py` 调用，动作清单的唯一数据源是 `assets/actions.json`。核心读写全部基于 Python 标准库（`zipfile` / `tarfile` / `gzip` / `bz2` / `lzma`），**开箱即用、不需要装任何东西**；`pyzipper`（AES-256）、`py7zr`（7z）、`rarfile`（rar 只读）是可选项，缺失时自动降级并如实说明。

## 统一入口

```bash
python scripts/actions.py list                  # 全部动作
python scripts/actions.py list --json           # 机器可读清单
python scripts/actions.py describe <id>         # 参数、依赖、备注
python scripts/actions.py check                 # 本机依赖
python scripts/actions.py run <id> --input a.zip --output out/
python scripts/actions.py run arc-create --inputs a.txt img/ --output out.tar.gz
```

`run` 把其余参数原样透传给 `scripts/<id 下划线>.py`；也可直接 `python scripts/arc_create.py ...`。精细参数见 `references/recipes.md`；格式矩阵、退出码、降级与排错见 `references/toolchain.md`。

## 动作 id

- 打包与解包：`arc-create` `arc-extract`
- 查看与校验：`arc-list` `arc-test` `arc-info`
- 包内编辑：`arc-add` `arc-remove` `arc-convert`
- 加密：`arc-encrypt` `arc-decrypt`
- 批量：`arc-split` `arc-merge` `arc-batch`

## 默认无需逐项确认

本技能**默认无需逐项确认**：不对每个文件、每一步操作弹确认，直接执行到出结果。

- 批量、分卷命名、临时目录、重名处理、可选依赖降级全部自动决策；单份失败不中断整批，末尾统一汇总。
- 输出路径已存在时默认自动改名 ` (2)`，用 `--on-conflict overwrite|skip` 改策略。
- 依赖缺失不询问、不联网：能用标准库就用标准库，确实做不了（如写 7z / rar）才报一条安装提示。
- **唯一不放行的是安全底线**：绝对路径、盘符、`..` 越界、符号链接/硬链接条目一律拒绝（退出码 7）；输出等于输入、输出覆盖原包一律拒绝（退出码 3）。原包始终只读，所有写操作都产出新文件或新目录。
- 处理前不要求用户逐个确认，但**不主动删除任何用户文件**；需要清理时只清理本技能自己创建的临时目录。

## 约束

- 全程本地处理，压缩包与其中文件不上传任何云端或第三方服务，**不提供在线兜底**（`online` 全为 null）。
- 加密：`arc-encrypt` 在装了 `pyzipper` 时自动用 AES-256；否则用标准库实现的传统 ZipCrypto，属**弱加密、仅防误看**，必须在交付里如实说明，不得宣称"高强度加密"。
- 密码只在进程内存里使用，不写入日志、不回显、不落盘。
- 7z / rar：写 rar 不支持（无开源写入器）；7z 读写需 `py7zr`；rar 只读需 `rarfile` + unrar。缺失时如实说明，不伪装成功。
- `gz` / `bz2` / `xz` 是单文件压缩，不是归档格式；多文件必须走 zip 或 tar 系列。

## 路由边界

- 本技能只处理**压缩归档容器**的创建、解包、变换与检查。
- 需要 PDF / 图片 / 视频 / Office 文档内部的处理，交给对应的 `pdf-workshop` / `image-all-done` / `video-all-done` / `office-all-done`；本技能不解析包内文件的语义。
- 需要「读一份包里的文档讲了什么」时，先 `arc-extract` 到独立目录，再按文件类型走对应技能。

## 交付

给出产物路径与关键校验（条目数、原始/压缩体积、压缩率、加密状态、校验结果），依赖缺失或动作失败时附一行安装提示。不输出功能清单或操作说明。

## 免责声明
- **本地优先**：本技能全程在本机运行，原始文件不会上传任何云端或第三方服务器；本技能不提供第三方在线替代方案，缺依赖时只给出本地安装指引。
- **结果仅供参考**：跨格式转换、加密、分卷合并会丢失部分元信息（如 Unix 权限位、符号链接、精确时间戳、包注释）；加密 zip 在未安装 pyzipper 时使用传统 ZipCrypto 弱加密，仅防误看，不适用于敏感或合规场景。重要归档请务必保留原包并人工核对。
- **依赖与第三方组件**：核心功能基于 Python 标准库；可选增强依赖 pyzipper / py7zr / rarfile（及其外部二进制 unrar），相关组件的下载、许可与版权归各自作者所有，由使用者自行获取并合规使用。密码由使用者自行保管，遗失后本技能无法找回。第三方组件均由使用者自行安装并各自适用其独立许可，本技能不分发其二进制、库或模型权重；完整清单与许可提示见 THIRD-PARTY.md。
- **按现状提供**：本技能以 MIT 许可按「现状」提供，不提供任何明示或暗示的担保（含适用性、准确性、无中断、无损害）。因使用本技能产生的任何直接或间接损失，由使用者自行承担；处理前请自行备份原始文件。
