# 用法配方

统一入口是 `python scripts/actions.py run <id> -- <参数>`，也可以直接
`python scripts/prompt_read.py --input x.png`。下文用简写。

## prompt-read 读一张图

```bash
python scripts/prompt_read.py --input out.png
python scripts/prompt_read.py --input out.png --max 120     # 提示词只显示前 120 字
```

输出示例（A1111）：

```
a1111.png
  容器 PNG  832x1216  元数据块 1 个：parameters
  生成工具 A1111 / Forge

  正向提示词
    masterpiece, best quality, 1girl, silver hair, kimono
  反向提示词
    lowres, bad anatomy, watermark

  参数
    Steps             28
    Sampler           DPM++ 2M Karras
    CFG scale         7
    Seed              3847291056
    Model             anythingV5_v5PrtRE
```

读不出时退出码 3，并给出原因（无文字块 / 有块但不是 AI 格式）。文件打不开退出码 2。

## prompt-copy 只要提示词正文

```bash
python scripts/prompt_copy.py --input out.png                          # 正向，打到屏幕
python scripts/prompt_copy.py --input out.png --part negative          # 只要反向
python scripts/prompt_copy.py --input out.png --part both              # 拼成 A1111 写法
python scripts/prompt_copy.py --input out.png --output prompt.txt      # 写文件
```

`--part both` 的输出可以直接粘回 A1111 的提示词框：

```
masterpiece, 1girl, silver hair

Negative prompt: lowres, bad anatomy
```

## prompt-json 导出结构化数据

```bash
python scripts/prompt_json.py --input out.png
python scripts/prompt_json.py --input out.png --raw --output meta.json   # 附原始块全文
python scripts/prompt_json.py --input out.png --indent 0                 # 压成一行
```

`params` 是「标签 → 值」的对象，字段名沿用原工具写法（`CFG scale` / `Seed` …），
便于和已有脚本对齐。

## prompt-batch 扫一个目录

```bash
python scripts/prompt_batch.py --input-dir D:\gen\2024
python scripts/prompt_batch.py --input-dir D:\gen --recursive --output D:\gen\index.csv
python scripts/prompt_batch.py --input-dir D:\gen --no-csv          # 只看屏幕
python scripts/prompt_batch.py --input-dir D:\gen --ext png,jpg     # 限定后缀
```

屏幕上是速览表，CSV 有 14 列：文件、格式、生成工具、模型、Seed、Steps、Sampler、
CFG、画布、生成尺寸、正向字数、正向提示词、反向提示词、备注。

CSV 用 UTF-8-BOM 写入，Excel 直接双击不会乱码。

典型用途：想找「同一组提示词出过的所有图」→ 按正向提示词列排序；
想知道「硬盘里哪些图还能复现」→ 备注列为空的都能读全参数。

## prompt-raw 看原始块

```bash
python scripts/prompt_raw.py --input out.png
python scripts/prompt_raw.py --input out.png --name parameters --full
```

遇到认不出的工具时先跑这个：块名和原文会告诉你它是哪家的格式，
必要时再让 `prompt-json --raw` 落盘做二次分析。

## 组合用法

```bash
# 全部图导出 JSON，再用 jq 统计用过的模型
for f in *.png; do python scripts/prompt_json.py --input "$f" --indent 0 \
  --output "meta/${f%.png}.json"; done
```

批量场景优先用 `prompt-batch`：它一次打开目录、只读文件头，
比循环调用 `prompt-json` 快得多，也不会产生成百上千个小文件。
