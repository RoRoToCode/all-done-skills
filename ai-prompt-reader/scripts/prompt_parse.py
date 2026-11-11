"""解释层：把各家写进图片的元数据整理成统一字段。

认得：
  A1111 / Forge      parameters 文本块（正向 + Negative prompt: + 末行 Settings）
  ComfyUI            prompt（API 工作流 JSON），顺着 KSampler 追正负提示词
  NovelAI            Comment 里的 JSON（prompt / uc / steps / seed）
  InvokeAI           invokeai_metadata JSON
  Fooocus / SwarmUI  parameters 里塞 JSON 的变体
其余情况把字段原样列出来，不猜。
"""
import json
import re

from prompt_meta import MetaReadError, read_meta  # noqa: F401  （供动作脚本复用）

_SETTING_KEY = re.compile(r"^[A-Za-z][A-Za-z0-9 _\-/()#.]{0,39}$")

# A1111 末行设置里的常见键，用来判断这一行到底是不是设置行
_KNOWN_KEYS = {"steps", "sampler", "cfg scale", "seed", "size", "model", "model hash",
               "sampler index", "schedule type", "version", "denoising strength"}


def _norm(text):
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _split_settings(line):
    """按逗号拆设置行，引号/括号里的逗号不拆。"""
    parts, cur, depth, quote = [], "", 0, None
    for ch in line:
        if quote:
            cur += ch
            if ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote = ch
            cur += ch
            continue
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth = max(0, depth - 1)
        if ch == "," and depth == 0:
            parts.append(cur)
            cur = ""
            continue
        cur += ch
    parts.append(cur)

    out = []
    for p in parts:
        if ":" not in p:
            continue
        k, v = p.split(":", 1)
        k, v = k.strip(), v.strip().strip('"').strip()
        if not k or not v or not _SETTING_KEY.match(k):
            continue
        out.append((k, v))
    return out


def _is_settings_line(line):
    got = _split_settings(line)
    if len(got) < 2:
        return None
    if not any(k.lower() in _KNOWN_KEYS for k, _ in got):
        return None
    return got


def parse_a1111(text):
    """A1111 / Forge 的 parameters 文本：正向 → Negative prompt: → 末行参数。"""
    lines = _norm(text).split("\n")
    last = None
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip():
            last = i
            break
    if last is None:
        return None

    settings = _is_settings_line(lines[last].strip())
    body_end = last if settings else last + 1
    pos_lines = lines[:body_end]

    neg_at = None
    for i, ln in enumerate(pos_lines):
        if ln.strip().lower().startswith("negative prompt:"):
            neg_at = i
            break

    if neg_at is None:
        positive = "\n".join(pos_lines).strip()
        negative = ""
    else:
        positive = "\n".join(pos_lines[:neg_at]).strip()
        head = pos_lines[neg_at].split(":", 1)[1]
        negative = "\n".join([head] + pos_lines[neg_at + 1:]).strip()

    if not positive and not settings and not negative:
        return None

    params = settings or []
    return {
        "tool": "A1111 / Forge",
        "positive": positive or None,
        "negative": negative or None,
        "params": params,
    }


# ---------------------------------------------------------------- ComfyUI

def _link(v):
    return isinstance(v, list) and len(v) == 2 and isinstance(v[0], str)


def _graph_text(nodes, link, depth=0, seen=None):
    """顺着 conditioning 链路回溯，直到找到 CLIPTextEncode 里的 text。"""
    seen = seen or set()
    if depth > 12 or not _link(link):
        return None
    nid = link[0]
    if nid in seen:
        return None
    seen.add(nid)
    node = nodes.get(nid)
    if not node:
        return None
    ins = node.get("inputs") or {}
    for key in ("text", "text_g", "text_l", "string", "value", "prompt"):
        v = ins.get(key)
        if isinstance(v, str) and v.strip():
            return v
    for v in ins.values():
        if _link(v):
            got = _graph_text(nodes, v, depth + 1, seen)
            if got:
                return got
    return None


