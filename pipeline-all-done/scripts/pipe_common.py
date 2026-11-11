# -*- coding: utf-8 -*-
"""流水线全搞定 · 共享层：技能发现、路由、定义校验与 8 个动作的实现。

安全底线：只用参数数组调用家族技能的 scripts/actions.py，绝不拼 shell；
不执行任意命令；产物写入独立运行目录；缺依赖只给本地安装指引。
"""
from __future__ import annotations

import html
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

EXIT_USAGE = 2
EXIT_IO = 3
EXIT_FAIL = 5
EXIT_SAFETY = 7
MAX_STEPS = 30
DANGEROUS = (";", "&&", "||", "`", "$(", "\n")

# 路由关键词表：命中即加分，再叠加技能名/动作名/说明的字符重合度
ROUTE_HINTS = {
    "pdf-workshop": ["pdf", "合并 pdf", "拆分 pdf", "水印", "加密 pdf", "pdf 转", "页码", "脱敏"],
    "ocr-workshop": ["ocr", "识别", "扫描件", "文字识别", "可搜索 pdf"],
    "image-all-done": ["图片", "图像", "抠图", "压缩图", "改尺寸", "image", "exif"],
    "video-all-done": ["视频", "转码", "剪辑", "gif", "抽帧", "video"],
    "audio-all-done": ["音频", "音量", "降噪", "重采样", "audio", "波形"],
    "av-transcribe": ["转写", "语音识别", "字幕", "whisper", "srt", "vtt"],
    "office-all-done": ["docx", "xlsx", "pptx", "word", "excel", "ppt", "office", "转 pdf"],
    "doc-data-extract": ["抽表格", "抽字段", "实体", "文档抽取", "结构化"],
    "archive-all-done": ["压缩包", "解压", "分卷", "zip", "tar", "7z"],
    "ebook-all-done": ["epub", "电子书", "目录", "封面", "calibre"],
    "web-capture": ["网页", "截图", "抓取", "爬虫", "整页", "html 转"],
    "text-all-done": ["编码", "乱码", "去重", "diff", "文本比对", "切分文本", "词频"],
    "ai-prompt-reader": ["提示词", "seed", "采样器", "反读", "prompt"],
    "file-all-done": ["批量重命名", "查重复文件", "目录清单", "文件树", "sha256", "校验文件",
                      "按类型整理", "大文件", "文件比对", "安全复制"],
    "data-all-done": ["csv 转", "json 转", "字段映射", "合并表格", "筛选数据", "数据校验",
                      "schema", "扁平化", "markdown 表格"],
    "pipeline-all-done": ["流水线", "串起来", "编排", "断点续跑", "用哪个技能", "路由"],
    "privacy-all-done": ["脱敏", "敏感信息", "手机号", "身份证", "清除 exif", "元数据清理",
                         "二维码", "条形码"],
}

