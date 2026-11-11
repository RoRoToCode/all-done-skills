# 图片全搞定 · 用法配方

统一入口：所有动作都经 `python scripts/actions.py run <id> -- <参数>`，
也可直接 `python scripts/<id>.py --input x --output y`。下文用简写。

## 格式与体积

### img-convert 格式互转
```bash
python scripts/img_convert.py --input a.png --output b.jpg          # 转 JPG（透明变白底）
python scripts/img_convert.py --input a.png --output b.webp --quality 80
python scripts/img_convert.py --input a.heic --output a.png --background FFFFFF
```
支持 png / jpg / webp / bmp / tiff。转 JPG 时 RGBA/LA 自动压白底；`--background` 改底色。

### img-compress 压缩体积
```bash
python scripts/img_compress.py --input a.png --output b.jpg --quality 75
python scripts/img_compress.py --input a.png --output b.jpg --target-kb 200   # 自动选质量逼近 200KB
```
PNG 走优化；jpg/webp 走有损质量。

### img-resize 改尺寸 / 批量
```bash
python scripts/img_resize.py --input a.png --output b.png --long-edge 1080   # 最长边 1080
python scripts/img_resize.py --input a.png --output b.png --scale 50          # 缩到一半
python scripts/img_resize.py --input a.png --output b.png --width 800 --height 600 --no-keep-ratio
```

### img-crop 裁剪
```bash
python scripts/img_crop.py --input a.png --output b.png --square              # 居中最大正方形
python scripts/img_crop.py --input a.png --output b.png --ratio 16:9         # 居中 16:9
python scripts/img_crop.py --input a.png --output b.png --box 100,100,500,400
```

## 排版与水印

### img-watermark 加水印
```bash
python scripts/img_watermark.py --input a.jpg --output b.jpg --text "版权所有" \
  --font-size 36 --opacity 128 --position tile --color FFFFFF
# --position center 居中单点；--opacity 0-255 越大越实
```

### img-rotate 旋转 / 翻转
```bash
python scripts/img_rotate.py --input a.jpg --output b.jpg --angle 90
python scripts/img_rotate.py --input a.jpg --output b.jpg --flip h           # 水平翻转
# 默认按 EXIF 方向自动校正；--no-auto-orient 关闭
```

### img-merge 拼图 / 合并
```bash
python scripts/img_merge.py --inputs 1.png 2.png 3.png --output out.png --layout h   # 横向
python scripts/img_merge.py --inputs *.png --output out.png --layout grid --cols 3 --gap 10
```

## 智能处理

### img-bgremove 智能抠图（需 rembg）
```bash
pip install rembg                       # 首次会自动下载模型
python scripts/img_bgremove.py --input a.jpg --output a_nobg.png --model u2net
```

### img-upscale 高清放大（realesrgan 可选，缺失自动回退插值）
```bash
pip install realesrgan                  # 可选，获得 AI 画质
python scripts/img_upscale.py --input a.png --output b.png --scale 4
```

### img-ocr 图片文字识别（需 Tesseract + pytesseract）
```bash
# 安装 Tesseract 并加入 PATH，Windows 另装 chi_sim 语言包；pip install pytesseract
python scripts/img_ocr.py --input a.png --output text.txt --lang chi_sim+eng
```

## 批量与元信息

### img-batch 批量处理
```bash
python scripts/img_batch.py --input-dir in --output-dir out --action convert --ext webp --quality 80
python scripts/img_batch.py --input-dir in --output-dir out --action compress --quality 70
python scripts/img_batch.py --input-dir in --output-dir out --action resize --long-edge 1920
```

### img-metadata 查看 / 清除 EXIF
```bash
python scripts/img_metadata.py --input a.jpg                  # 仅查看
python scripts/img_metadata.py --input a.jpg --output b.jpg   # 另存并剥离 EXIF
```
