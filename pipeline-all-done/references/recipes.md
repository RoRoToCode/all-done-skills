命令都在技能根目录执行；`<in>` / `<out>` 换成实际路径，路径含空格要加引号。

## 1. 先看本机有什么

```bash
python scripts/pipe_list.py --format table
python scripts/pipe_route.py "把扫描件识别成可搜索 PDF" --top 3
python scripts/pipe_list.py -o catalog.json --format json
```

`pipe_list` 直接读各技能的 `assets/actions.json`，家族新增技能后无需改本技能。

## 2. 从模板改出一条流水线

```bash
python scripts/pipe_template.py scan2md -o myflow.json
python scripts/pipe_validate.py myflow.json
python scripts/pipe_run.py myflow.json --input samples/ --dry-run
```

内置模板：`scan2md`（扫描件→OCR→Markdown）、`web2ebook`（网页→PDF→EPUB 前置）、
`office2pdf`（Office 批量转 PDF）、`tidy2pdf`（整理目录→图片转 PDF 前置）。
模板里带 `{{input}}` 占位，执行时用 `--input` 填。

## 3. 正式执行与断点续跑

```bash
python scripts/pipe_run.py myflow.json --input samples/ --workdir runs/ --on-error continue
python scripts/pipe_status.py runs/<运行目录>
python scripts/pipe_resume.py runs/<运行目录>
python scripts/pipe_report.py runs/<运行目录> -o report.md --format md
```

每步一个独立目录，`manifest.json` 记录命令、退出码、耗时与 stdout；`state.json`
标记已完成步骤，`pipe_resume` 从第一个未完成处继续。

## 4. 自定义步骤

```json
{
  "name": "scan-to-markdown",
  "steps": [
    {"skill": "ocr-workshop", "action": "ocr-batch",
     "args": ["--input", "{{input}}", "--output", "{{step.0.output}}/txt"]},
    {"skill": "text-all-done", "action": "txt-normalize",
     "args": ["--input", "{{step.0.output}}/txt", "--output", "{{step.1.output}}/clean.txt"]}
  ]
}
```

下标从 0 开始，`{{step.N.output}}` 表示第 N 步的输出目录，N 可以是当前步骤
（把产物写进自己的目录），但**不能指向更晚的步骤**。

## 组合流水线

```bash
python scripts/pipe_template.py scan2md -o flow.json && \
python scripts/pipe_validate.py flow.json && \
python scripts/pipe_run.py flow.json --input scans/ --workdir runs/
```
