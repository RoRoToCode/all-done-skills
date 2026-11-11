# 常用配方

命令都在技能根目录执行；`<in>` / `<out>` 换成实际路径，路径含空格要加引号。

## 1. 乱码先从"看清楚"开始

```bash
python scripts/txt_convert.py <in> --check          # 只探测，不写文件
python scripts/txt_convert.py <in> -o <out> --to utf-8-bom
```

GBK 的 CSV 在 Excel 里要正常显示中文，`--to utf-8-bom` 比纯 UTF-8 更稳。探测结果可疑时用 `--from gb18030` 显式指定。

## 2. 排版前统一换行与空行

```bash
python scripts/txt_normalize.py <in> -o <out> --newline crlf --max-blank 1
```

`--max-blank 0` 会删掉所有空行（适合把稿件压成一整段再重组）；`--no-final-newline` 用于不能有多余换行的场景。

## 3. 清单 / 日志去重

```bash
python scripts/txt_dedupe.py <in> -o <out> --ignore-case --ignore-space --report-only
python scripts/txt_dedupe.py <in> -o <out> --keep last --sort
```

先 `--report-only` 看 `removed` 与 `top_duplicates`，确认重复是"真重复"再落盘。

## 4. 批量替换敏感信息

```bash
python scripts/txt_replace.py <in> -o <out> --pattern '1[3-9]\d{9}' --repl '<手机号>'
python scripts/txt_replace.py <in> --pattern '（' --literal --dry-run
```

默认走正则，`--literal` 把模式当纯文本。**不给 `-o` 就只报命中数**，这是刻意的：替换不可逆。

## 5. 两个版本比差异

```bash
python scripts/txt_diff.py old.txt new.txt --context 2 --json
python scripts/txt_diff.py old.txt new.txt -o diff.patch
```

两个文件编码可以不同（各自嗅探）；`--ignore-space` 用于排除缩进噪声。

## 6. 字数与词频

```bash
python scripts/txt_stats.py <in> --top 30 -o stats.json
python scripts/txt_stats.py <in> --stopwords stopwords.txt
```

`reading_minutes_zh` 按 300 字/分钟估算，只作参考。

## 7. 大文件切分

```bash
python scripts/txt_split.py big.log -o parts --by lines --size 50000
python scripts/txt_split.py big.csv -o parts --by bytes --size 5000000 --to utf-8-bom
```

产物目录里会有 `<prefix>-manifest.json`，记录每份的行数与权重，便于合并回去。

## 组合流水线

```bash
python scripts/txt_convert.py raw_gbk.txt -o step1.txt --to utf-8 \
  && python scripts/txt_normalize.py step1.txt -o step2.txt --newline lf \
  && python scripts/txt_dedupe.py step2.txt -o final.txt --ignore-space
```
