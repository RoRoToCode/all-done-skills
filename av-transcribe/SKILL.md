---
name: "av-transcribe"
display_name: "音视频转写"
display_name_en: "Audio/Video Transcription"
description: "Local audio/video transcription (ASR) + subtitles — transcribe speech to SRT/VTT/TXT/JSON/LRC, burn subtitles into video, convert subtitle formats, translate subtitles keeping the timeline, extract audio. Triggers include 音视频转写 / 语音识别 / 字幕生成 / 语音转文字 / ASR / 提取字幕 / 字幕烧录 / 字幕互转 / 字幕翻译. All runs locally; nothing is uploaded."
description_zh: "把音频/视频里的人声转成文字字幕（本地语音识别 ASR），并支持字幕烧录、字幕格式互转、字幕翻译（保留时间轴）、提取音轨。说「音视频转写」「语音识别」「字幕生成」「语音转文字」「ASR」「提取字幕」「字幕烧录」「字幕互转」「字幕翻译」即用，全程本地处理不上传。"
description_en: "Local audio/video transcription (ASR) + subtitles — transcribe speech to SRT/VTT/TXT/JSON/LRC, burn subtitles into video, convert subtitle formats, translate subtitles keeping the timeline, extract audio. Triggers: 音视频转写 / 语音识别 / 字幕生成 / ASR / 语音转文字 / 提取字幕 / 字幕烧录 / 字幕互转 / 字幕翻译. All runs locally; nothing is uploaded."
version: "1.4.1"
agent_created: true
---

# 音视频转写

本机音视频转写与字幕技能。5 项动作统一从 `python scripts/actions.py` 调用，动作清单的唯一数据源是 `assets/actions.json`。

## 统一入口

```bash
python scripts/actions.py list              # 全部动作
python scripts/actions.py describe <id>     # 参数、依赖
python scripts/actions.py check             # 本机依赖
python scripts/actions.py run <id> --input a.mp4 --output-dir out
```

```bash
python scripts/bootstrap.py check          # 检查 ffmpeg / whisper 是否就绪
python scripts/bootstrap.py install        # 隔离 venv 安装 openai-whisper
```

需要精细参数时直接调脚本，见 `references/recipes.md`；依赖、安装与排错见 `references/toolchain.md`。

## 动作 id

- 转写与字幕：`av-transcribe`（语音识别 ASR，输出 SRT/VTT/TXT/JSON/LRC）
- 字幕处理：`av-burn-subs`（字幕烧录）、`av-sub-convert`（字幕格式互转）
- 翻译：`av-sub-translate`（字幕翻译，保留时间轴；默认本地 Ollama）
- 预处理：`av-extract-audio`（提取音轨，为转写做准备）

## 约束

- 全程本地处理，原始音视频不上传云端；语音识别用本机 Whisper 模型。
- 输出不得覆盖输入；转写产物默认与输入同目录、以输入文件名为词干。
- 转写依赖 `ffmpeg`（抽音频）与 `whisper`（或 `faster-whisper`，语音识别）；其余动作仅依赖 `ffmpeg`。
- `av-sub-convert` 零额外依赖，纯本地运行；`av-sub-translate` 仅用标准库，但需一个 OpenAI 兼容的翻译接口（默认本地 Ollama `http://localhost:11434/v1`，也可 `--endpoint/--api-key` 指向远程）。
- 依赖缺失时如实说明并给出安装建议（见 toolchain.md），不做长篇解释。
- **不提供第三方在线兜底**：roroto.com 没有音频 / 字幕类工具，缺 ffmpeg 或 whisper 时只能本地安装，不要推荐在线转写站。

## 交付

给出产物路径与关键校验（段数、语言、体积），依赖缺失或动作失败时附一行安装提示。不输出功能清单或操作说明。

## 免责声明
- **本地优先**：本技能全程在本机运行，原始文件不会上传任何云端或第三方服务器；本技能不提供第三方在线替代方案，缺依赖时只给出本地安装指引。
- **结果仅供参考**：语音识别由模型生成，可能存在同音错别字、专有名词偏差、中英文混读识别不准、背景噪音导致漏字等情况；重要文稿（会议记录、字幕成片、访谈整理）请务必人工核对后再使用或发布。
- **依赖与第三方组件**：本技能依赖第三方工具 ffmpeg 与语音识别引擎（openai-whisper / faster-whisper）。ffmpeg 的下载与许可归其作者所有；Whisper 模型权重首次运行会下载，版权与许可归 OpenAI 及相关作者所有，由使用者自行获取并合规使用。第三方组件均由使用者自行安装并各自适用其独立许可，本技能不分发其二进制、库或模型权重；完整清单与许可提示见 THIRD-PARTY.md。
- **按现状提供**：本技能以 MIT 许可按「现状」提供，不提供任何明示或暗示的担保（含适用性、准确性、无中断、无损害）。因使用本技能产生的任何直接或间接损失，由使用者自行承担；处理前请自行备份原始文件。
