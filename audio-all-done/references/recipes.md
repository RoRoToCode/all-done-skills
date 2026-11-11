# 音频全搞定 · 用法配方

统一入口：所有动作都经 `python scripts/actions.py run <id> -- <参数>`，
也可直接 `python scripts/<id>.py --input x --output y`。下文用简写。

所有动作依赖本机 `ffmpeg` / `ffprobe`（加入 PATH）；无 Python 第三方库依赖。

## 格式与体积

### aud-convert 格式转换
```bash
python scripts/aud_convert.py --input a.wav --output a.mp3
python scripts/aud_convert.py --input a.m4a --output a.flac
python scripts/aud_convert.py --input a.wav --output a.ogg --quality 5
python scripts/aud_convert.py --input a.mp3 --output a_16k.wav --sample-rate 16000 --channels 1
python scripts/aud_convert.py --input a.wav --output a_24.wav --bit-depth 24
python scripts/aud_convert.py --input a.wav --output a.aac --codec aac --bitrate 256k
```

### aud-compress 压缩体积
```bash
python scripts/aud_compress.py --input a.wav --output a.mp3 --bitrate 96k
python scripts/aud_compress.py --input a.wav --output a.m4a --target-mb 5
python scripts/aud_compress.py --input a.wav --output a.opus --bitrate 64k
```

### aud-resample 采样率 / 声道 / 位深
```bash
python scripts/aud_resample.py --input a.wav --output a_48k.wav --sample-rate 48000
python scripts/aud_resample.py --input a.mp3 --output a_mono.mp3 --channels 1
python scripts/aud_resample.py --input a.wav --output a_24.wav --bit-depth 24
python scripts/aud_resample.py --input a.mp3 --output asr.wav --sample-rate 16000 --channels 1
```

## 剪辑处理

### aud-trim 截取片段
```bash
python scripts/aud_trim.py --input a.mp3 --output b.mp3 --start 00:00:05 --end 00:00:15
python scripts/aud_trim.py --input a.mp3 --output b.mp3 --start 5 --duration 10
python scripts/aud_trim.py --input a.mp3 --output b.mp3 --start 5 --duration 3 --accurate
python scripts/aud_trim.py --input a.mp3 --output b.mp3 --start 0 --duration 30 --copy
```

### aud-concat 拼接合并
```bash
python scripts/aud_concat.py --inputs "p1.mp3,p2.mp3,p3.mp3" --output out.mp3
python scripts/aud_concat.py --inputs "clip*.wav" --output out.wav
python scripts/aud_concat.py --inputs "a.wav,b.mp3" --output out.mp3 --reencode
```

### aud-split 按静音 / 等长切分
```bash
python scripts/aud_split.py --input speech.wav --output parts/ --mode silence
python scripts/aud_split.py --input speech.mp3 --output parts/ --mode silence \
  --noise-db -40dB --min-silence 0.6 --min-length 2
python scripts/aud_split.py --input lecture.mp3 --output parts/ --mode equal --segment-seconds 60
python scripts/aud_split.py --input a.mp3 --output parts/ --mode equal --copy
```

### aud-speed 变速 / 变调
```bash
python scripts/aud_speed.py --input a.mp3 --output fast.mp3 --speed 1.5
python scripts/aud_speed.py --input a.mp3 --output slow.mp3 --speed 0.75
python scripts/aud_speed.py --input a.mp3 --output high.mp3 --pitch 2
python scripts/aud_speed.py --input a.mp3 --output chip.mp3 --speed 1.25 --pitch 4
python scripts/aud_speed.py --input a.wav --output b.wav --pitch -3 --sample-rate 44100
```

## 音质与效果

### aud-volume 音量增益
```bash
python scripts/aud_volume.py --input a.mp3 --output b.mp3 --gain-db 6
python scripts/aud_volume.py --input a.mp3 --output b.mp3 --gain-db -3
python scripts/aud_volume.py --input a.mp3 --output b.mp3 --gain 1.5 --limiter
```

### aud-normalize 响度归一化
```bash
python scripts/aud_normalize.py --input raw.wav --output norm.wav
python scripts/aud_normalize.py --input ep.mp3 --output ep_norm.mp3 --target-lufs -16 --two-pass
python scripts/aud_normalize.py --input ep.mp3 --output ep_yt.mp3 --target-lufs -14 --tp -1 --two-pass
```

### aud-denoise 轻量降噪
```bash
python scripts/aud_denoise.py --input noisy.wav --output clean.wav
python scripts/aud_denoise.py --input noisy.wav --output clean.wav --strength 70 --highpass 100
python scripts/aud_denoise.py --input tape.wav --output clean.wav --strength 35 --lowpass 12000
```

### aud-fade 淡入 / 淡出
```bash
python scripts/aud_fade.py --input a.mp3 --output b.mp3 --fade-in 2 --fade-out 3
python scripts/aud_fade.py --input a.mp3 --output b.mp3 --fade-out 5 --curve qsin
python scripts/aud_fade.py --input a.mp3 --output b.mp3 --fade-out 3 --duration 00:03:20
```

### aud-mix 双轨混音
```bash
python scripts/aud_mix.py --input voice.wav --mix bgm.mp3 --output mixed.mp3
python scripts/aud_mix.py --input voice.wav --mix bgm.mp3 --output mixed.mp3 \
  --mix-volume 0.15 --loop
python scripts/aud_mix.py --input a.wav --mix b.wav --output m.wav --main-volume 0.8 --mix-volume 0.8
```

## 分析提取

### aud-info 音频信息探测
```bash
python scripts/aud_info.py --input a.mp3
python scripts/aud_info.py --input a.mp3 --format json
python scripts/aud_info.py --input a.mp3 --output a.meta.json
```

### aud-visualize 波形图 / 频谱图
```bash
python scripts/aud_visualize.py --input a.mp3 --output wave.png
python scripts/aud_visualize.py --input a.mp3 --output spec.png --mode spectrum
python scripts/aud_visualize.py --input stereo.wav --output wave.png --size 2000x600 \
  --split-channels --color "#ff6b6b"
```

### aud-extract 从视频提取音轨
```bash
python scripts/aud_extract.py --input clip.mp4 --output clip.mp3
python scripts/aud_extract.py --input clip.mkv --output clip.m4a --copy
python scripts/aud_extract.py --input clip.mp4 --output asr.wav --sample-rate 16000 --mono
python scripts/aud_extract.py --input clip.mp4 --output clip.flac
```
