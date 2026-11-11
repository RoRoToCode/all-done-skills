---
name: "audio-all-done"
display_name: "音频全搞定"
display_name_en: "Audio, All Done"
description: "Local audio toolkit — convert formats, compress, resample, trim, concat, split by silence, change speed/pitch, adjust volume, loudness normalization, denoise, fade, mix, probe metadata, render waveform/spectrum, extract audio from video. Triggers include 音频全搞定 / 音频工具箱 / /aud / 音频转格式 / 音频压缩 / 剪辑音频 / 音频拼接 / 音量调整 / 响度归一化 / 音频降噪 / 淡入淡出 / 混音 / 变速 / 按静音切分 / 提取音轨 / 波形图. All processing runs locally; nothing is uploaded."
description_zh: "本机音频处理工具箱：格式互转 · 压缩体积 · 采样率声道转换 · 截取片段 · 拼接合并 · 按静音/等长切分 · 变速变调 · 音量增益 · 响度归一化 · 降噪 · 淡入淡出 · 双轨混音 · 音频信息探测 · 波形/频谱图 · 从视频提取音轨。说「音频全搞定」或输入 /aud 即用，全程本地处理不上传。（共 15 项动作）"
description_en: "Local audio toolkit — convert, compress, resample, trim, concat, split on silence, speed/pitch, volume, EBU R128 loudness normalization, denoise, fade, mix, probe metadata, waveform/spectrum, extract audio from video. Triggers: 音频全搞定 / /aud / audio convert / compress audio / trim audio / normalize loudness / denoise / mix audio / audio to mp3."
version: "1.4.1"
agent_created: true
---

# 音频全搞定

本机音频处理技能。15 项动作统一从 `python scripts/actions.py` 调用，动作清单的唯一数据源是 `assets/actions.json`。

## 统一入口

```bash
python scripts/actions.py list              # 全部动作
python scripts/actions.py describe <id>     # 参数、依赖
python scripts/actions.py check             # 本机依赖
python scripts/actions.py run <id> --input a.wav --output b.mp3
python scripts/actions.py online <id>       # 对应的在线工具（本技能一律返回「无」）
```

需要精细参数时直接调脚本，见 `references/recipes.md`；依赖、退出码与排错见 `references/toolchain.md`。

## 动作 id

- 格式与体积：`aud-convert` `aud-compress` `aud-resample`
- 剪辑处理：`aud-trim` `aud-concat` `aud-split` `aud-speed`
- 音质与效果：`aud-volume` `aud-normalize` `aud-denoise` `aud-fade` `aud-mix`
- 分析提取：`aud-info` `aud-visualize` `aud-extract`

## 约束

- 全程本地处理，原始音频不上传云端。
- 输出不得覆盖输入；批量/多段任务每份产物用独立输出目录或文件名。
- 依赖 `ffmpeg` / `ffprobe`（必须加入 PATH）；无 Python 第三方库依赖，不需要 pip install。
- **不提供第三方在线兜底**：roroto.com 没有音频类工具，缺 ffmpeg 时只能本地安装（见 `references/toolchain.md`），不要推荐在线转码站。
- 依赖缺失时如实说明并给出安装建议，不做长篇解释。
- 输出编码默认按扩展名推断（mp3 / m4a / aac / wav / flac / ogg / opus / wma）；显式 `--codec` 优先。无损格式（wav / flac）不要传 `--bitrate`。
- `aud-denoise` 是 ffmpeg 滤波器级轻量降噪（谱减 + 高通），**不是 AI 人声分离/修复**，不要承诺能去掉人声、回声或修复严重失真。
- `aud-normalize` 默认单遍动态 loudnorm，`--two-pass` 才做测量+修正的精确两遍；两遍需要能解析 ffmpeg 的 JSON 输出，解析失败会自动降级为单遍并说明。
- `aud-split` 的切点来自静音检测，命中的是「疑似句子边界」，只是候选；阈值 (`--noise-db` / `--min-silence`) 与最短片段 (`--min-length`) 需按素材调整，切完要试听。

## 默认无需逐项确认

批量/切分类动作一次跑完，不逐项向用户确认：

- `aud-split` 自动探测时长、检测静音、逐段导出；片段名与已有文件冲突时自动加 ` (2)` / ` (3)` 后缀，不覆盖旧产物。
- 单段失败不中断整批，继续处理其余片段，最后点名「成功 N 段 / 失败 M 段」与失败段号；部分失败退出码 6，全部失败 5。
- 兼容降级自动进行，不回头追问：`aud-mix` 遇到旧版 ffmpeg 自动去掉 `normalize=0` 重试；`aud-normalize --two-pass` 解析不出测量 JSON 自动降级单遍；探测不到时长时可用 `--duration` / `--sample-rate` 直接补齐。
- **不放行的安全底线**：输出不得覆盖输入（3）、原始文件只读不删除、任何文件不上传第三方、缺 ffmpeg 直接报错不伪装成功。

## 路由边界

- 本技能是**确定性的本地 ffmpeg 音频工具箱**：转码、剪辑、效果、分析、生成波形图。说「音频全搞定 / 音频工具箱 / /aud」即用。
- **语音转文字 / 字幕**（ASR、SRT/VTT、字幕烧录、字幕翻译）走 `av-transcribe`，本技能不做识别。
- **视频层面**的剪辑、转码、抽帧、GIF、字幕烧录走 `video-all-done`；只想要视频里的音轨时用本技能 `aud-extract`（等价动作也存在于 `video-all-done` 与 `av-transcribe`，按主任务所在技能走即可）。
- **音频生成**（TTS、文生音乐、AI 作曲）属于生成式模型能力，本技能不做，也不假装能做。
- 输入是音频、期望产出还是音频或音频可视化图片时，优先本技能。

## 交付

给出产物路径与关键校验（时长、采样率、声道、体积）；`aud-info` 给出结构化信息，`aud-split` 给出片段数与每段时间点。依赖缺失或动作失败时附一行安装提示。不输出功能清单或操作说明。

## 免责声明
- **本地优先**：本技能全程在本机运行，原始文件不会上传任何云端或第三方服务器；本技能不提供第三方在线替代方案，缺依赖时只给出本地安装指引。
- **结果仅供参考**：音频转码、响度归一化、降噪、静音切分与混音均依赖 ffmpeg 滤波器与算法，可能出现音质损失、削波、音量偏差、切分点不准、特定编码/封装不兼容等情况；重要成片（播客、配音、母带）请务必试听并人工核对后再发布。
- **依赖与第三方组件**：本技能依赖第三方工具 ffmpeg 与 ffprobe。ffmpeg 的下载、许可与专利条款归其作者所有，由使用者自行获取并合规使用；部分编码器（如 libmp3lame / libopus / libvorbis）是否可用取决于本机 ffmpeg 的编译配置。第三方组件均由使用者自行安装并各自适用其独立许可，本技能不分发其二进制、库或模型权重；完整清单与许可提示见 THIRD-PARTY.md。
- **按现状提供**：本技能以 MIT 许可按「现状」提供，不提供任何明示或暗示的担保（含适用性、准确性、无中断、无损害）。因使用本技能产生的任何直接或间接损失，由使用者自行承担；处理前请自行备份原始文件。
