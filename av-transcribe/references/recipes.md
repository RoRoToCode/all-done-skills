# 音视频转写 · 用法配方

统一入口：所有动作都经 `python scripts/actions.py run <id> -- <参数>`，
也可直接 `python scripts/<id>.py --input x ...`。下文用简写。

前置：`ffmpeg` / `ffprobe` 在 PATH 上；转写另需 `whisper`（见 toolchain.md）。
缺依赖时先用 `python scripts/bootstrap.py check` 查看，再 `python scripts/bootstrap.py install`。

## 转写与字幕

### av-transcribe 音视频转写（语音识别）
```bash
# 最常用：中文视频自动识别，输出 SRT/VTT/TXT/JSON/LRC 到 out 目录
python scripts/av_transcribe.py --input 会议.mp4 --output-dir out --language zh --model small

# 只想要字幕文件（SRT），指定模型
python scripts/av_transcribe.py --input 访谈.wav --output-dir out --model base --format srt

# 英文，用 GPU 加速
python scripts/av_transcribe.py --input talk.mp4 --output-dir out --language en --device cuda
```
- `--model`：`tiny` < `base` < `small` < `medium` < `large`。中文建议 `small` 起。
- `--format`：`all`（默认，出 srt/vtt/txt/json/lrc）/ 或 `srt,vtt,txt,json,lrc,ass` 任选。
- 产物默认与输入同目录、以输入文件名为词干；`--output-dir` 可改到别处。

### av-burn-subs 字幕烧录
```bash
python scripts/av_burn_subs.py --input 视频.mp4 --subtitle out/视频.srt --output 成片.mp4
python scripts/av_burn_subs.py --input a.mp4 --subtitle a.srt --output b.mp4 \
  --font-size 28 --font-color FFFF00 --position bottom
```
- 硬字幕（烧进画面），会重编码视频；`--position bottom|center|top`。

### av-sub-convert 字幕格式互转（零依赖）
```bash
python scripts/av_sub_convert.py --input a.srt --output a.vtt
python scripts/av_sub_convert.py --input a.srt --output a.lrc
python scripts/av_sub_convert.py --input a.srt --output a.ass
python scripts/av_sub_convert.py --input a.vtt --output a.txt
```
- 目标格式由输出扩展名决定，也可 `--to srt|vtt|lrc|txt|ass` 显式指定。

### av-sub-translate 字幕翻译（保留时间轴）
```bash
# 默认对接本地 Ollama；先把模型拉下来并启动服务
#   ollama pull qwen2.5   &&   ollama serve
python scripts/av_sub_translate.py --input a.srt --output a_en.srt --target en

# 中文字幕翻英、输出 VTT；源语言已知时显式指定更稳
python scripts/av_sub_translate.py --input 会议.srt --output 会议_en.vtt --source zh --target en

# 指向远程 OpenAI 兼容服务
python scripts/av_sub_translate.py --input a.srt --output a_ja.srt --target ja \
  --endpoint https://api.example.com/v1 --model gpt-4o-mini --api-key sk-xxx
```
- 时间戳原样沿用，只翻译文本；每批条数用 `--batch-size` 控制。
- 接口需 OpenAI 兼容的 `/chat/completions`；本地 Ollama 无需 `--api-key`。

### av-extract-audio 提取音轨
```bash
python scripts/av_extract_audio.py --input 视频.mp4 --output 音频.mp3
python scripts/av_extract_audio.py --input a.mp4 --output a.wav --sample-rate 16000 --mono
```
- 给转写做预处理时，直接交给 `av_transcribe.py` 也行（它会自动抽 16k 单声道）。
