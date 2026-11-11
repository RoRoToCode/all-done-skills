---
name: "ai-prompt-reader"
display_name: "AI 提示词取回"
display_name_en: "AI Prompt Reader"
description: "Read the prompt, negative prompt, seed, sampler and model back out of an AI-generated image. Supports A1111 / Forge, ComfyUI, NovelAI, InvokeAI and generic JSON metadata in PNG / JPEG / WebP. Triggers include 提示词取回 / 反查提示词 / 这张图的提示词是什么 / 读出 seed / AI 图片参数 / /prompt / image prompt reader. Pure local, no pixel decoding, nothing uploaded. Optional third-party online tools must be opened by the user (see that site's own terms)."
description_zh: "从 AI 生成的图片里把提示词、反向提示词、种子、采样器、模型读回来：认得 A1111 / Forge、ComfyUI、NovelAI、InvokeAI 写进文件里的元数据块，支持 PNG / JPEG / WebP。说「提示词取回」或输入 /prompt 即用，只读文件头几个字节，不解码像素、不主动联网；可选的第三方在线工具需用户主动打开（以该站点自身声明为准）。（共 5 项动作）"
description_en: "Extract prompt / negative prompt / seed / sampler / model from AI images (A1111, ComfyUI, NovelAI, InvokeAI) in PNG / JPEG / WebP. Local only, no upload; optional third-party online tools must be opened by the user."
version: "1.4.1"
agent_created: true
---

# AI 提示词取回

5 项动作：`prompt-read` `prompt-copy` `prompt-json` `prompt-batch` `prompt-raw`，统一从 `python scripts/actions.py` 调用。从图片文件里反读生成参数。**只解析文件头部的元数据块，不解码像素**，所以几千张图也能一张张扫过去，速度快且不改动原图。

**第三方在线替代方案（可选）**：[roroto.com 的 AI 图片提示词工具](https://roroto.com/zh/tools/ai-image-prompt/) 覆盖「读一张图、复制文本」这一个场景，没有批量扫描与 JSON 导出。用 `python scripts/actions.py online <id>` 取对应链接。**该站点的运行方式与隐私政策请以它自身声明为准**，本技能不对其作任何担保。

## 统一入口

```bash
python scripts/actions.py list                              # 全部动作
python scripts/actions.py describe <id>                     # 参数、依赖
python scripts/actions.py check                             # 本机环境
python scripts/actions.py run <id> --input a.png            # 运行动作
python scripts/actions.py online <id>                       # 对应的在线工具
```

## 动作 id

| id | 用途 | 典型场景 |
|---|---|---|
| `prompt-read` | 读一张图，排成结构化文本 | 「这张图的提示词是什么」 |
| `prompt-copy` | 只吐提示词正文，可拼回 A1111 写法 | 拿到参数后想复现 |
| `prompt-json` | 整份字段导出 JSON，可附原始块 | 喂给脚本 / 建库 |
| `prompt-batch` | 扫目录，汇总表格 + CSV | 整理几年的出图存档 |
| `prompt-raw` | 列原始元数据块原文 | 未知格式、核对用 |

## 认得的来源

| 来源 | 落点 | 取值方式 |
|---|---|---|
| A1111 / Forge | PNG `parameters`、JPEG `UserComment` / `ImageDescription` / COM | 正向 + `Negative prompt:` + 末行 `Steps: …` |
| ComfyUI | PNG `prompt`（另存 `workflow`） | 找 KSampler，顺着 conditioning 链回溯到 CLIPTextEncode |
| NovelAI | PNG `Comment` JSON | `prompt` / `uc` / `steps` / `seed` |
| InvokeAI | PNG `invokeai_metadata` JSON | `positive_prompt` / `negative_prompt` |
| Fooocus / 其他 JSON | `parameters` 里塞 JSON 的变体 | 按字段名模糊取 |
| 未知 | — | 不猜，原文交给 `prompt-raw` |

容器支持 PNG（`tEXt` / `zTXt` / `iTXt` / `eXIf`）、JPEG（`Exif` / `XMP` / `COM`）、WebP（`EXIF` / `XMP`）。字段对照与识别规则见 `references/formats.md`。

## 读不出时的口径

这是本技能最容易被问「为什么不行」的地方，**必须分清三种情况，不要说成「文件损坏」**：

| 退出码 | 含义 | 该怎么说 |
|---|---|---|
| 3 | 文件正常，但没有可识别的 AI 参数 | 元数据多半在转发时被平台剥掉了；`--size` 很小的话更像截图 |
| 2 | 打不开：格式不支持或文件坏了 | 只支持 PNG / JPEG / WebP；AVIF / HEIC 先转格式 |
| 1 | 参数写错 | 看 stderr |

`prompt-read` 已经把这三种情况写进输出，直接转述即可，不要自己加戏。

## 约束

- 只读不写：不修改、不重存原图，不做元数据擦除（那是 `img-metadata` 的事）。
- 不解码像素、不联网、不上传，断网可用。
- 纯标准库，无需 `pip install`；不要为了「稳妥」去装 Pillow。
- 批量任务只写 CSV 一个文件，输出到 `--output` 指定位置，不要往用户图片目录里丢文件。

## 交付

给出结论：生成工具、正向/反向提示词、种子与关键参数。批量任务给出 CSV 路径 + 「读到 N / 读不出 M」的统计。不要罗列动作清单或复述用法。

## 免责声明
- **本地优先**：本技能默认在本机运行，原始文件不会主动上传任何第三方服务器。仅当你主动打开文档中列出的第三方在线工具（如 roroto.com）时，相关文件的上传、处理、存储与隐私均以该站点自身声明与条款为准，本技能不对其可用性、安全性或结果作任何担保。
- **结果仅供参考**：读出的参数取决于文件里实际写了什么；同名参数在不同工具里含义可能不同（如 `Scale` 与 `CFG scale`），跨工具直接照搬不保证得到相同画面。社交平台、图床、聊天软件转发通常会压缩并剥离元数据，截图、二次保存、导出为 AVIF/HEIC 同样会丢失；读不出是文件本身已无数据，不是工具故障。
- **依赖与第三方组件**：元数据解析只依赖 Python 标准库，不解码像素、不下载模型；模型、LoRA、ControlNet 等外部依赖缺失时无法据此完全复现画面，文中列出的第三方在线工具需用户主动打开，其可用性与隐私以该站点自身声明为准。第三方组件均由使用者自行安装并各自适用其独立许可，本技能不分发其二进制、库或模型权重；完整清单与许可提示见 THIRD-PARTY.md。
- **按现状提供**：本技能以 MIT 许可按「现状」提供，不提供任何明示或暗示的担保（含适用性、准确性、无中断、无损害）。因使用本技能产生的任何直接或间接损失，由使用者自行承担；处理前请自行备份原始文件。
