命令都在技能根目录执行；`<in>` / `<out>` 换成实际路径，路径含空格要加引号。

## 1. 先看清目录里有什么

```bash
python scripts/file_list.py <in> -o inventory.json --recursive --sort size
python scripts/file_tree.py <in> --depth 2
```

`--format csv|md` 可直接出表格；`--pattern "*.pdf"` 只收指定类型。清单是所有后续动作的起点。

## 2. 找重复文件，只报告不删除

```bash
python scripts/file_dedupe.py <in> -o dupes.json --recursive
python scripts/file_dedupe.py <in> --min-size 1024 --algo sha256
```

先按体积分组、再对同体积文件算哈希，避免对整盘做无谓的哈希计算。报告里每组给出 `keep` 建议与可释放体积，**是否删除由人决定**。

## 3. 批量重命名先看预览

```bash
python scripts/file_rename.py <in> --prefix "2026-" --seq --start 1
python scripts/file_rename.py <in> --prefix "2026-" --seq --start 1 --apply
python scripts/file_rename.py <in> --replace '^IMG_(\d+)' --with 'photo_\1'
```

不带 `--apply` 只打印计划 JSON，不碰任何文件。`--apply` 会写 `rename-map.json`，重名自动避让。

## 4. 校验清单：算一次，之后随时复核

```bash
python scripts/file_hash.py <in> -o checksums.json --recursive
python scripts/file_verify.py checksums.json --root <in> -o verify.json
```

`file_verify` 也认 `sha256sum` 格式的纯文本。结果逐条给 `ok` / `mismatch` / `missing`。

## 5. 按类型或日期归类（复制，不动原件）

```bash
python scripts/file_organize.py <in> -o <out> --by ext
python scripts/file_organize.py <in> -o <out> --by date --apply
```

默认预览；`--apply` 才真正复制。`--by date` 按修改时间建 `2026-11/` 这样的子目录。

## 6. 大文件与两目录差异

```bash
python scripts/file_size.py <in> --top 20 --min-mb 10
python scripts/file_compare.py dirA dirB --hash -o diff.json
```

`--hash` 会额外比较同路径同体积文件的内容哈希，结果分 `only_left` / `only_right` / `different` / `same`。

## 组合流水线

```bash
python scripts/file_list.py raw/ -o inv.json && \
python scripts/file_dedupe.py raw/ -o dup.json && \
python scripts/file_organize.py raw/ -o sorted/ --by ext --apply
```
