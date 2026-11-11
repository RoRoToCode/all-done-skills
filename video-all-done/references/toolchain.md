# 工具链与环境

## 两层依赖

| 能力 | 依赖 | 是否必需 |
|---|---|---|
| 全部编辑动作（转码/压缩/截取/拼接/缩放/旋转/水印/抽帧/ GIF / 字幕） | `ffmpeg` + `ffprobe` 二进制 | 必需，加入 PATH |
| 水印文字、幻灯片、文字卡片的渲染 | `Pillow`（Python 包） | 仅这些动作需要 |

中文渲染走系统字体（Windows：微软雅黑 / 黑体；macOS：PingFang；Linux：Noto Sans CJK），无需自带字体文件。水印文字先用 Pillow 渲染成透明 PNG，再用 ffmpeg `overlay` 叠加，因此无论 ffmpeg 自身是否带中文字体都能正常显示。

## ffmpeg 安装

`python scripts/actions.py check` 会报告 `ffmpeg` / `ffprobe` 是否在 PATH 上。缺失时安装：

- Windows：`scoop install ffmpeg` 或 `choco install ffmpeg`；也可到 https://ffmpeg.org 下载，把 `bin` 目录加入 PATH。
- macOS：`brew install ffmpeg`
- Linux（Debian/Ubuntu）：`sudo apt install ffmpeg`

Pillow：`pip install Pillow`（如本机解释器无网，先征得用户同意再安装）。

## 退出码

| 码 | 含义 | 处理 |
|---|---|---|
| 0 | 成功 | 继续 |
| 2 | 用法错误 / 缺参数 | 修参数 |
| 3 | 输入/输出错误（路径不存在、输出=输入） | 检查路径、目录、权限 |
| 5 | 转换/拼接失败（ffmpeg 返回非 0） | 看 stderr，换参数或格式 |

## 常用编码速查

```
vid-convert : -c:v libx264 -c:a aac   （webm 用 libvp9/libvorbis）
vid-compress: -crf 28  （0-51，越大越小）或 -b:v 码率
vid-trim    : -ss 起点 -to 终点 -c copy（流拷贝）；--reencode 改重编码
vid-concat  : concat demuxer，-c copy；编码不一致加 --reencode
vid-resize  : scale=W:-2 / scale=-2:H / scale 按比例+pad
vid-rotate  : transpose=1(90°CW) / transpose=2(90°CCW) / hflip / vflip
vid-watermark: 文字→Pillow PNG→overlay；logo→scale+overlay
vid-extract-audio: -vn -acodec aac|libmp3lame|pcm_s16le
vid-extract-frames: -vf fps=... 或 -ss + -frames:v 1
vid-gif     : palettegen+paletteuse 两遍调色板；GIF→视频直接转封装
vid-subs    : subtitles=xxx.srt:force_style='...'
vid-slideshow / vid-textcard: 每页渲染成 PNG → 每页生成等长 mp4 →
             fade 用 xfade 衔接，none 用 concat demuxer；可选 --audio 循环配乐
```

## 说明

- 输出不得覆盖输入；多段/批量任务每份产物用独立输出名。
- 旋转/翻转等会改变画面参数的操作在部分封装下会触发重编码，以实际产物为准。
- 本机未安装 ffmpeg 时，所有依赖它的动作会直接报错并提示安装，不会静默失败。