def parse_comfy(graph):
    nodes = {k: v for k, v in graph.items()
             if isinstance(v, dict) and v.get("class_type")}
    if not nodes:
        return None

    def cls(n):
        return (n.get("class_type") or "").lower()

    samplers = [(nid, n) for nid, n in nodes.items()
                if "sampler" in cls(n) and isinstance((n.get("inputs") or {}).get("positive"), list)]
    if not samplers:
        samplers = [(nid, n) for nid, n in nodes.items() if "sampler" in cls(n)]
    if not samplers:
        return None
    # 取步数最大的那个，通常才是最终出图的采样器
    samplers.sort(key=lambda p: -int(float((p[1].get("inputs") or {}).get("steps") or 0)))
    nid, sn = samplers[0]
    ins = sn.get("inputs") or {}

    positive = _graph_text(nodes, ins.get("positive")) if _link(ins.get("positive")) else None
    negative = _graph_text(nodes, ins.get("negative")) if _link(ins.get("negative")) else None

    params = []
    seed = ins.get("seed", ins.get("noise_seed"))
    if seed is not None:
        params.append(("Seed", str(seed)))
    if ins.get("steps") is not None:
        params.append(("Steps", str(ins["steps"])))
    if ins.get("cfg") is not None:
        params.append(("CFG scale", str(ins["cfg"])))
    if ins.get("sampler_name"):
        params.append(("Sampler", str(ins["sampler_name"])))
    if ins.get("scheduler"):
        params.append(("Scheduler", str(ins["scheduler"])))
    if ins.get("denoise") is not None:
        params.append(("Denoise", str(ins["denoise"])))
    if ins.get("start_at_step") is not None:
        params.append(("Steps 范围", "%s→%s" % (ins["start_at_step"],
                                              ins.get("end_at_step", "?"))))

    # 模型与尺寸：找 checkpoint / latent 节点
    for _n, n in nodes.items():
        c = cls(n)
        if "checkpointloader" in c or c.endswith("unetloader"):
            name = (n.get("inputs") or {}).get("ckpt_name") or (n.get("inputs") or {}).get("unet_name")
            if name:
                params.append(("Model", str(name)))
                break
    for _n, n in nodes.items():
        c = cls(n)
        if "emptylatent" in c or "latentimage" in c or "emptysd3latent" in c:
            i = n.get("inputs") or {}
            if i.get("width") and i.get("height"):
                params.append(("Size", "%sx%s" % (i["width"], i["height"])))
                break

    params.append(("采样器节点", sn.get("class_type")))
    params.append(("工作流节点数", str(len(nodes))))
    return {"tool": "ComfyUI", "positive": positive, "negative": negative,
            "params": params}


# ---------------------------------------------------------------- JSON 类

def _pick(obj, *keys):
    low = {k.lower(): v for k, v in obj.items()} if isinstance(obj, dict) else {}
    for k in keys:
        if k.lower() in low and low[k.lower()] not in (None, "", []):
            return low[k.lower()]
    return None


def _flat(v):
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False)
    return str(v)


def parse_json_meta(obj, tool):
    """NovelAI / InvokeAI / Fooocus / 通用 JSON 的统一取字段。"""
    model = _pick(obj, "model", "base_model", "ckpt_name", "base model")
    if isinstance(model, dict):
        model = _pick(model, "model_name", "name", "model") or json.dumps(model, ensure_ascii=False)

    params = []
    for label, keys in (
        ("Seed", ("seed", "noise_seed")),
        ("Steps", ("steps",)),
        ("CFG scale", ("cfg_scale", "scale", "guidance_scale", "cfg")),
        ("Sampler", ("sampler", "sampler_name")),
        ("Schedule", ("noise_schedule", "schedule", "scheduler")),
        ("Denoise", ("denoising_strength", "strength", "denoise")),
        ("Size", ("size", "resolution")),
    ):
        v = _pick(obj, *keys)
        if v is None or any(p[0] == label for p in params):
            continue
        # InvokeAI 把采样器写在 scheduler 里，会出现 Sampler 与 Schedule 重复
        if label == "Schedule" and _flat(v) in [p[1] for p in params]:
            continue
        params.append((label, _flat(v)))
    w, h = _pick(obj, "width"), _pick(obj, "height")
    if w and h:
        params.append(("Size", "%sx%s" % (w, h)))
    if model:
        params.insert(0, ("Model", _flat(model)))

    styles = _pick(obj, "styles")
    if styles:
        params.append(("Styles", _flat(styles)))

    return {
        "tool": tool,
        "positive": _pick(obj, "prompt", "positive_prompt", "positive", "Prompt"),
        "negative": _pick(obj, "uc", "negative_prompt", "negative", "Negative Prompt"),
        "params": params,
    }


