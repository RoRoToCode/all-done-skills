# 运行环境与排错

## 依赖

**零第三方依赖**：全部动作只用 Python 3.9+ 标准库（`argparse` / `json` / `re` /
`difflib` / `pathlib` / `collections`）。不需要 pip，不需要联网，不需要外部二进制。

`python scripts/actions.py check` 会打印当前解释器路径——这个技能最常见的"跑不起来"
其实是**用错了解释器**（例如宿主内置 Python 与系统 Python 混用），而不是缺包。

## 退出码

| 码 | 含义 | 典型原因 |
| --- | --- | --- |
| 0 | 成功 | — |
| 1 | 动作失败 | 正则无效、切分参数非法、内部异常 |
| 2 | 参数错误 | 缺必填参数、编码名不支持、`--size` 非正数 |
| 3 | 输入输出冲突 | 输入不存在、输出等于输入、输出是目录 |

## 编码处理约定

1. BOM 优先：`utf-8-sig` / `utf-16-le` / `utf-16-be` / `utf-32-*`。
2. 严格 UTF-8 解码成功即认定 UTF-8（不用 `errors="replace"` 试，否则永远"成功"）。
3. 失败则依次尝试 GB18030（GBK/GB2312 超集）、BIG5。
4. 全部失败兜底 Latin-1——它永不报错，因此**结论可能是错的**，重要文件请 `--from` 显式指定。

写盘时用 `newline=""` 原样落 `\n` / `\r\n`，不再做平台转换，避免出现 `\r\r\n`。

## Windows 控制台

输出统一 `ensure_ascii=False`，并在启动时把 stdout/stderr 设为 `errors="replace"`，
避免 cp936 控制台遇到生僻字直接抛 `UnicodeEncodeError`。需要机器读取时用 `-o` 写
JSON 文件，而不是抓 stdout。

## 排错清单

- **`--check` 显示 gb18030 但你确定是 UTF-8**：文件可能含非法字节，用 `--from utf-8 --strict` 看具体位置。
- **替换后文件变大/变小很多**：正则把跨行内容吃掉了，检查是否要加 `--multiline` / 去掉 `--dotall`。
- **diff 全是差异**：两边换行风格不同，先各自 `txt_normalize --newline lf` 再比。
- **切分份数与预期不符**：`--by chars` 按字符计，`--by bytes` 按目标编码字节计（含 BOM 差异），中文一个字符在 UTF-8 占 3 字节。
