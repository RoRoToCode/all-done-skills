# 运行环境与排错

## 依赖

| 能力 | 依赖 | 状态 |
| --- | --- | --- |
| 文本扫描 / 脱敏 / 批量 / 报告 / 规则 | Python 标准库 | 必需，零安装 |
| JPEG / PNG / OOXML / PDF 元数据 | Python 标准库 | 必需，零安装 |
| Code128-B 条形码 SVG | Python 标准库 | 必需，零安装 |
| 二维码生成 | `qrcode` + `Pillow` | 可选，缺失时 rc=2 |
| 二维码识别 | `pyzbar`（需系统 zbar）或 `opencv-python` | 可选，缺失时 rc=2 |

安装示例：`<当前解释器> -m pip install qrcode[pil] opencv-python`
（`actions.py check` 第一行会打印当前解释器路径）。**本技能不联网安装、不分发任何二进制或模型权重**。

## 退出码

| 码 | 含义 | 典型原因 |
| --- | --- | --- |
| 0 | 成功 | — |
| 2 | 参数错误 / 缺可选依赖 | 规则名不存在、格式不支持、缺 qrcode / 识别后端 |
| 3 | 输入输出冲突 | 输入不存在、输出等于输入、输出是目录 |
| 5 | 动作失败 | 文件损坏、编码错误、单份文件处理异常 |

## 内置规则

`phone_cn`（11 位手机号号段）、`id_card_cn`（18 位身份证 + 校验位）、
`email`、`bank_card`（13–19 位 + Luhn）、`ipv4`、`mac`、`car_plate_cn`、
`passport_cn`、`qq`、`api_key`（常见密钥前缀）、`url_token`（URL 里的 token 参数）。
自定义规则 JSON：`[{"name": "...", "pattern": "正则", "mask": "mask|placeholder|remove"}]`。

## 排错清单

- **命中 0 条但肉眼能看到手机号**：号码可能被空格/连字符分隔，先规范化文本或加自定义规则。
- **脱敏后文件打不开**：源文件可能是二进制或非常规编码，先确认是纯文本再脱敏；PDF 请用 `pdf-redact`。
- **二维码识别报缺 zbar**：pyzbar 需要系统 libzbar，Windows 上改用 `opencv-python` 后端更省事。
- **元数据清理后仍有信息**：PDF 的注释、修订、XMP 与嵌入对象不在保守清理范围，报告会标 `skipped`。