TEMPLATES = {
    "scan2md": {
        "name": "scan2md",
        "note": "扫描件 → OCR → 文本规范化；参数按子技能实际 CLI 调整",
        "steps": [
            {"skill": "ocr-workshop", "action": "ocr-pdf",
             "args": ["--input", "{{input}}", "-o", "{{step.0.output}}/ocr.md"]},
            {"skill": "text-all-done", "action": "txt-normalize",
             "args": ["{{step.0.output}}/ocr.md", "-o", "{{step.1.output}}/clean.md"]},
        ],
    },
    "web2ebook": {
        "name": "web2ebook",
        "note": "网页 → Markdown → EPUB",
        "steps": [
            {"skill": "web-capture", "action": "web-to-md",
             "args": ["--input", "{{input}}", "-o", "{{step.0.output}}/page.md"]},
            {"skill": "ebook-all-done", "action": "eb-from-md",
             "args": ["--input", "{{step.0.output}}/page.md", "-o", "{{step.1.output}}/book.epub"]},
        ],
    },
    "office2pdf": {
        "name": "office2pdf",
        "note": "Office → PDF → 查看 PDF 信息",
        "steps": [
            {"skill": "office-all-done", "action": "docx-to-pdf",
             "args": ["--input", "{{input}}", "-o", "{{step.0.output}}/doc.pdf"]},
            {"skill": "pdf-workshop", "action": "pdf-info",
             "args": ["--input", "{{step.0.output}}/doc.pdf", "-o", "{{step.1.output}}/info.json"]},
        ],
    },
    "tidy2pdf": {
        "name": "tidy2pdf",
        "note": "整理目录清单 → 转成 CSV；两个新技能串起来的最小示例",
        "steps": [
            {"skill": "file-all-done", "action": "file-list",
             "args": ["{{input}}", "--recursive", "-o", "{{step.0.output}}/inventory.json"]},
            {"skill": "data-all-done", "action": "data-convert",
             "args": ["{{step.0.output}}/inventory.json", "-o",
                      "{{step.1.output}}/inventory.csv", "--to", "csv"]},
        ],
    },
}


