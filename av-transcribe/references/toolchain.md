# 工具链与环境

## 两层依赖

| 能力 | 依赖 | 是否必需 | 说明 |
|---|---|---|---|
| 抽音频 / 烧字幕 / 提音轨 | `ffmpeg` + `ffprobe` | 必需 | 建议用完整 build（含 libx264），加入 PATH |
| 语音识别（ASR） | `whisper`（openai-whisper）或 `faster-whisper` | 仅 `av-transcribe` 需要 | 本地模型，首次运行下载权重 |
| 字幕格式互转 | 无 | `av-sub-convert` 不需要任何外部依赖 | 纯 Python 解析/生成 |

`ffmpeg` 与 `ffprobe` 通常同包；Windows 下 `scoop install ffmpeg` 或 `choco install ffmpeg`，或从 https://ffmpeg.org 下载后把 `bin` 加入 PATH。

## Whisper 安装（av-transcribe）

```bash
pip install openai-whisper        # 官方实现（推荐）
# 或更快的替代：
pip install faster-whisper
```

- 首次转写会自动下载模型权重（默认存 `~/.cache/whisper`），需联网。
- 模型越大越准越慢：`tiny` < `base` < `small` < `medium` < `large`。中文场景建议 `small` 起步，`base` 仅适合快速预览。
- 默认 `device=cpu`；有 NVIDIA 显卡可加 `--device cuda`（需 CUDA 环境）。

## 字幕翻译后端（av-sub-translate）

`av-sub-translate` 只用 Python 标准库，但需要一个 OpenAI 兼容的 `/chat/completions` 接口：

- **本地 Ollama（默认）**：`ollama serve` 后把模型拉下来，如 `ollama pull qwen2.5`；默认端点 `http://localhost:11434/v1`、模型 `qwen2.5`，无需 `--api-key`，全程不出本机。
- **远程服务**：`--endpoint https://.../v1 --model <名> --api-key <key>`，或设环境变量 `AV_TRANSLATE_ENDPOINT` / `AV_TRANSLATE_MODEL` / `AV_TRANSLATE_API_KEY`。
- 时间戳不重算，只替换文本；批量子句若模型返回条数对不上，会自动逐条重译兜底。

## 动作与退出码

| 码 | 含义 | 处理 |
|---|---|---|
| 0 | 成功 | 继续 |
| 2 | 依赖缺失（ffmpeg / whisper） | 看 stderr 安装提示 |
| 3 | 用法错误 / 输入输出路径问题 | 修参数或路径 |
| 5 | ffmpeg / 识别执行失败 | 检查源文件、字幕编码、磁盘空间 |

## 与其他技能的边界

- 本技能的 `av-burn-subs`（字幕烧录）与「视频全搞定」的 `vid-subs` 能力重合。若你已习惯 `视频全搞定`，可直接用那里的 `vid-subs`；本技能自带一份是为了让「转写→烧录」链路在同一技能内闭环。
- 本技能只做「语音→文字/字幕」与字幕的本地处理；视频剪辑、压缩、转码等走「视频全搞定」，PDF/图片处理走各自的技能。

## 隐私

原始音视频始终在本地处理，转写用的 Whisper 模型也在本机运行，音频不会上传任何云端服务。
