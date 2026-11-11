# 工具链与环境

## 依赖

| 能力 | 依赖 | 是否必需 |
|---|---|---|
| 全部 15 个动作 | `ffmpeg` + `ffprobe` 二进制 | 必需，加入 PATH |
| Python 第三方库 | 无 | 纯标准库，不需要 pip install |

`ffprobe` 只用于读取时长、采样率与元数据（`aud-info` / `aud-compress --target-mb` / `aud-split` / `aud-fade` / `aud-speed --pitch`）；探测不到时，多数动作会安静降级（结果里少几个字段），需要时长的动作会明确报错并给出 `--duration` / `--sample-rate` 手动指定。

`python scripts/actions.py check` 会报告 `ffmpeg` / `ffprobe` 是否在 PATH 上。缺失时安装：

- Windows：`scoop install ffmpeg` 或 `choco install ffmpeg`；也可到 https://ffmpeg.org 下载，把 `bin` 目录加入 PATH。
- macOS：`brew install ffmpeg`
- Linux（Debian/Ubuntu）：`sudo apt install ffmpeg`

部分编码器（`libmp3lame` / `libopus` / `libvorbis` / `libx264`）与滤镜（`afftdn` / `loudnorm` / `showspectrumpic`）是否可用取决于本机 ffmpeg 的编译配置。官方静态构建一般齐全；缺哪个就在动作失败信息里点名，可换 `--codec` 或换输出格式。

## 退出码

| 码 | 含义 | 处理 |
|---|---|---|
| 0 | 成功 | 继续 |
| 2 | 用法错误 / 缺参数 / 参数越界 | 修参数 |
| 3 | 输入/输出错误（路径不存在、输出=输入、无可用片段） | 检查路径、目录、权限 |
| 5 | ffmpeg/ffprobe 返回非 0，或信息解析失败 | 看 stderr，换参数或格式 |
| 6 | 批量部分失败（`aud-split` 有片段成功、有片段失败） | 看失败段号，调整阈值后只重跑失败段 |

## 编码器与格式速查

| 扩展名 | 默认编码器 | 码率参数 |
|---|---|---|
| `.mp3` | `libmp3lame` | `-b:a` |
| `.m4a` / `.aac` / `.mp4` | `aac` | `-b:a` |
| `.ogg` / `.oga` | `libvorbis` | `-b:a` 或 `-q:a`（`--quality`） |
| `.opus` | `libopus` | `-b:a` |
| `.wma` | `wmav2` | `-b:a` |
| `.wav` | `pcm_s16le` | 不传码率；`--bit-depth 24/32/float` 可换 |
| `.aiff` | `pcm_s16be` | 同上 |
| `.flac` | `flac` | 不传码率 |

`audio_encode_args()` 是唯一推断入口，所有动作共用：按输出扩展名选编码器，**无损格式不传 `-b:a`**（否则 ffmpeg 报错），`--codec` 显式指定优先。

## 常用滤镜速查

```
aud-convert   : -map 0:a:0 -c:a <按扩展名> [-ar N] [-ac N]
aud-compress  : -b:a <kbit>；--target-mb 用 ffprobe 取时长算 目标*8*0.95/dur
aud-resample  : -ar 16000 -ac 1；WAV 位深 → pcm_s24le / pcm_f32le
aud-trim      : -ss 起点 [-t 时长]；--copy 用 -c copy，--accurate 把 -ss 放到 -i 后
aud-concat    : concat demuxer，-c copy；编码不一致加 --reencode
aud-split     : silencedetect=noise=-35dB:d=0.4 解析 stderr → 静音中点作切点
aud-speed     : atempo=0.5~2.0 串联；变调 = asetrate=sr*2^(n/12),aresample=sr,atempo=speed/ratio
aud-volume    : volume=+6dB 或 volume=1.5；--limiter 追加 alimiter=limit=1
aud-normalize : loudnorm=I=-16:TP=-1.5:LRA=11:linear=true；--two-pass 先测 measured_* 再修正
aud-denoise   : highpass=f=80,afftdn=nf=-35[,lowpass=f=N]
aud-fade      : afade=t=in:st=0:d=X,afade=t=out:st=dur-Y:d=Y
aud-mix       : [0:a]volume=V0[a0];[1:a]volume=V1[a1];[a0][a1]amix=inputs=2:duration=first:normalize=0
aud-info      : ffprobe -show_format -show_streams -of json
aud-visualize : showwavespic / showspectrumpic + -frames:v 1
aud-extract   : -map 0:a:0 [-c copy 或 -c:a ...]
```

## 已知坑

- **MP3 流拷贝**：`--copy` 在 MP3 上会有毫秒级到数十毫秒的边界偏移（帧粒度）。要精准用默认重编码，或给 `aud-trim` 加 `--accurate`。
- **amix 的 normalize 参数**：`normalize=0` 需要 ffmpeg 4.4+；旧版会报错，`aud-mix` 会自动去掉该参数重试一次并打印提示，代价是两轨自动各衰减一半。
- **atempo 范围**：单个 atempo 只接受 0.5–2.0，`atempo_chain()` 会把 0.125–8 的倍率自动拆成多个因子串联。
- **loudnorm 两遍**：第一遍的 JSON 从 stderr 解析，不同 ffmpeg 版本键名可能变化；解析失败会降级为单遍动态模式，不会静默给错结果。
- **静音切分只是候选**：`silencedetect` 找的是能量阈值下的区间，语速快、底噪大、有背景音乐时切点会偏。切完必须试听，别当成句子级精准分段。
- **afftdn 不是 AI 降噪**：只能压稳态底噪，强度开太大（>80）会让人声发闷、出现「水下音」。
- 输出不得覆盖输入；批量/切分任务每份产物用独立文件名或目录。
- 本机未安装 ffmpeg 时，所有依赖它的动作会直接报错并提示安装，不会静默失败。