def main_guard():
    """输出编码兜底：被管道/重定向捕获时统一按 UTF-8 写出，否则父进程按 UTF-8
    解码会得到一串替换符；直接接终端时不动编码，免得老式 cp936 控制台显示异常。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            if stream.isatty():
                stream.reconfigure(errors="replace")
            else:
                stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass


def fail(message, code=EXIT_USAGE):
    print(message, file=sys.stderr)
    raise SystemExit(code)


def emit(payload, code=0):
    print(json.dumps(payload, ensure_ascii=False))
    return code


def w(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))
    return path


def read_json(path):
    p = Path(path)
    if not p.is_file():
        fail("文件不存在：%s" % p, EXIT_IO)
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except ValueError as exc:
        fail("JSON 解析失败：%s（%s）" % (p, exc), EXIT_USAGE)


def pick_definition(data):
    """模板文件是 {"名字": 定义} 的集合，直接传给 run/validate 会因为取不到 steps 而报错。

    只有一个模板时自动取出；多个模板时明确告知可选名字，避免用户对着
    “steps 必须是非空数组” 猜原因。
    """
    if not isinstance(data, dict) or isinstance(data.get("steps"), list):
        return data
    named = {k: v for k, v in data.items()
             if isinstance(v, dict) and isinstance(v.get("steps"), list)}
    if len(named) == 1:
        return list(named.values())[0]
    if len(named) > 1:
        fail("这个定义文件里有 %d 个流水线（%s），请把要用的一部单独保存成文件"
             % (len(named), "、".join(sorted(named))), EXIT_USAGE)
    return data


def deliver(ns, payload, text=None):
    out = getattr(ns, "output", None)
    if not out:
        return emit(payload) if text is None else print(text) or 0
    p = Path(out).resolve()
    w(p, text if text is not None else json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    return emit({"output": str(p), "bytes": p.stat().st_size})


def skills_root(ns):
    raw = getattr(ns, "skills_root", None) or os.environ.get("ALLDONE_SKILLS_ROOT")
    return Path(raw).expanduser().resolve() if raw else (Path.home() / ".workbuddy" / "skills")


def catalog(root):
    """读每个技能的 assets/actions.json，构造技能 → 动作表。零副作用。"""
    out = {}
    if not root.is_dir():
        return out
    for d in sorted(root.iterdir()):
        reg = d / "assets" / "actions.json"
        if not d.is_dir() or not reg.is_file():
            continue
        try:
            data = json.loads(reg.read_text(encoding="utf-8-sig"))
            out[d.name] = {
                "version": data.get("version", ""),
                "display_name": data.get("display_name", d.name),
                "entry": str(d / "scripts" / "actions.py"),
                "actions": [{"id": a["id"], "name": a.get("name", ""),
                             "desc": a.get("desc", "")} for a in data.get("actions", [])],
            }
        except (ValueError, OSError):
            continue
    return out


def action_exists(cat, skill, action):
    return skill in cat and any(a["id"] == action for a in cat[skill]["actions"])


# ---------------------------------------------------------------- 8 个动作

def run_pipe_list(ns):
    root = skills_root(ns)
    cat = catalog(root)
    lines = ["技能根目录: %s" % root, "共 %d 个技能 / %d 个动作"
             % (len(cat), sum(len(v["actions"]) for v in cat.values()))]
    for name, item in cat.items():
        lines.append("  %-20s v%-8s %2d 动作" % (name, item["version"], len(item["actions"])))
        for a in item["actions"]:
            lines.append("      %-20s %s" % (a["id"], a["name"]))
    payload = {"root": str(root), "skills": cat,
               "skill_count": len(cat),
               "action_count": sum(len(v["actions"]) for v in cat.values())}
    if ns.format == "table":
        return deliver(ns, payload, "\n".join(lines) + "\n")
    return deliver(ns, payload)


def run_pipe_route(ns):
    root = skills_root(ns)
    cat = catalog(root)
    text = ns.text.lower()
    scores = []
    for name, item in cat.items():
        skill_score = 0
        for kw in ROUTE_HINTS.get(name, []):
            if kw.lower() in text:
                skill_score += 12
        if name.replace("-all-done", "").replace("-workshop", "") in text:
            skill_score += 8
        for a in item["actions"]:
            score = skill_score
            blob = (a["id"] + " " + a["name"] + " " + a["desc"]).lower()
            for token in re.findall(r"[\u4e00-\u9fff]{2,}|[a-z]{3,}", text):
                if token in blob:
                    score += 4
            if a["id"].replace("-", " ") in text:
                score += 10
            if score > 0:
                scores.append({"skill": name, "action": a["id"], "name": a["name"],
                               "score": score, "reason": "关键词匹配（技能 %d 分）" % skill_score})
    scores.sort(key=lambda x: -x["score"])
    hits = scores[:max(1, ns.top)]
    return deliver(ns, {"query": ns.text, "root": str(root),
                        "candidates": hits, "count": len(hits),
                        "note": "只给建议，不自动执行；请人工确认后使用"})


def run_pipe_template(ns):
    data = TEMPLATES if ns.name == "all" else {ns.name: TEMPLATES[ns.name]}
    if ns.skills_root or os.environ.get("ALLDONE_SKILLS_ROOT"):
        root = skills_root(ns)
        cat = catalog(root)
        for tpl in data.values():
            tpl["unavailable"] = [
                "%s/%s" % (s["skill"], s["action"])
                for s in tpl["steps"] if not action_exists(cat, s["skill"], s["action"])]
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    return deliver(ns, {"templates": list(data), "definitions": data}, text)


def validate_definition(definition, cat, require_entry=True):
    problems = []
    if not isinstance(definition, dict):
        return ["定义必须是 JSON 对象"]
    steps = definition.get("steps")
    if not isinstance(steps, list) or not steps:
        return ["steps 必须是非空数组"]
    if len(steps) > MAX_STEPS:
        problems.append("步骤数 %d 超过上限 %d" % (len(steps), MAX_STEPS))
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            problems.append("步骤 %d 不是对象" % i)
            continue
        skill, action = step.get("skill", ""), step.get("action", "")
        if not skill or not action or "/" in skill or ".." in skill or "\\" in skill:
            problems.append("步骤 %d 的 skill/action 非法" % i)
            continue
        if skill not in cat:
            problems.append("步骤 %d：技能未安装 %s" % (i, skill))
        elif not action_exists(cat, skill, action):
            problems.append("步骤 %d：动作不存在 %s/%s" % (i, skill, action))
        elif require_entry and not Path(cat[skill]["entry"]).is_file():
            problems.append("步骤 %d：缺统一入口 %s" % (i, cat[skill]["entry"]))
        args = step.get("args", [])
        if not isinstance(args, list) or not all(isinstance(x, str) for x in args):
            problems.append("步骤 %d 的 args 必须是字符串数组" % i)
            continue
        for arg in args:
            if any(token in arg for token in DANGEROUS):
                problems.append("步骤 %d 参数含 shell 语法：%s" % (i, arg[:60]))
            for m in re.finditer(r"\{\{step\.(\d+)\.output\}\}", arg):
                if int(m.group(1)) > i:
                    problems.append("步骤 %d 引用了未来步骤：%s" % (i, arg[:60]))
            for m in re.finditer(r"\{\{([^}]+)\}\}", arg):
                token = m.group(1)
                if token != "input" and not re.fullmatch(r"step\.\d+\.output", token):
                    problems.append("步骤 %d 的变量不支持：%s" % (i, token))
    return problems


def run_pipe_validate(ns):
    definition = pick_definition(read_json(ns.input))
    cat = catalog(skills_root(ns))
    problems = validate_definition(definition, cat)
    name = definition.get("name", "") if isinstance(definition, dict) else ""
    payload = {"definition": str(ns.input), "root": str(skills_root(ns)),
               "name": name,
               "steps": len(definition.get("steps", [])) if isinstance(definition, dict) else 0,
               "problems": problems, "valid": not problems}
    rc = deliver(ns, payload)
    return EXIT_FAIL if problems else rc


def substitute(arg, pipeline_input, outputs):
    # 步骤子进程的 cwd 是 run_dir，用户给的相对路径必须先折算成绝对路径，
    # 否则 {{input}} 会指向 run_dir 下并不存在的文件。
    src = os.path.abspath(pipeline_input) if pipeline_input else ""
    arg = arg.replace("{{input}}", src)

    def repl(m):
        idx = int(m.group(1))
        return str(outputs[idx]) if idx < len(outputs) else m.group(0)

    return re.sub(r"\{\{step\.(\d+)\.output\}\}", repl, arg)


def step_output_dir(run_dir, index, action):
    d = run_dir / "steps" / ("%02d-%s" % (index + 1, action))
    d.mkdir(parents=True, exist_ok=True)
    return d


def execute_steps(run_dir, definition, root, cat, ns, start_index=0):
    """执行（或续跑）步骤，逐步更新 manifest.json 与 state.json。"""
    steps = definition["steps"]
    manifest_path = run_dir / "manifest.json"
    state_path = run_dir / "state.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else []
    manifest = manifest[:start_index]
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.is_file() else {}
    outputs = [step_output_dir(run_dir, i, s["action"]) for i, s in enumerate(steps)]
    pipe_input = getattr(ns, "pipeline_input", None) or state.get("input")
    failed = []
    commands = []

    for i in range(start_index, len(steps)):
        step = steps[i]
        entry = Path(cat[step["skill"]]["entry"])
        args = [substitute(a, pipe_input, outputs) for a in step.get("args", [])]
        cmd = [sys.executable, str(entry), "run", step["action"]] + args
        commands.append({"index": i + 1, "cmd": cmd})
        if getattr(ns, "dry_run", False):
            manifest.append({"index": i + 1, "skill": step["skill"],
                             "action": step["action"], "dry_run": True,
                             "output_dir": str(outputs[i])})
            continue
        t0 = time.time()
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True,
                                  encoding="utf-8", errors="replace",
                                  timeout=getattr(ns, "timeout", 1800), cwd=str(run_dir))
            rc, out, err = proc.returncode, proc.stdout, proc.stderr
        except subprocess.TimeoutExpired:
            rc, out, err = 124, "", "超时 %s 秒" % getattr(ns, "timeout", 1800)
        except OSError as exc:
            rc, out, err = 126, "", str(exc)
        record = {"index": i + 1, "skill": step["skill"], "action": step["action"],
                  "cmd": cmd, "returncode": rc, "seconds": round(time.time() - t0, 3),
                  "stdout_tail": out[-800:], "stderr_tail": err[-800:],
                  "output_dir": str(outputs[i])}
        manifest.append(record)
        if rc != 0:
            failed.append({"index": i + 1, "action": step["action"], "returncode": rc,
                           "error": err[-200:] or "未安装依赖或参数不匹配"})
        state = {"name": definition.get("name", "pipeline"), "input": pipe_input,
                 "root": str(root), "completed": i + 1 if rc == 0 else i,
                 "total": len(steps), "failed": failed,
                 "updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        w(state_path, json.dumps(state, ensure_ascii=False, indent=2) + "\n")
        w(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
        if rc != 0 and getattr(ns, "on_error", "stop") == "stop":
            break
    if getattr(ns, "dry_run", False):
        w(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return {"commands": commands, "failed": failed, "executed": len(manifest) - start_index,
            "state": state}


def new_run_dir(ns, definition):
    parent = Path(ns.workdir).resolve() if ns.workdir else Path.cwd() / "pipeline-runs"
    parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    name = re.sub(r"[^\w\-]", "-", definition.get("name", "pipeline"))[:40]
    d = parent / ("%s-%s" % (name, stamp))
    i = 2
    while d.exists():
        d = parent / ("%s-%s-%d" % (name, stamp, i))
        i += 1
    d.mkdir()
    return d


def run_pipe_run(ns):
    definition = pick_definition(read_json(ns.input))
    root = skills_root(ns)
    cat = catalog(root)
    problems = validate_definition(definition, cat)
    if problems:
        return emit({"valid": False, "problems": problems}, EXIT_FAIL)
    if ns.dry_run:
        outputs = [Path("<step%d-output>" % (i + 1)) for i in range(len(definition["steps"]))]
        commands = [[sys.executable, cat[s["skill"]]["entry"], "run", s["action"]] +
                    [substitute(a, ns.pipeline_input, outputs) for a in s.get("args", [])]
                    for s in definition["steps"]]
        return emit({"valid": True, "dry_run": True, "commands": commands,
                     "steps": len(commands), "note": "未创建任何目录，未执行任何动作"})
    run_dir = new_run_dir(ns, definition)
    w(run_dir / "definition.json", json.dumps(definition, ensure_ascii=False, indent=2) + "\n")
    w(run_dir / "state.json", json.dumps(
        {"name": definition.get("name", "pipeline"), "input": ns.pipeline_input,
         "root": str(root), "completed": 0, "total": len(definition["steps"]),
         "failed": []}, ensure_ascii=False, indent=2) + "\n")
    info = execute_steps(run_dir, definition, root, cat, ns, 0)
    return emit({"run_dir": str(run_dir), "name": definition.get("name", "pipeline"),
                 "steps": len(definition["steps"]), "executed": info["executed"],
                 "failed": info["failed"], "manifest": str(run_dir / "manifest.json"),
                 "state": str(run_dir / "state.json"),
                 "ok": not info["failed"]}, EXIT_FAIL if info["failed"] else 0)


def run_pipe_resume(ns):
    p = Path(ns.input).resolve()
    run_dir = p if p.is_dir() else p.parent
    state_path = run_dir / "state.json"
    def_path = run_dir / "definition.json"
    if not state_path.is_file() or not def_path.is_file():
        fail("运行目录缺 state.json / definition.json：%s" % run_dir, EXIT_IO)
    state = read_json(state_path)
    definition = read_json(def_path)
    root = skills_root(ns)
    cat = catalog(root)
    problems = validate_definition(definition, cat)
    if problems:
        return emit({"valid": False, "problems": problems}, EXIT_FAIL)
    start = int(state.get("completed", 0))
    if start >= len(definition["steps"]):
        return emit({"run_dir": str(run_dir), "completed": start,
                     "note": "所有步骤已完成，无需续跑"})
    ns.on_error = "stop"
    ns.dry_run = False
    ns.pipeline_input = getattr(ns, "pipeline_input", None) or state.get("input")
    info = execute_steps(run_dir, definition, root, cat, ns, start)
    return emit({"run_dir": str(run_dir), "resumed_from": start,
                 "executed": info["executed"], "failed": info["failed"],
                 "ok": not info["failed"]}, EXIT_FAIL if info["failed"] else 0)


def _load_run(run_dir):
    manifest = read_json(run_dir / "manifest.json") if (run_dir / "manifest.json").is_file() else []
    state = read_json(run_dir / "state.json") if (run_dir / "state.json").is_file() else {}
    return manifest, state


def run_pipe_status(ns):
    run_dir = Path(ns.input).resolve()
    if not run_dir.is_dir():
        fail("运行目录不存在：%s" % run_dir, EXIT_IO)
    manifest, state = _load_run(run_dir)
    steps = [{"index": m.get("index"), "action": m.get("action"),
              "returncode": m.get("returncode"), "seconds": m.get("seconds"),
              "output_dir": m.get("output_dir")} for m in manifest]
    return deliver(ns, {"run_dir": str(run_dir), "name": state.get("name", ""),
                        "completed": state.get("completed", 0),
                        "total": state.get("total", len(manifest)),
                        "failed": state.get("failed", []), "steps": steps})


def run_pipe_report(ns):
    run_dir = Path(ns.input).resolve()
    if not run_dir.is_dir():
        fail("运行目录不存在：%s" % run_dir, EXIT_IO)
    manifest, state = _load_run(run_dir)
    payload = {"run_dir": str(run_dir), "name": state.get("name", ""),
               "completed": state.get("completed", 0), "total": state.get("total", 0),
               "failed": state.get("failed", []), "steps": manifest}
    if ns.format == "json":
        return deliver(ns, payload)
    lines = ["# 流水线报告：%s" % state.get("name", "pipeline"), "",
             "- 运行目录：`%s`" % run_dir,
             "- 完成步骤：%s / %s" % (state.get("completed", 0), state.get("total", 0)),
             "- 失败：%d" % len(state.get("failed", [])), "",
             "| # | 技能 | 动作 | 返回码 | 耗时(s) | 产物目录 |", "|---|---|---|---|---|---|"]
    for m in manifest:
        lines.append("| %s | %s | %s | %s | %s | `%s` |"
                     % (m.get("index"), m.get("skill"), m.get("action"),
                        m.get("returncode", "-"), m.get("seconds", "-"),
                        m.get("output_dir", "")))
    if state.get("failed"):
        lines += ["", "## 失败清单", ""]
        lines += ["- 步骤 %s `%s`：rc=%s %s" % (f.get("index"), f.get("action"),
                                                f.get("returncode"), f.get("error", ""))
                  for f in state["failed"]]
    md = "\n".join(lines) + "\n"
    if ns.format == "md":
        return deliver(ns, payload, md)
    body = "".join("<tr><td>%s</td></tr>" % html.escape(line.strip("|").replace("|", " | "))
                   for line in lines[7:] if line.startswith("|") and "---" not in line)
    htm = ("<!doctype html><meta charset='utf-8'><title>流水线报告</title>"
           "<style>body{font:14px/1.6 system-ui;margin:2rem;color:#222}"
           "table{border-collapse:collapse}td,th{border:1px solid #ddd;padding:4px 8px}"
           "code{background:#f5f5f5}</style><h1>流水线报告：%s</h1>"
           "<p>完成 %s / %s 步，失败 %d</p><table>%s</table>"
           % (html.escape(state.get("name", "")), state.get("completed", 0),
              state.get("total", 0), len(state.get("failed", [])), body))
    return deliver(ns, payload, htm)