def _json_or_none(text):
    t = text.strip()
    if not t or t[0] not in "{[":
        return None
    try:
        return json.loads(t)
    except Exception:
        return None


def interpret(meta):
    """返回 {tool, positive, negative, params, notes}。读不出时 tool 为 None。"""
    blocks = meta.get("blocks") or []
    by_name = {}
    for b in blocks:
        by_name.setdefault(b["name"], b["text"])
    names = set(by_name)

    out = {"tool": None, "positive": None, "negative": None, "params": [], "notes": []}

    if "invokeai_metadata" in names:
        obj = _json_or_none(by_name["invokeai_metadata"])
        if isinstance(obj, dict):
            got = parse_json_meta(obj, "InvokeAI")
            got.setdefault("notes", []).append(
                "generation_mode: %s" % _pick(obj, "generation_mode"))
            out.update(got)
            return out

    if "prompt" in names or "workflow" in names:
        graph = _json_or_none(by_name.get("prompt", ""))
        if isinstance(graph, dict) and any(isinstance(v, dict) and v.get("class_type")
                                           for v in graph.values()):
            out.update(parse_comfy(graph))
            if "workflow" in names:
                out["notes"].append("另存有 UI 工作流（workflow），可导入 ComfyUI 复现")
            return out

    # NovelAI：Comment 是 JSON，且带 uc / sampler
    if "Comment" in names:
        obj = _json_or_none(by_name["Comment"])
        if isinstance(obj, dict) and (_pick(obj, "uc") or _pick(obj, "sampler") or _pick(obj, "prompt")):
            sw = by_name.get("Software", "")
            tool = "NovelAI" if "novelai" in sw.lower() or _pick(obj, "uc") else "JSON 元数据"
            out.update(parse_json_meta(obj, tool))
            return out

    for key in ("parameters", "UserComment", "ImageDescription", "Comment"):
        text = by_name.get(key)
        if not text:
            continue
        obj = _json_or_none(text)
        if isinstance(obj, dict):
            tool = "Fooocus / JSON 参数" if _pick(obj, "Prompt", "Styles") else "JSON 元数据"
            if not (_pick(obj, "prompt", "positive_prompt", "Prompt")):
                continue
            out.update(parse_json_meta(obj, tool))
            return out
        got = parse_a1111(text)
        if got:
            out.update(got)
            return out

    # XMP 里偶尔也塞了参数，兜底扫一遍
    if "XMP" in names:
        m = re.search(r"(Negative prompt:.*?)(?:<|$)", by_name["XMP"], re.S)
        if m:
            got = parse_a1111(re.sub(r"<[^>]+>", "", m.group(1)))
            if got:
                got["notes"].append("参数取自 XMP 扩展字段")
                out.update(got)
                return out
    return out


def load(path):
    """读文件 + 解释，返回 (meta, info)。读不出就抛 MetaReadError。"""
    meta = read_meta(path)
    return meta, interpret(meta)


def head_words(text, n=40):
    if not text:
        return ""
    flat = re.sub(r"\s+", " ", text).strip()
    return flat if len(flat) <= n else flat[:n] + "…"
