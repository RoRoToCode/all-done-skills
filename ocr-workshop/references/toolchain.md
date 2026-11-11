# 依赖与排错

## 依赖矩阵

| 能力 | 依赖 | 是否必需 |
|---|---|---|
| 图片识别 | `rapidocr_onnxruntime`（或 Tesseract 二进制 + 语言包） | 必需；RapidOCR 纯 Python，模型随包离线可用 |
| PDF 识别 | `pymupdf` | 仅 PDF / 批量输入需要，用来把页面渲染成 PNG |
| 表格 CSV | 同上，无额外依赖 | 行列表格由文字框坐标重建 |

## 自检与安装

```bash
python scripts/bootstrap.py check                 # ocr / pdf 两组状态
python scripts/bootstrap.py install --ocr         # 装 RapidOCR
python scripts/bootstrap.py install --pdf         # 装 PyMuPDF
python scripts/actions.py engines                 # 可用引擎 + Tesseract 语言包
```

`install --ocr` **不会**直接 `pip install rapidocr-onnxruntime`：该包声明了 `opencv-python`，网速差时会卡在 44MB 下载上，哪怕本机 `cv2` 已经可用。安装器先探测 `cv2 / numpy / onnxruntime / PIL / yaml / shapely / pyclipper / six`，全部可导入时走 `--no-deps`，缺哪个才补哪个。

## 引擎优先级

1. **rapidocr**：默认。中文质量最好，返回文字 + 置信度 + 坐标，能重建版面与表格。
2. **tesseract**：仅在 RapidOCR 缺席时使用。只返回纯文本（无坐标），因此 JSON 里不含 `box`，表格只能按行拼接。

`--engine rapidocr|tesseract` 可强制指定；指定的引擎不可用会直接报错，不会静默切换。

## 环境变量

| 变量 | 作用 |
|---|---|
| `TESSERACT` / `PDF2DOCX_TESSERACT` | Tesseract 可执行文件路径 |
| `OCR_LANG` | Tesseract 语言组合，默认 `chi_sim+eng` |

## 常见失败

| 现象 | 处理 |
|---|---|
| `未找到 OCR 引擎` | `bootstrap.py install --ocr` |
| `缺少 PyMuPDF，无法渲染 PDF 页面` | `bootstrap.py install --pdf` |
| `PDF 已加密` | 传 `--password` |
| 中文断行、数字错位 | 提高 `--dpi`（300）重跑；或装 Tesseract + `chi_sim` 做对照 |
| 表格识别成普通文本 | 表格需**有框线或明显列间距**；倾斜页先摆正 |
| JSON 里没有坐标 | 当前跑的是 tesseract 通道 |

## 退出码

| 码 | 含义 |
|---|---|
| 0 | 成功（可能带告警） |
| 1 | 安装失败 / 识别过程异常 |
| 2 | 依赖缺失（`actions.py check`、`bootstrap.py check`） |
