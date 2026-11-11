---
name: "pipeline-all-done"
display_name: "流水线全搞定"
display_name_en: "Pipelines, All Done"
description: "Local orchestration toolkit for the All Done skill family - discover installed skills and actions, route a request to the right skill, generate and validate pipeline definitions, run multi-skill workflows with isolated step outputs and a manifest, resume from checkpoints, inspect status and render reports. Triggers include 流水线全搞定 / 编排工具箱 / /pipe / 串起来 / 一键处理 / 批量流程 / 技能路由 / 断点续跑 / 流水线报告 / 哪个技能. Pure stdlib, fully local, no shell execution, no per-step confirmation by default."
description_zh: "本机跨技能编排技能：发现已安装技能与动作 · 一句话路由到合适技能 · 生成并校验流水线定义 · 按步骤调用各技能统一入口 · 每步独立产物目录 + manifest · 断点续跑 · 状态查看 · JSON/Markdown/HTML 报告。说「流水线全搞定」或输入 /pipe 即用，纯标准库零依赖，全程本地不上传，默认无需逐项确认（不执行任意命令、产物不覆盖输入）。"
description_en: "Local orchestration toolkit for the All Done family - discover skills/actions, route a request, generate and validate pipeline definitions, run steps with isolated outputs and manifest, resume, inspect status and render reports. Triggers: 流水线全搞定 / /pipe / workflow / which skill / resume. Pure stdlib, fully local, no shell execution, no per-step confirmation by default."
version: "1.4.1"
agent_created: true
---

# 流水线全搞定

本机跨技能编排技能。8 项动作统一从 `python scripts/actions.py` 调用，动作清单的唯一数据源是 `assets/actions.json`。**全部动作只用 Python 标准库**：不启动 shell、不执行任意命令，只以参数数组调用家族里各技能的 `scripts/actions.py run <id>`。技能根目录默认 `~/.workbuddy/skills`，可用 `--skills-root` 或环境变量 `ALLDONE_SKILLS_ROOT` 覆盖。

## 统一入口

```bash
python scripts/actions.py list                  # 全部动作
python scripts/actions.py list --json           # 机器可读清单
python scripts/actions.py describe <id>         # 参数、依赖、备注
python scripts/actions.py check                 # 解释器 + 依赖状态
python scripts/actions.py run <id> --input <in> --output <out>
python scripts/actions.py online <id>           # 在线替代（本技能一律返回「无」）
```

`run` 把其余参数原样透传给 `scripts/<id 下划线>.py`；也可直接调用单个脚本。
精细参数见 `references/recipes.md`；格式矩阵、退出码、依赖与排错见
`references/toolchain.md`。动作清单的唯一数据源是 `assets/actions.json`。

## 动作 id

- 发现与路由：`pipe-list` `pipe-route` `pipe-template`
- 定义与执行：`pipe-validate` `pipe-run` `pipe-resume`
- 状态与报告：`pipe-status` `pipe-report`

## 默认无需逐项确认

本技能**默认无需逐项确认**：不对每个文件、每一步操作弹确认，直接执行到出结果。

- 输出命名、重名避让（` (2)` / `-2`）、可选依赖降级、批量单份失败不中断，全部自动决策。
- 依赖缺失不询问、不联网：只给一条本地安装指引，不伪装成功。
- **唯一不放行的是安全底线**：输出不得覆盖输入、不删除或移动用户原文件、不执行任意命令、不上传任何云端或第三方服务器。
- 预览类动作（`--dry-run` / 默认预览）在不落盘的前提下给出完整计划，落盘需显式 `--apply` 或 `-o`。

## 约束

- 全程本地处理，流水线定义与中间产物不上传任何云端或第三方服务，**不提供在线兜底**（`online` 全为 null）。
- **只调用白名单入口**：步骤执行固定为 `[当前解释器, <技能>/scripts/actions.py, run, <动作 id>, ...参数]`，不经过 shell、不支持任意命令、不解析 `;`、`&&`、管道等语法。
- 流水线定义必须是 JSON：`{"name": "...", "steps": [{"skill": "...", "action": "...", "args": ["--input", "{{input}}"]}]}`；`{{input}}` 指向初始输入，`{{step.N.output}}` 指向第 N 步的输出目录。
- 每步写入独立目录 `<workdir>/steps/01-<id>/`，产物不覆盖输入；运行目录已存在时自动避让为 `-2`/`-3`。
- `--on-error stop` 为默认；`continue` 时单步失败不中断，全部失败仍返回非零。缺依赖只给本地安装指引，不伪装成功、不联网安装。
- 步骤数上限 30、单步超时默认 30 分钟；`pipe-validate` 会拒绝不存在的技能/动作、未知变量引用与循环引用。

## 路由边界

- 本技能只做**编排与路由**，不重新实现任何文件处理能力，也不解析文件内容。
- 具体处理分别走 `pdf-workshop` / `ocr-workshop` / `image-all-done` / `video-all-done` / `audio-all-done` / `av-transcribe` / `office-all-done` / `doc-data-extract` / `archive-all-done` / `ebook-all-done` / `web-capture` / `text-all-done` / `file-all-done` / `data-all-done` / `privacy-all-done`。
- 定时任务、并行调度、分布式队列与云端工作流不在范围内；一次只跑一条本地流水线。

## 交付

给出运行目录、每步状态与产物路径、失败清单与报告路径；依赖缺失时附一条本地安装指引，不输出功能清单或操作说明。

## 免责声明
- **本地优先**：本技能全程在本机运行，原始文件不会上传任何云端或第三方服务器；本技能不提供第三方在线替代方案，缺依赖时只给出本地安装指引。
- **结果仅供参考**：流水线只是把各技能按定义串起来，正确性取决于每一步自身；上游产物缺失、格式不匹配或依赖未安装都会导致步骤失败。路由建议基于关键词匹配，可能给出多个候选，需人工确认后使用；断点续跑依赖 manifest/state 文件完整，手工删除产物目录后无法续跑。重要资料请先备份并核对每步产物。
- **依赖与第三方组件**：本技能只使用 Python 标准库；被编排的各技能所需第三方组件由使用者自行安装并各自适用其独立许可，相关组件的下载、许可与版权归各自作者所有。第三方组件均由使用者自行安装并各自适用其独立许可，本技能不分发其二进制、库或模型权重；完整清单与许可提示见 THIRD-PARTY.md。
- **按现状提供**：本技能以 MIT 许可按「现状」提供，不提供任何明示或暗示的担保（含适用性、准确性、无中断、无损害）。因使用本技能产生的任何直接或间接损失，由使用者自行承担；处理前请自行备份原始文件。
