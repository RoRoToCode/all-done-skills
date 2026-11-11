---
name: "image-all-done"
display_name: "图片全搞定"
display_name_en: "Images, All Done"
description: "Local image toolkit — convert formats, compress, resize, crop, watermark, rotate, merge, remove background, upscale, OCR, batch process, strip metadata. Triggers include 图片全搞定 / 图像工具箱 / /img / 图片转格式 / 图片压缩 / 批量改尺寸 / 去背景 / 图片放大 / 图片转文字 / 加水印. All processing runs locally; nothing is uploaded."
description_zh: "本机图片处理工具箱：格式互转 · 压缩 · 改尺寸 · 裁剪 · 水印 · 旋转 · 拼图 · 智能抠图 · 高清放大 · 文字识别 OCR（优先 RapidOCR，Tesseract 兜底）· 批量处理 · 清除 EXIF。说「图片全搞定」或输入 /img 即用，全程本地处理不上传。"
description_en: "Local image toolkit — convert, compress, resize, crop, watermark, rotate, merge, background removal, upscale, OCR, batch, strip EXIF. Triggers: 图片全搞定 / /img / image convert / compress image / remove bg / upscale."
version: "1.4.1"
agent_created: true
---

# 图片全搞定

本机图片处理技能。12 项动作统一从 `python scripts/actions.py` 调用，动作清单的唯一数据源是 `assets/actions.json`。

**第三方在线替代方案（可选）**：[roroto.com](https://roroto.com) 的图片工具只覆盖一部分动作——格式转换 / 压缩 / 改尺寸 / 裁剪 / 水印 / 拼图 / 抠图 / OCR 有对应页，旋转、放大、批量、元信息四项该站没有。用 `python scripts/actions.py online <id>` 取对应链接，返回「无」就表示该站没有替代、只能本地处理或安装依赖。**该站点的运行方式与隐私政策请以它自身声明为准**，本技能不对其作任何担保。

## 统一入口

```bash
python scripts/actions.py list              # 全部动作
python scripts/actions.py describe <id>     # 参数、依赖
python scripts/actions.py check             # 本机依赖
python scripts/actions.py run <id> --input a.png --output out.png
python scripts/actions.py online <id>       # 对应的在线工具
```

## 动作 id

- 格式与体积：`img-convert` `img-compress` `img-resize` `img-crop`
- 排版与水印：`img-watermark` `img-rotate` `img-merge`
- 智能处理：`img-bgremove` `img-upscale` `img-ocr`
- 批量与元信息：`img-batch` `img-metadata`

需要精细参数时直接调脚本，见 `references/recipes.md`；依赖安装、降级与排错见 `references/toolchain.md`。

## 约束

- 全程本地处理，原始图片不上传云端。
- 输出不得覆盖输入；批量任务每份文件用独立输出目录。
- 依赖缺失时先看 `references/toolchain.md`（Pillow / RapidOCR / Tesseract / rembg / Real-ESRGAN 的安装与降级）；模型权重体积较大，下载前先征得用户同意，不做长篇解释。

## 交付

给出产物路径与关键校验（尺寸、格式、体积），不输出功能清单或操作说明。

## 免责声明
- **本地优先**：本技能默认在本机运行，原始文件不会主动上传任何第三方服务器。仅当你主动打开文档中列出的第三方在线工具（如 roroto.com）时，相关文件的上传、处理、存储与隐私均以该站点自身声明与条款为准，本技能不对其可用性、安全性或结果作任何担保。
- **结果仅供参考**：OCR 文字识别、智能抠图、AI 高清放大等由算法/模型生成，可能存在识别偏差、边缘瑕疵、细节丢失或色差，重要图片请务必保留并核对原图。
- **依赖与第三方组件**：部分动作需安装第三方库与模型（rembg、Real-ESRGAN、Tesseract 等），未安装时功能受限或自动降级；相关模型权重、字体的下载与版权归各自作者所有，由使用者自行获取并合规使用。第三方组件均由使用者自行安装并各自适用其独立许可，本技能不分发其二进制、库或模型权重；完整清单与许可提示见 THIRD-PARTY.md。
- **按现状提供**：本技能以 MIT 许可按「现状」提供，不提供任何明示或暗示的担保（含适用性、准确性、无中断、无损害）。因使用本技能产生的任何直接或间接损失，由使用者自行承担；处理前请自行备份原始文件。
