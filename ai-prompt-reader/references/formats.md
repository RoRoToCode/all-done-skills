# 元数据格式对照

## 容器层：文字块从哪来

| 容器 | 块 | 说明 |
|---|---|---|
| PNG | `tEXt` | 最常见。关键字 + Latin-1 正文，A1111 的 `parameters` 就在这里 |
| PNG | `zTXt` | 同 `tEXt`，正文 zlib 压缩（A1111 勾了压缩写入时） |
| PNG | `iTXt` | UTF-8，可压可不压；中文提示词多是这种 |
| PNG | `eXIf` | 部分工具（如 A1111 的 stealth pnginfo）把参数写进 EXIF `UserComment` |
| JPEG | APP1 `Exif` | `UserComment`(0x9286)、`ImageDescription`(0x010E)、`XPComment`(0x9C9C) |
| JPEG | APP1 `XMP` | 少数工具写参数；正文里同样能找到 `Negative prompt:` |
| JPEG | `COM`(0xFFFE) | 有的工具把整段 parameters 塞进注释 |
| WebP | `EXIF` | 同 JPEG 的 EXIF 结构 |
| WebP | `XMP ` | XMP 包 |

EXIF 里的 `UserComment` 前 8 字节是字符集标记（`ASCII` / `UNICODE` / `JIS`），
正文才跟在后面；`UNICODE` 通常是 UTF-16。跳过这 8 字节直接读会得到一串方块，
这是很多工具读 A1111 图只读出乱码的原因。`UserComment` 位于 Exif 子 IFD
（经 `0x8769` 指针跳转），不在 IFD0 里。

## A1111 / Forge

单个文本块，三段式：

```
<正向提示词，可多行>

Negative prompt: <反向提示词，可多行>
Steps: 28, Sampler: DPM++ 2M Karras, CFG scale: 7, Seed: 3847291056, Size: 832x1216
```

识别规则：最后一条非空行能按逗号拆出 ≥2 组 `键: 值`，且键里出现
`Steps` / `Sampler` / `Seed` / `CFG scale` 之一，才认定为设置行。
拆逗号时会跳过引号与括号内的内容，所以
`Lora hashes: "add_detail: 7c6bad76eb54"` 不会被切碎。

没有 `Negative prompt:` 行是正常的（用户没填反向），此时整个前段都是正向。

## ComfyUI

`prompt` 块是**执行图**（API 格式），`workflow` 块是**UI 图**。取参数走 `prompt`：

1. 找 `class_type` 含 `sampler` 且带 `positive` 输入的节点（多个时取 `steps` 最大的）；
2. `seed` / `noise_seed`、`steps`、`cfg`、`sampler_name`、`scheduler`、`denoise` 直接取；
3. `positive` / `negative` 是 `[节点 id, 槽位]` 链接，顺着链接回溯，直到某个节点
   的 `inputs` 里有 `text` / `text_g` / `text_l`（SDXL 的 CLIPTextEncode 用后两个）；
   中间夹 `ConditioningCombine`、`ControlNetApplyAdvanced` 这类节点也能穿过去；
4. 模型取 `CheckpointLoader*` 的 `ckpt_name`（或 `UNETLoader` 的 `unet_name`）；
5. 尺寸取 `EmptyLatentImage` / `EmptySD3LatentImage` 的 `width` / `height`。

回路上限 12 层、节点去重，避免自引用图导致死循环。

## NovelAI

PNG 的 `Comment` 块是 JSON，关键字段：

| 字段 | 含义 |
|---|---|
| `prompt` | 正向（`{}` 是权重语法，原样保留） |
| `uc` | 反向（undesired content） |
| `steps` `scale` `seed` `sampler` `noise_schedule` | 步数 / CFG / 种子 / 采样器 / 噪声调度 |
| `width` `height` | 生成尺寸 |

`Software` 块同时写着 `NovelAI`，用来区分「恰好也叫 Comment 的其他 JSON」。

## InvokeAI

`invokeai_metadata` 块，字段是平铺的：`positive_prompt`、`negative_prompt`、
`width`、`height`、`seed`、`cfg_scale`、`steps`、`scheduler`，
`model` 是对象（取 `model_name`）。`generation_mode` 会作为备注输出（txt2img / img2img）。

注意 InvokeAI 把采样器写在 `scheduler` 里，所以 `Sampler` 与 `Schedule` 可能同值 ——
这种情况会去重，只留一条。

## 其他

- **Fooocus**：`parameters` 块是 JSON（`Prompt` / `Negative Prompt` / `Styles` / `Seed`），
  走通用 JSON 分支。
- **SwarmUI / 自研工具**：只要有 `prompt` / `positive_prompt` / `negative_prompt`
  这类字段就能取到正文；其余字段原样列在参数里。
- **无法识别**：`tool` 为空，退出码 3，用 `prompt-raw` 看原文。

## 为什么读不出

| 现象 | 原因 |
|---|---|
| 块数为 0 | 平台转发 / 图床压缩 / 聊天软件发图都会剥元数据；截图、二次保存同样会丢 |
| 有块但无参数 | 只剩 `Software`、`IHDR` 之类，或工具用了本技能未覆盖的格式 |
| 尺寸很小（如 512 以下） | 多半是缩略图或截图，原图参数早已不在这份文件里 |
| 打不开 | AVIF / HEIC / GIF 不在支持范围，先转成 PNG 或 JPEG |

`prompt-read` 会把上面这些情况区分开并直接写进输出，不要笼统说成「图片损坏」。
