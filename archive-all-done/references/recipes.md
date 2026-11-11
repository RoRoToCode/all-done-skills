# 压缩包全搞定 · 用法配方

统一入口：`python scripts/actions.py run <id> -- <参数>`；也可直接
`python scripts/arc_create.py --inputs a.txt --output out.zip`。
所有命令在技能目录下执行；路径用绝对路径最稳。**默认无需逐项确认**，不对每个文件弹确认。

## 打包与解包

### arc-create 创建压缩包
```bash
python scripts/arc_create.py --inputs report.docx img/ --output out.zip
python scripts/arc_create.py --inputs src/ --output src.tar.gz --level 9
python scripts/arc_create.py --inputs src/ --output src.tar.xz --exclude "*.pyc" __pycache__ .git
python scripts/arc_create.py --inputs src/ --output out.zip --base /work/project --comment "2026 归档"
```
`--format` 省略时按输出扩展名判断；`--base` 决定归档内的相对根。

### arc-extract 解压
```bash
python scripts/arc_extract.py --input out.zip --output extracted/
python scripts/arc_extract.py --input data.tar.gz --output out/ --strip-components 1
python scripts/arc_extract.py --input out.zip --output out/ --members "*.md" "docs/*"
python scripts/arc_extract.py --input out.zip --output out/ --on-conflict overwrite
```
默认重名自动改名 ` (2)`。绝对路径 / `..` / 盘符 / 链接条目一律拒绝。

## 查看与校验

### arc-list 查看清单
```bash
python scripts/arc_list.py --input out.zip
python scripts/arc_list.py --input out.zip --limit 20
python scripts/arc_list.py --input out.zip --json > entries.json
```
zip 走目录表，加密包也可先看清单再决定要不要密码。

### arc-test 完整性校验
```bash
python scripts/arc_test.py --input out.zip
python scripts/arc_test.py --input secret.zip --password "pw"
```
zip 用 CRC 校验，其余格式逐成员读到底；损坏返回退出码 4。

### arc-info 包信息与统计
```bash
python scripts/arc_info.py --input out.zip
python scripts/arc_info.py --input out.tar.gz --json
```
小文件多的包压缩率可能为负（元数据比内容还大），属正常现象。

## 包内编辑（原包只读，一律产出新包）

### arc-add 追加条目
```bash
python scripts/arc_add.py --input out.zip --inputs new.txt assets/ --output out2.zip
python scripts/arc_add.py --input secret.zip --password pw --inputs a.txt \
  --output secret2.zip --keep-password
```
同名条目自动加 ` (2)`，不静默覆盖。

### arc-remove 删除条目
```bash
python scripts/arc_remove.py --input out.zip --output clean.zip --members "*.tmp" "cache/*"
```

### arc-convert 格式互转
```bash
python scripts/arc_convert.py --input out.zip --output out.tar.gz
python scripts/arc_convert.py --input out.tar.gz --output out.zip --level 9
python scripts/arc_convert.py --input one.zip --output one.txt.gz   # 单成员才行
```

## 加密

### arc-encrypt 加密压缩
```bash
python scripts/arc_encrypt.py --inputs private/ --output secret.zip --password "pw"
python scripts/arc_encrypt.py --inputs private/ --output secret.7z --password "pw" --format 7z
```
装了 `pyzipper` 自动用 AES-256；否则用标准库实现的传统 ZipCrypto（**弱加密，仅防误看**）。输出会打印实际算法，不要对外宣称高强度加密。

### arc-decrypt 带密码解压
```bash
python scripts/arc_decrypt.py --input secret.zip --output plain/ --password "pw"
python scripts/arc_decrypt.py --input secret.zip --output plain/ --password "pw" --repack plain.zip
```
`--repack` 顺手产出无密码包。密码不落盘、不回显。

## 批量

### arc-split 分卷压缩
```bash
python scripts/arc_split.py --inputs photos/ --output parts/photos.zip --size 10M
python scripts/arc_split.py --inputs big/ --output vol.tar.gz --size 500K --format tgz
```
每卷都是**独立可解压**的压缩包，另写 `<前缀>.manifest.json` 记录分卷清单。
`--size` 按原始体积估算分组，压缩后体积不保证精确等于上限。

### arc-merge 合并压缩包
```bash
python scripts/arc_merge.py --inputs parts/photos.manifest.json --output all.zip
python scripts/arc_merge.py --inputs a.zip b.tar.gz --output all.tar.xz
```
重名条目自动加 ` (2)`。传清单文件会自动展开全部分卷。

### arc-batch 批量压缩 / 解压
```bash
python scripts/arc_batch.py --input-dir inbox/ --output-dir packed/ --direction pack --format tgz
python scripts/arc_batch.py --input-dir zips/ --output-dir unpacked/ --direction unpack --password pw
```
每个顶层项各自出一份产物；单份失败不中断整批，末尾统一汇总。

## 依赖检查
```bash
python scripts/actions.py list --json
python scripts/actions.py describe arc-encrypt
python scripts/actions.py check
```
