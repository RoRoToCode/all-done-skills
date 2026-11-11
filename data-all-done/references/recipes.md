命令都在技能根目录执行；`<in>` / `<out>` 换成实际路径，路径含空格要加引号。

## 1. 格式互转

```bash
python scripts/data_convert.py <in>.csv -o <out>.json
python scripts/data_convert.py <in>.json -o <out>.md --to md
python scripts/data_convert.py <in>.json -o <out>.csv --to csv
```

不给 `--from` / `--to` 时按扩展名推断。CSV 默认 UTF-8，中文给 Excel 用可先转出再用 `text-all-done` 加 BOM。

## 2. 转之前先体检

```bash
python scripts/data_validate.py <in>.csv -o check.json
python scripts/data_schema.py <in>.json -o schema.json
```

校验报告给记录数、字段一致性、空值与疑似类型错误；schema 输出 JSON Schema draft-07 草案。

## 3. 筛选 / 选列 / 排序 / 去重

```bash
python scripts/data_filter.py <in>.csv -o hit.csv --where "amount >= 100" --where "status = paid"
python scripts/data_select.py <in>.csv -o slim.csv --fields id,name,amount --rename "name:客户名"
python scripts/data_sort.py <in>.csv -o sorted.csv --by amount --numeric --desc
python scripts/data_dedupe.py <in>.csv -o uniq.csv --by id --keep last
```

`--where` 支持 `= != > < >= <= contains startswith endswith regex in`，多个条件默认全部满足，可加 `--match any`。

## 4. 合并与比对

```bash
python scripts/data_merge.py --inputs a.csv b.csv -o all.csv
python scripts/data_merge.py --inputs users.csv orders.csv -o joined.json --by id --how left
python scripts/data_diff.py old.csv new.csv -o diff.json --key id
```

默认按行拼接；`--by` 指定键时做左连接（右表同键首条记录合并进左表）。

## 5. 画像、拆表与扁平化

```bash
python scripts/data_stats.py <in>.csv -o stats.json --top 10
python scripts/data_split.py <in>.csv -o parts/ --by rows --size 5000
python scripts/data_flatten.py nested.json -o flat.csv --to csv
```

`data_flatten` 把嵌套字段变成 `a.b.0.c` 这样的点路径列，之后就能直接转 CSV/Markdown。

## 组合流水线

```bash
python scripts/data_flatten.py raw.json -o flat.json && \
python scripts/data_filter.py flat.json -o hit.json --where "state = done" && \
python scripts/data_convert.py hit.json -o report.md --to md
```
