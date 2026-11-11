# 视频全搞定 · 用法配方

统一入口：所有动作都经 `python scripts/actions.py run <id> -- <参数>`，
也可直接 `python scripts/<id>.py --input x --output y`。下文用简写。

所有动作依赖本机 `ffmpeg` / `ffprobe`（加入 PATH）；水印文字、幻灯片、文字卡片另需 `Pillow`。

## 格式与体积

### vid-convert 格式转换
```bash
python scripts/vid_convert.py --input a.mov --output b.mp4
python scripts/vid_convert.py --input a.mp4 --output b.webm --vcodec libvp9
python scripts/vid_convert.py --input a.mp4 --output b.mp4 --crf 23   # 控质量
```

### vid-compress 压缩体积
```bash
python scripts/vid_compress.py --input a.mp4 --output b.mp4 --crf 28
python scripts/vid_compress.py --input a.mp4 --output b.mp4 --target-mb 20   # 逼近 20MB
```

## 剪辑处理

### vid-trim 截取片段
```bash
python scripts/vid_trim.py --input a.mp4 --output b.mp4 --start 00:00:05 --end 00:00:15
python scripts/vid_trim.py --input a.mp4 --output b.mp4 --start 5 --duration 10
python scripts/vid_trim.py --input a.mp4 --output b.mp4 --start 5 --duration 3 --reencode  # 精准
```

### vid-concat 拼接合并
```bash
python scripts/vid_concat.py --inputs "p1.mp4,p2.mp4,p3.mp4" --output out.mp4
python scripts/vid_concat.py --inputs "clip*.mp4" --output out.mp4 --reencode
```

### vid-resize 改分辨率 / 比例
```bash
python scripts/vid_resize.py --input a.mp4 --output b.mp4 --width 1280          # 高自动
python scripts/vid_resize.py --input a.mp4 --output b.mp4 --scale 50            # 缩一半
python scripts/vid_resize.py --input a.mp4 --output b.mp4 --width 1920 --height 1080  # 保持比例+黑边
```

### vid-rotate 旋转 / 翻转
```bash
python scripts/vid_rotate.py --input a.mp4 --output b.mp4 --angle 90
python scripts/vid_rotate.py --input a.mp4 --output b.mp4 --flip h
```

## 叠加与提取

### vid-watermark 水印
```bash
python scripts/vid_watermark.py --input a.mp4 --output b.mp4 --text "版权所有" \
  --position bottomright --opacity 180 --size 36 --color FFFFFF
python scripts/vid_watermark.py --input a.mp4 --output b.mp4 --logo logo.png --size 64
```

### vid-extract-audio 提取音频
```bash
python scripts/vid_extract_audio.py --input a.mp4 --output a.mp3 --format mp3
python scripts/vid_extract_audio.py --input a.mp4 --output a.m4a
```

### vid-extract-frames 提取帧 / 截图
```bash
python scripts/vid_extract_frames.py --input a.mp4 --output shot.png --at 00:00:03   # 单帧
python scripts/vid_extract_frames.py --input a.mp4 --output f_%04d.png --every 2     # 每 2 秒
python scripts/vid_extract_frames.py --input a.mp4 --output f_%04d.png --fps 1       # 每秒 1 帧
```

### vid-gif 转 GIF / GIF 转视频
```bash
python scripts/vid_gif.py --input a.mp4 --output a.gif --fps 15 --width 480
python scripts/vid_gif.py --input a.mp4 --output a.gif --start 2 --duration 4
python scripts/vid_gif.py --input a.gif --output a.mp4 --reverse
```

### vid-subs 字幕烧录
```bash
python scripts/vid_subs.py --input a.mp4 --output b.mp4 --subs sub.srt --font-size 28
```

## 生成（无模型，纯本地）

### vid-slideshow 图片生成视频（幻灯片）
```bash
python scripts/vid_slideshow.py --image-dir photos --output show.mp4 --duration 3 --transition fade
python scripts/vid_slideshow.py --images "1.jpg,2.jpg,3.jpg" --output show.mp4 --audio bgm.mp3 --kenburns
python scripts/vid_slideshow.py --image-dir photos --output show.mp4 --resolution 1920x1080
```

### vid-textcard 文字卡片生成视频
```bash
python scripts/vid_textcard.py --title "开场" --body "这是第一页" --output card.mp4
python scripts/vid_textcard.py --cards cards.json --output deck.mp4 --audio bgm.mp3
```
`cards.json` 形如：
```json
[
  {"title": "第一章", "body": "要点一\n要点二", "bg": "#10142b", "accent": "#5b8cff"},
  {"title": "第二章", "body": "更多内容"}
]
```
