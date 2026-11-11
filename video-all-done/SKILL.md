---
name: "video-all-done"
display_name: "视频全搞定"
display_name_en: "Videos, All Done"
description: "Local video toolkit — format convert, compress, trim, concat, resize, rotate, watermark, extract audio, extract frames, GIF, burn subtitles, plus AI-free generation (slideshow from images+audio, text-card video). Triggers include 视频全搞定 / 视频工具箱 / /vid / 视频转格式 / 视频压缩 / 剪辑视频 / 视频拼接 / 视频加水印 / 视频转 GIF / 字幕烧录 / 图片生成视频 / 文字生成视频 / 视频旋转. All processing runs locally; nothing is uploaded."
description_zh: "本机视频处理工具箱：格式转换 · 压缩 · 截取片段 · 拼接合并 · 改分辨率 · 旋转翻转 · 水印 · 提取音频 · 提取帧 · 转 GIF · 字幕烧录；另含无模型生成——图片+音乐做幻灯片视频、文字卡片生成视频。说「视频全搞定」或输入 /vid 即用，全程本地处理不上传。（共 13 项动作）"
description_en: "Local video toolkit — convert, compress, trim, concat, resize, rotate, watermark, extract audio/frames, GIF, burn subtitles; plus model-free generation (image+audio slideshow, text-card video). Triggers: 视频全搞定 / /vid / video convert / compress / trim / concat / watermark / video to gif / burn subtitles / image to video / text to video / rotate video."
version: "1.4.1"
agent_created: true
---

# 视频全搞定

本机视频处理技能。13 项动作统一从 `python scripts/actions.py` 调用，动作清单的唯一数据源是 `assets/actions.json`。

## 统一入口

```bash
python scripts/actions.py list              # 全部动作
python scripts/actions.py describe <id>     # 参数、依赖
python scripts/actions.py check             # 本机依赖
python scripts/actions.py run <id> --input a.mp4 --output out.mp4
```

需要精细参数时直接调脚本，见 `references/recipes.md`；依赖、退出码与排错见 `references/toolchain.md`。

## 动作 id

- 格式与体积：`vid-convert` `vid-compress`
- 剪辑处理：`vid-trim` `vid-concat` `vid-resize` `vid-rotate`
- 叠加与提取：`vid-watermark` `vid-extract-audio` `vid-extract-frames` `vid-gif` `vid-subs`
- 生成（无模型，纯本地）：`vid-slideshow` `vid-textcard`

## 约束

- 全程本地处理，原始视频不上传云端。
- 输出不得覆盖输入；批量/多段任务每份产物用独立输出名。
- 依赖 `ffmpeg` / `ffprobe`（必须加入 PATH）；水印文字、幻灯片、文字卡片另需 `Pillow`。
- **不提供第三方在线兜底**：roroto.com 没有视频类工具，缺 ffmpeg 时只能本地安装（见 `references/toolchain.md`），不要推荐在线转码站。
- 依赖缺失时如实说明并给出安装建议（见 toolchain.md），不做长篇解释。
- 旋转/翻转等会改变编码的参数在 Windows 下也可能触发重编码；以实际产物为准，必要时 `--reencode`。

## 路由边界

- 本技能是**确定性的本地 ffmpeg 工具箱**：剪辑、转码、抽帧、字幕、本地合成生成。说「视频全搞定 / 视频工具箱 / /vid」即用。
- **不在本技能范围**：真正的 AI 文生视频 / 图生视频（如 Sora、可灵、Runway 类模型生成），那类属于生成式模型能力，本技能不做，也不假装能做。本技能的「生成」指图片/文字 → 视频的本地合成。
- 需要**单帧图片**的处理（抠图、放大、格式转换、OCR）走内置 `image-all-done`；需要**文档**的生成/编辑/OCR 走内置 `pdf-workshop`；本技能只在视频（连续帧）层面工作。
- 输入是视频、期望产出还是视频或可播放片段时，优先本技能；若只是想「读」一段视频里讲了什么，先做抽帧再用多模态理解，不必盲目转码。

## 交付

给出产物路径与关键校验（时长、分辨率、体积），依赖缺失或动作失败时附一行安装提示。不输出功能清单或操作说明。

## 免责声明
- **本地优先**：本技能全程在本机运行，原始文件不会上传任何云端或第三方服务器；本技能不提供第三方在线替代方案，缺依赖时只给出本地安装指引。
- **结果仅供参考**：视频转码、抽帧、字幕烧录、缩放等均依赖 ffmpeg 与算法，可能出现画质损失、音画不同步、特定编码/封装不兼容等情况；重要成片请务必人工核对后再发布。
- **依赖与第三方组件**：本技能依赖第三方工具 ffmpeg（及其组件）与 Pillow。ffmpeg 的下载、许可与专利条款归其作者所有，由使用者自行获取并合规使用；相关字体版权亦由使用者自行负责。第三方组件均由使用者自行安装并各自适用其独立许可，本技能不分发其二进制、库或模型权重；完整清单与许可提示见 THIRD-PARTY.md。
- **按现状提供**：本技能以 MIT 许可按「现状」提供，不提供任何明示或暗示的担保（含适用性、准确性、无中断、无损害）。因使用本技能产生的任何直接或间接损失，由使用者自行承担；处理前请自行备份原始文件。
