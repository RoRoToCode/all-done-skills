# 运行环境与排错

## 依赖

**零第三方依赖**：全部动作只用 Python 3.9+ 标准库（`subprocess` / `json` /
`argparse` / `pathlib` / `re` / `datetime`）。不需要 pip，不需要联网，不需要外部二进制。
被编排技能自身的依赖（ffmpeg / PyMuPDF / OCR 引擎等）仍需各自安装。

`python scripts/actions.py check` 会打印当前解释器路径；执行步骤时**强制使用当前解释器**
调用子技能，避免「包装在 A、技能用 B 解释器跑」导致的凭空失败。

## 退出码

| 码 | 含义 | 典型原因 |
| --- | --- | --- |
| 0 | 成功 | — |
| 2 | 参数错误 | 定义 JSON 非法、模板名不存在、动作 id 未注册 |
| 3 | 输入输出冲突 | 定义文件不存在、运行目录无法创建、变量指向自身 |
| 5 | 步骤失败 | 子技能返回非零、超时、产物缺失 |
| 7 | 安全拒绝 | 步骤含非法技能名、路径越界、试图拼接 shell 语法 |

## 目录结构

```
<workdir>/<运行名>/
  definition.json      本次使用的流水线定义快照
  steps/01-<id>/       每步独立输出目录
  manifest.json        步骤命令、退出码、耗时、stdout 摘要
  state.json           完成状态（供 pipe_resume 使用）
  report.md            可选，由 pipe_report 生成
```

## 排错清单

- **`pipe_list` 看不到某个技能**：确认它已安装到 `~/.workbuddy/skills`，或用 `--skills-root` 指到正确目录。
- **步骤全失败且提示缺脚本**：子技能的 `scripts/actions.py` 不在预期位置，先在该技能目录跑 `actions.py list`。
- **变量没替换**：只能用 `{{input}}` 与 `{{step.N.output}}`，N 不得大于当前步骤序号。
- **续跑从头开始**：`state.json` 被删或运行目录被改名，本技能不会猜测已完成步骤。
