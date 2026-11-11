# 第三方组件与许可声明

本技能包中的源码、脚本与文档由 RoRoTo 以 MIT 许可发布，详见同目录 `LICENSE`。
本技能通过 Python 导入或命令行调用使用第三方组件，**不随包分发任何第三方
二进制程序、库文件、语言包、字体或模型权重**；这些组件均由使用者在本机
自行安装，各自适用其独立许可条款。下表仅为信息性提示，许可种类可能随版本、
发行方式或编译选项变化，一律以各项目官方声明为准。

## 常见外部依赖与许可提示

| 组件 | 典型许可（以官方为准） | 用途 |
|---|---|---|
| Tesseract OCR | Apache-2.0（语言数据包按其发布条款） | 文字识别 |
| PaddleOCR / RapidOCR / rapidocr_onnxruntime | Apache-2.0 | 文字识别 |
| PyMuPDF (fitz) | AGPL-3.0 或商业双许可 | PDF 解析与渲染 |
| pypdf | BSD-3-Clause | PDF 读写 |
| Pillow | HPND（类 MIT） | 图像读写 |
| python-docx / openpyxl / python-pptx | MIT / BSD 系 | Office 文档读写 |
| beautifulsoup4 / lxml / requests / pandas | MIT / BSD / Apache 系 | 解析与数据处理 |
| ffmpeg / ffprobe | LGPL-2.1+ 或 GPL-2.0+，取决于编译选项 | 音视频转码与探测 |
| openai-whisper / faster-whisper | MIT（模型权重按其发布条款） | 语音转写 |
| LibreOffice (soffice) | MPL-2.0 | Office 转 PDF |
| Calibre (ebook-convert) | GPL-3.0 | 电子书格式互转 |
| rembg / Real-ESRGAN / onnxruntime | MIT / BSD / Apache 系 | 背景去除与超分 |
| pyzipper / py7zr / rarfile / unrar | 各组件独立许可（unrar 为专有许可） | 压缩格式扩展 |
| Microsoft Edge / Google Chrome | 专有许可 | 网页渲染与截图 |
| 系统字体、OCR 语言包、模型权重 | 版权归各自权利人 | 渲染与识别 |

各技能实际用到的组件见本目录 `SKILL.md`「免责声明」第 3 条与
`references/toolchain.md`，并非每个技能都需要上表全部组件。

## 使用者的合规责任

- 安装、使用、商用或再分发上述组件前，请自行核对并遵守其许可条款；
  GPL / LGPL / AGPL 类组件的组合与衍生作品可能产生额外的开源义务。
- 部分编解码器、字体与模型权重可能涉及专利、授权或地域限制，使用者需
  自行评估；第三方在线工具（若有）的隐私与条款以其自身声明为准。
- 处理电子书、PDF、网页、图片、音视频等第三方内容前，请确认你拥有合法
  处理与转换的权利；本技能不提供绕过 DRM、访问控制或版权保护的能力。
- 本技能不对第三方组件的可用性、安全性、许可状态或处理结果作担保，
  相关权利与责任归各自权利人。

本文档为信息性说明，不构成法律意见。
