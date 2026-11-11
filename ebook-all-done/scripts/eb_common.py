# -*- coding: utf-8 -*-
"""电子书动作共享工具：EPUB2 / EPUB3 读写、目录、Markdown↔XHTML、打包、浏览器 PDF。

设计要点：
  * 只用标准库。EPUB 就是一个 ZIP，mimetype 必须第一条且 STORED（不压缩）。
  * 读：container.xml -> OPF -> manifest/spine -> XHTML；目录优先 nav.xhtml，其次 NCX。
  * 写：一律另存新文件，不原地改源文件；重建式动作生成规范 EPUB3 + 兼容 NCX。
"""
import datetime
import html as html_lib
import html.entities
import json
import os
import pathlib
import posixpath
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import zipfile
from html.parser import HTMLParser
from xml.etree import ElementTree as ET

OPF_NS = "http://www.idpf.org/2007/opf"
DC_NS = "http://purl.org/dc/elements/1.1/"
NCX_NS = "http://www.daisy.org/z3986/2005/ncx/"
CONTAINER_NS = "urn:oasis:names:tc:opendocument:xmlns:container"
XHTML_NS = "http://www.w3.org/1999/xhtml"

EXIT_USAGE = 2
EXIT_IO = 3
EXIT_FORMAT = 4
EXIT_FAIL = 5

MIME = {
    ".xhtml": "application/xhtml+xml", ".html": "application/xhtml+xml",
    ".htm": "application/xhtml+xml", ".ncx": "application/x-dtbncx+xml",
    ".css": "text/css", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".png": "image/png", ".gif": "image/gif", ".webp": "image/webp",
    ".svg": "image/svg+xml", ".bmp": "image/bmp", ".ttf": "font/ttf",
    ".otf": "font/otf", ".woff": "font/woff", ".woff2": "font/woff2",
    ".mp3": "audio/mpeg", ".mp4": "video/mp4", ".js": "text/javascript",
    ".opf": "application/oebps-package+xml", ".xml": "application/xml",
}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp"}
FONT_EXT = {".ttf", ".otf", ".woff", ".woff2"}
STYLE_EXT = {".css"}
VOID_TAGS = {"br", "hr", "img", "input", "meta", "link", "area", "base",
             "col", "embed", "param", "source", "track", "wbr"}


def setup_stdout():
    """Windows 控制台默认 GBK，统一成 UTF-8，避免中文输出炸掉。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def die(msg, code=EXIT_FAIL):
    sys.stderr.write(str(msg).rstrip() + "\n")
    sys.exit(code)


def local(tag):
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag.split(":")[-1]


def decode(data, encoding=None):
    if encoding:
        return data.decode(encoding, errors="replace")
    for enc in ("utf-8-sig", "utf-8", "gb18030", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def read_source(path, encoding=None):
    with open(path, "rb") as f:
        return decode(f.read(), encoding)


# ---------------------------------------------------------------------------
# 默认无需逐项确认：重名自动改名；只有安全底线不放行
# ---------------------------------------------------------------------------
CONFLICT_MODE = os.environ.get("EBOOK_ON_CONFLICT", "rename").lower()


def set_conflict_mode(mode):
    global CONFLICT_MODE
    CONFLICT_MODE = (mode or "rename").lower()


def conflict_path(target, mode=None):
    """文件输出：已存在时自动改名 ` (2)`；overwrite 原样，skip 返回 None。"""
    target = str(target)
    m = (mode or CONFLICT_MODE).lower()
    if m == "overwrite" or not os.path.exists(target):
        return target
    if m == "skip":
        return None
    stem, ext = os.path.splitext(target)
    n = 2
    while os.path.exists("%s (%d)%s" % (stem, n, ext)):
        n += 1
    return "%s (%d)%s" % (stem, n, ext)


def conflict_dir(path, mode=None):
    """目录输出：已存在且非空时自动改名；空目录直接复用。"""
    p = str(path)
    m = (mode or CONFLICT_MODE).lower()
    if m == "overwrite" or not os.path.isdir(p) or not os.listdir(p):
        return p
    if m == "skip":
        return None
    n = 2
    while os.path.exists("%s (%d)" % (p, n)):
        n += 1
    return "%s (%d)" % (p, n)


def resolve_display(path):
    """result() 用：把用户给的路径校正成实际写入的（可能已自动改名）路径。"""
    p = str(path)
    if os.path.exists(p) or p == "None":
        return p
    stem, ext = os.path.splitext(p)
    latest = None
    n = 2
    while os.path.exists("%s (%d)%s" % (stem, n, ext)):
        latest = "%s (%d)%s" % (stem, n, ext)
        n += 1
    if latest:
        return latest
    n = 2
    while os.path.isdir("%s (%d)" % (p, n)):
        latest = "%s (%d)" % (p, n)
        n += 1
    return latest or p


def no_overwrite(inp, out):
    if inp and out and os.path.abspath(str(inp)) == os.path.abspath(str(out)):
        die("输出不得等于输入：%s" % inp, EXIT_IO)


def ensure_parent(out):
    d = os.path.dirname(os.path.abspath(str(out)))
    if d:
        os.makedirs(d, exist_ok=True)


def require_file(path):
    if not path or not os.path.isfile(path):
        die("输入文件不存在：%s" % path, EXIT_IO)


LAST_OUTPUT = None
LAST_REQUESTED = None


def record_output(requested, actual):
    """记住本次实际写入的路径，让 result() 显示自动改名后的真实产物。"""
    global LAST_OUTPUT, LAST_REQUESTED
    LAST_REQUESTED = str(requested)
    LAST_OUTPUT = str(actual) if actual else None


def result(path, **info):
    shown = str(path)
    if LAST_REQUESTED == shown and LAST_OUTPUT:
        shown = LAST_OUTPUT
    else:
        shown = resolve_display(path)
    parts = ["已保存 %s" % shown]
    for k, v in info.items():
        if v is not None:
            parts.append("%s=%s" % (k, v))
    print("  ".join(parts))


def json_dump(path, obj):
    original = str(path)
    path = conflict_path(path)
    if path is None:
        print("已跳过（输出已存在，EBOOK_ON_CONFLICT=skip）：%s" % original)
        return original
    record_output(original, path)
    ensure_parent(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return path


def xml_escape(s):
    return html_lib.escape(str(s), quote=True)


def safe_name(s, maxlen=60):
    s = re.sub(r"[\\/:*?\"<>|\r\n\t]+", "_", str(s)).strip(" .")
    return (s[:maxlen] or "chapter")


def is_external(href):
    h = (href or "").strip().lower()
    return (not h or h.startswith(("http:", "https:", "mailto:", "data:",
                                  "javascript:", "ftp:", "#")))


def norm_href(base_zip_path, href):
    """把相对 href 解析成 ZIP 内成员路径；外部链接返回 None。"""
    if is_external(href):
        return None
    clean = urllib.parse.unquote(href.split("#", 1)[0].split("?", 1)[0].strip())
    if not clean:
        return None
    base_dir = posixpath.dirname(base_zip_path)
    return posixpath.normpath(posixpath.join(base_dir, clean)).lstrip("/")


def ext_of(name):
    return posixpath.splitext(name)[1].lower()


def mime_of(name):
    return MIME.get(ext_of(name), "application/octet-stream")


def word_count(text):
    cjk = len(re.findall(r"[\u3400-\u9fff]", text or ""))
    latin = len(re.findall(r"[A-Za-z0-9]+(?:['’-][A-Za-z0-9]+)*", text or ""))
    return cjk + latin


# ---------------------------------------------------------------------------
# EPUB 读取
# ---------------------------------------------------------------------------
class Epub:
    """只读视图：解析 container / OPF / manifest / spine / 目录 / 资源。"""

    def __init__(self, path):
        self.path = str(path)
        require_file(self.path)
        if not zipfile.is_zipfile(self.path):
            die("不是有效的 EPUB（ZIP）：%s" % self.path, EXIT_FORMAT)
        self.zf = zipfile.ZipFile(self.path)
        self.members = {n.replace("\\", "/"): n for n in self.zf.namelist()
                        if not n.endswith("/")}
        self.infos = {n: i for n, i in ((k, self.zf.getinfo(v))
                                        for k, v in self.members.items())}
        self.opf_path = self._find_opf()
        self.opf_dir = posixpath.dirname(self.opf_path)
        self.opf_root = None
        self.manifest = []          # [{id, href, path, media_type, properties}]
        self.by_id = {}
        self.spine = []             # [idref]
        self.spine_toc = None
        self.metadata = {}          # {dc-name: [values]}
        self.meta_tags = []         # [(attrs, text)]
        self.guide = []
        self.guard_messages = []
        self._parse_opf()
        self.version = (self.opf_root.get("version") or "2.0") if self.opf_root is not None else "2.0"

    # -- 基础 IO ---------------------------------------------------------
    def has(self, name):
        return name.replace("\\", "/") in self.members

    def read(self, name):
        key = name.replace("\\", "/")
        if key not in self.members:
            raise KeyError(name)
        return self.zf.read(self.members[key])

    def text(self, name, encoding=None):
        return decode(self.read(name), encoding)

    def all_files(self):
        return sorted(self.members)

    def all_bytes(self):
        return {n: self.zf.read(self.members[n]) for n in self.all_files()}

    def resolve(self, base_zip_path, href):
        return norm_href(base_zip_path, href)

    def close(self):
        self.zf.close()

    # -- 结构解析 -------------------------------------------------------
    def _find_opf(self):
        cpath = "META-INF/container.xml"
        if self.has(cpath):
            try:
                root = ET.fromstring(self.read(cpath))
                for el in root.iter():
                    if local(el.tag) == "rootfile" and el.get("full-path"):
                        p = el.get("full-path").replace("\\", "/").lstrip("/")
                        if self.has(p):
                            return p
            except ET.ParseError:
                pass
        for cand in ("OEBPS/content.opf", "content.opf", "OPS/package.opf",
                     "EPUB/content.opf", "package.opf"):
            if self.has(cand):
                return cand
        found = [n for n in self.all_files() if n.lower().endswith(".opf")]
        if found:
            return found[0]
        die("找不到 OPF：META-INF/container.xml 缺失或指向的文件不存在", EXIT_FORMAT)

    def _parse_opf(self):
        try:
            self.opf_root = ET.fromstring(self.read(self.opf_path))
        except ET.ParseError as exc:
            die("OPF 无法解析：%s（%s）" % (self.opf_path, exc), EXIT_FORMAT)
        for el in self.opf_root.iter():
            tag = local(el.tag)
            if tag == "metadata":
                for child in el:
                    cname = local(child.tag)
                    text = (child.text or "").strip()
                    if child.tag.startswith("{" + DC_NS + "}"):
                        self.metadata.setdefault(cname, []).append(text)
                    elif cname == "meta":
                        self.meta_tags.append((dict(child.attrib), text))
            elif tag == "item":
                item = {
                    "id": el.get("id", ""),
                    "href": el.get("href", ""),
                    "path": self.resolve(self.opf_path, el.get("href", "")),
                    "media_type": el.get("media-type", ""),
                    "properties": (el.get("properties") or "").split(),
                }
                self.manifest.append(item)
                self.by_id[item["id"]] = item
            elif tag == "itemref":
                if el.get("idref"):
                    self.spine.append(el.get("idref"))
            elif tag == "spine":
                self.spine_toc = el.get("toc")
            elif tag == "reference":
                self.guide.append(dict(el.attrib))

    # -- 派生视图 -------------------------------------------------------
    def dc(self, name, default=""):
        vals = self.metadata.get(name) or []
        return vals[0] if vals else default

    def title(self):
        return self.dc("title") or os.path.splitext(os.path.basename(self.path))[0]

    def protected(self):
        ep = "META-INF/encryption.xml"
        if not self.has(ep):
            return False
        data = self.read(ep).decode("utf-8", errors="replace")
        return bool(re.search(r"EncryptedData|CipherData|DRM", data, re.I))

    def guard_writable(self):
        if self.protected():
            die("该书含 DRM / 加密标记（META-INF/encryption.xml），本技能不处理受保护内容，也不提供绕过手段。",
                EXIT_FORMAT)

    def spine_docs(self):
        out = []
        for idref in self.spine:
            item = self.by_id.get(idref)
            if not item or not item["path"] or not self.has(item["path"]):
                continue
            if ext_of(item["path"]) not in (".xhtml", ".html", ".htm"):
                continue
            out.append({"idref": idref, "path": item["path"], "item": item})
        return out

    def nav_path(self):
        for item in self.manifest:
            if "nav" in item["properties"] and item["path"]:
                return item["path"]
        for item in self.manifest:
            if posixpath.basename(item["path"] or "").lower() in ("nav.xhtml", "nav.html"):
                return item["path"]
        return None

    def ncx_path(self):
        if self.spine_toc and self.spine_toc in self.by_id:
            return self.by_id[self.spine_toc]["path"]
        for item in self.manifest:
            if (item["media_type"] == "application/x-dtbncx+xml"
                    or ext_of(item["path"] or "") == ".ncx"):
                return item["path"]
        return None

    def cover_path(self):
        for attrs, _ in self.meta_tags:
            if attrs.get("name", "").lower() == "cover":
                item = self.by_id.get(attrs.get("content", ""))
                if item and item["path"]:
                    return item["path"]
        for item in self.manifest:
            if "cover-image" in item["properties"] and item["path"]:
                return item["path"]
        for item in self.manifest:
            p = item["path"] or ""
            if ext_of(p) in IMAGE_EXT and "cover" in posixpath.basename(p).lower():
                return p
        for ref in self.guide:
            if ref.get("type", "").lower() == "cover" and ref.get("href"):
                return self.resolve(self.opf_path, ref["href"])
        return None

    def toc_entries(self):
        """[{title, level, href, path}]；优先 nav.xhtml，其次 NCX，最后按章节标题兜底。"""
        nav = self.nav_path()
        if nav and self.has(nav):
            entries = parse_nav(self.read(nav), nav)
            if entries:
                return entries
        ncx = self.ncx_path()
        if ncx and self.has(ncx):
            entries = parse_ncx(self.read(ncx), ncx)
            if entries:
                return entries
        entries = []
        for i, doc in enumerate(self.spine_docs(), 1):
            entries.append({"title": first_heading(self.read(doc["path"]))
                            or "第 %d 节" % i,
                            "level": 1, "href": doc["path"], "path": doc["path"]})
        return entries

    def chapters(self):
        """章节序列：目录条目为准，目录缺失时退化成 spine 顺序。"""
        entries = self.toc_entries()
        docs = self.spine_docs()
        if not docs:
            return []
        by_path = {d["path"]: d for d in docs}
        out = []
        used = set()
        for e in entries:
            p = e.get("path")
            if p in by_path and p not in used:
                used.add(p)
                out.append({"title": e["title"], "level": e.get("level", 1),
                            "path": p})
        # 目录没覆盖到的 spine 文档也要保留在正文里
        for d in docs:
            if d["path"] not in used:
                out.append({"title": first_heading(self.read(d["path"]))
                            or posixpath.basename(d["path"]),
                            "level": 1, "path": d["path"]})
        return out

    def assets(self):
        out = []
        for item in self.manifest:
            p = item["path"] or ""
            ext = ext_of(p)
            if ext in IMAGE_EXT:
                kind = "image"
            elif ext in FONT_EXT:
                kind = "font"
            elif ext in STYLE_EXT:
                kind = "style"
            else:
                continue
            if not self.has(p):
                continue
            out.append({"kind": kind, "path": p, "media_type": item["media_type"],
                        "size": self.infos[p].file_size})
        return out


class _NavParser(HTMLParser):
    """抓 EPUB3 nav 里 epub:type="toc" 的 ol/li/a 嵌套层级。"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_toc = False
        self.nav_depth = 0
        self.level = 0
        self.capture = None
        self.buf = []
        self.entries = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "nav":
            t = (a.get("epub:type") or a.get("type") or "").lower()
            if "toc" in t:
                self.in_toc = True
                self.nav_depth = 1
            return
        if not self.in_toc:
            return
        if tag == "ol":
            self.level += 1
        elif tag == "a" and a.get("href"):
            self.current = {"title": "", "level": max(1, self.level),
                            "href": a["href"], "buf": []}
            self.capture = self.current

    def handle_data(self, data):
        if self.capture is not None:
            self.capture["buf"].append(data)

    def handle_endtag(self, tag):
        if not self.in_toc:
            return
        if tag == "a" and self.capture is not None:
            e = self.capture
            e["title"] = "".join(e.pop("buf")).strip()
            if e["title"]:
                self.entries.append(e)
            self.capture = None
        elif tag == "ol":
            self.level = max(0, self.level - 1)
        elif tag == "nav":
            self.nav_depth -= 1
            if self.nav_depth <= 0:
                self.in_toc = False


def parse_nav(data, nav_path):
    p = _NavParser()
    try:
        p.feed(decode(data))
    except Exception:
        return []
    out = []
    for e in p.entries:
        out.append({"title": e["title"], "level": e["level"], "href": e["href"],
                    "path": norm_href(nav_path, e["href"])})
    return out


def parse_ncx(data, ncx_path):
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        return []
    out = []

    def walk(node, level):
        for child in node:
            if local(child.tag) != "navPoint":
                continue
            title, src = "", ""
            for sub in child:
                if local(sub.tag) == "navLabel":
                    for t in sub.iter():
                        if local(t.tag) == "text" and (t.text or "").strip():
                            title = (t.text or "").strip()
                            break
                elif local(sub.tag) == "content":
                    src = sub.get("src", "")
            out.append({"title": title or "未命名", "level": level,
                        "href": src, "path": norm_href(ncx_path, src)})
            walk(child, level + 1)

    for el in root.iter():
        if local(el.tag) == "navMap":
            walk(el, 1)
            break
    return out


def first_heading(data):
    """取 XHTML 里第一个 h1-h6 或 <title> 的纯文本。"""
    text = decode(data)
    for pattern in (r"<h[1-6][^>]*>(.*?)</h[1-6]>", r"<title[^>]*>(.*?)</title>"):
        m = re.search(pattern, text, re.I | re.S)
        if m:
            clean = re.sub(r"<[^>]+>", "", m.group(1))
            clean = html_lib.unescape(clean).strip()
            if clean:
                return re.sub(r"\s+", " ", clean)[:120]
    return ""


# ---------------------------------------------------------------------------
# XHTML / Markdown
# ---------------------------------------------------------------------------
class _MarkdownParser(HTMLParser):
    """把 XHTML 正文转成易读 Markdown（标题/段落/列表/引用/表格/图片/代码）。"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skip = 0
        self.pre = False
        self.strong = 0
        self.em = 0

    def _nl(self, n=2):
        existing = 0
        for part in reversed(self.parts):
            m = re.search(r"\n+$", part)
            if m:
                existing += len(m.group(0))
                if m.group(0) == part:
                    continue
            break
        if existing < n:
            self.parts.append("\n" * (n - existing))

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("script", "style", "head"):
            self.skip += 1
            return
        if self.skip:
            return
        if re.fullmatch(r"h[1-6]", tag):
            self._nl(2)
            self.parts.append("#" * int(tag[1]) + " ")
        elif tag == "p":
            self._nl(2)
        elif tag in ("div", "section", "article", "ul", "ol", "table", "blockquote"):
            self._nl(2)
        elif tag == "li":
            self._nl(1)
            self.parts.append("- ")
        elif tag == "blockquote":
            self.parts.append("> ")
        elif tag == "br":
            self.parts.append("\n")
        elif tag == "hr":
            self._nl(2)
            self.parts.append("---\n")
        elif tag == "tr":
            self._nl(1)
        elif tag in ("td", "th"):
            self.parts.append("| ")
        elif tag == "pre":
            self._nl(2)
            self.parts.append("```\n")
            self.pre = True
        elif tag == "img":
            self.parts.append("![%s](%s)" % (a.get("alt", ""), a.get("src", "")))
        elif tag in ("strong", "b"):
            self.parts.append("**")
            self.strong += 1
        elif tag in ("em", "i"):
            self.parts.append("*")
            self.em += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style", "head"):
            self.skip = max(0, self.skip - 1)
            return
        if self.skip:
            return
        if tag in ("strong", "b") and self.strong:
            self.parts.append("**")
            self.strong -= 1
        elif tag in ("em", "i") and self.em:
            self.parts.append("*")
            self.em -= 1
        elif tag == "pre":
            self.parts.append("\n```\n")
            self.pre = False
        elif tag in ("p", "div", "section", "article", "ul", "ol", "table",
                     "blockquote", "tr") or re.fullmatch(r"h[1-6]", tag):
            self._nl(2)

    def handle_data(self, data):
        if self.skip:
            return
        self.parts.append(data if self.pre else re.sub(r"[ \t\r\n]+", " ", data))

    def text(self):
        s = "".join(self.parts)
        s = re.sub(r"[ \t]+\n", "\n", s)
        s = re.sub(r"\n{3,}", "\n\n", s)
        return s.strip()


def xhtml_to_markdown(data):
    p = _MarkdownParser()
    try:
        p.feed(decode(data))
    except Exception:
        return re.sub(r"<[^>]+>", "", decode(data))
    return p.text()


def plain_text(data):
    p = _MarkdownParser()
    try:
        p.feed(decode(data))
    except Exception:
        return re.sub(r"<[^>]+>", "", decode(data))
    s = p.text()
    s = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", s)
    s = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", s)
    s = re.sub(r"[#>*`|_\-]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _inline_xhtml(text):
    t = html_lib.escape(text, quote=False)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)",
               lambda m: '<img alt="%s" src="%s" />' % (m.group(1), m.group(2)), t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)",
               lambda m: '<a href="%s">%s</a>' % (m.group(2), m.group(1)), t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", t)
    return t


def markdown_to_xhtml(md_text):
    """轻量 Markdown → well-formed XHTML 片段（不用第三方库）。"""
    lines = (md_text or "").splitlines()
    out, para = [], []

    def flush():
        if para:
            out.append("<p>%s</p>" % _inline_xhtml(" ".join(para)))
            para.clear()

    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        s = line.strip()
        if s.startswith("```"):
            flush()
            i += 1
            code = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            i += 1
            out.append("<pre><code>%s</code></pre>" % html_lib.escape("\n".join(code)))
            continue
        if not s:
            flush()
            i += 1
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", s)
        if m:
            flush()
            lv = len(m.group(1))
            out.append("<h%d>%s</h%d>" % (lv, _inline_xhtml(m.group(2)), lv))
            i += 1
            continue
        if re.match(r"^(\*\s*){3,}$|^(-{3,})\s*$", s):
            flush()
            out.append("<hr />")
            i += 1
            continue
        if s.startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|?\s*:?-{2,}", lines[i + 1]):
            flush()
            head = [c.strip() for c in s.strip("|").split("|")]
            i += 2
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            thead = "".join("<th>%s</th>" % _inline_xhtml(c) for c in head)
            tbody = "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % _inline_xhtml(c) for c in r)
                            for r in rows)
            out.append("<table><thead><tr>%s</tr></thead><tbody>%s</tbody></table>"
                       % (thead, tbody))
            continue
        if s.startswith("> "):
            flush()
            quote = []
            while i < len(lines) and lines[i].strip().startswith("> "):
                quote.append(lines[i].strip()[2:])
                i += 1
            out.append("<blockquote><p>%s</p></blockquote>" %
                       _inline_xhtml(" ".join(quote)))
            continue
        unordered = re.match(r"^[-*+]\s+(.*)$", s)
        ordered = re.match(r"^\d+[.)]\s+(.*)$", s)
        if unordered or ordered:
            flush()
            tag = "ul" if unordered else "ol"
            items = []
            while i < len(lines):
                cur = lines[i].strip()
                match = (re.match(r"^[-*+]\s+(.*)$", cur) if tag == "ul"
                         else re.match(r"^\d+[.)]\s+(.*)$", cur))
                if not match:
                    break
                items.append("<li>%s</li>" % _inline_xhtml(match.group(1)))
                i += 1
            out.append("<%s>%s</%s>" % (tag, "".join(items), tag))
            continue
        para.append(s)
        i += 1
    flush()
    return "\n".join(out)


_ENTITY_RE = re.compile(r"&([A-Za-z][A-Za-z0-9]{1,31});")


def normalize_xhtml(body):
    """把 HTML 风格片段整理成 XML well-formed（补 void 闭合、实体数字化）。"""
    def ent(m):
        name = m.group(1)
        cp = html.entities.name2codepoint.get(name)
        if cp:
            return "&#%d;" % cp
        if name in ("amp", "lt", "gt", "quot", "apos"):
            return m.group(0)
        return " "
    body = _ENTITY_RE.sub(ent, body)
    body = re.sub(r"&(?!#\d+;|#x[0-9A-Fa-f]+;|amp;|lt;|gt;|quot;|apos;)", "&amp;", body)
    for tag in VOID_TAGS:
        body = re.sub(r"<(%s)\b([^>]*?)\s*/>" % tag, r"<\1\2 />", body, flags=re.I)
        body = re.sub(r"<(%s)\b([^>]*?)(?<!/)\s*>" % tag, r"<\1\2 />", body, flags=re.I)
    body = re.sub(r"</?(html|body|head)\b[^>]*>", "", body, flags=re.I)
    return body.strip()


def html_body(data):
    text = decode(data)
    m = re.search(r"<body\b[^>]*>(.*?)</body\s*>", text, re.I | re.S)
    if m:
        return normalize_xhtml(m.group(1))
    text = re.sub(r"<\?xml[^>]*\?>|<!doctype[^>]*>", "", text, flags=re.I)
    text = re.sub(r"<head\b[^>]*>.*?</head\s*>", "", text, flags=re.I | re.S)
    return normalize_xhtml(text)


def rewrite_refs(body, mapping):
    """把片段里的 src/href 按 {原路径: 新相对路径} 重写。"""
    pat = re.compile(r"(\b(?:src|href)\s*=\s*)([\"'])([^\"']+)\2", re.I)

    def repl(m):
        raw = m.group(3)
        key = urllib.parse.unquote(raw.split("#", 1)[0].split("?", 1)[0])
        anchor = raw[len(raw.split("#", 1)[0]):] if "#" in raw else ""
        if key in mapping:
            return m.group(1) + m.group(2) + mapping[key] + anchor + m.group(2)
        base = posixpath.basename(key)
        if base in mapping:
            return m.group(1) + m.group(2) + mapping[base] + anchor + m.group(2)
        return m.group(0)
    return pat.sub(repl, body)


def xhtml_document(title, body):
    return ('<?xml version="1.0" encoding="utf-8"?>\n'
            '<!DOCTYPE html>\n'
            '<html xmlns="%s" xmlns:epub="http://www.idpf.org/2007/ops" '
            'xml:lang="zh-CN" lang="zh-CN"><head><title>%s</title>'
            '<meta charset="utf-8" /><link rel="stylesheet" type="text/css" href="style.css" />'
            '</head><body>\n%s\n</body></html>\n'
            % (XHTML_NS, xml_escape(title), body))


STYLE_CSS = """@page { margin: 5% }
body { font-family: "Microsoft YaHei", "Noto Sans CJK SC", sans-serif;
       line-height: 1.75; margin: 0 6%; color: #222; }
h1, h2, h3 { line-height: 1.35; margin: 1.4em 0 .7em; page-break-after: avoid; }
h1 { font-size: 1.7em; text-align: center; }
h2 { font-size: 1.35em; border-bottom: 1px solid #ddd; padding-bottom: .2em; }
p { text-indent: 2em; margin: .55em 0; text-align: justify; }
li p, blockquote p { text-indent: 0; }
blockquote { margin: 1em 0; padding-left: 1em; border-left: 3px solid #bbb; color: #555; }
pre { background: #f5f5f5; padding: .8em; white-space: pre-wrap; font-size: .9em; }
code { font-family: Consolas, Menlo, monospace; }
img { max-width: 100%; height: auto; }
table { border-collapse: collapse; width: 100%; margin: 1em 0; }
th, td { border: 1px solid #ccc; padding: .35em .6em; }
hr { border: none; border-top: 1px solid #ddd; }
"""


# ---------------------------------------------------------------------------
# EPUB 写出
# ---------------------------------------------------------------------------
def write_epub(out, members):
    """members: {zip 内路径: bytes}；mimetype 恒第一条且 STORED。"""
    original = str(out)
    out = conflict_path(out)
    if out is None:
        print("已跳过（输出已存在，EBOOK_ON_CONFLICT=skip）：%s" % original)
        sys.exit(0)
    record_output(original, out)
    ensure_parent(out)
    data = dict(members)
    data["mimetype"] = b"application/epub+zip"
    if "META-INF/container.xml" not in data:
        data["META-INF/container.xml"] = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<container version="1.0" xmlns="%s">'
            '<rootfiles><rootfile full-path="OEBPS/content.opf" '
            'media-type="application/oebps-package+xml"/></rootfiles></container>\n'
            % CONTAINER_NS).encode("utf-8")
    names = ["mimetype"] + sorted(n for n in data if n != "mimetype")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for n in names:
            info = zipfile.ZipInfo(n, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED if n == "mimetype" else zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, data[n])
    return out


def rewrite_epub(epub, out, replacements=None, additions=None, drops=None):
    """基于原书另存：替换/新增/删除若干成员，其余原样保留。"""
    epub.guard_writable()
    data = epub.all_bytes()
    for n, b in (replacements or {}).items():
        data[n] = b
    for n, b in (additions or {}).items():
        data[n] = b
    for n in (drops or set()):
        data.pop(n, None)
    return write_epub(out, data)


def _nav_tree(entries):
    root = []
    stack = [(0, root)]
    for e in entries:
        node = {"title": e.get("title") or "未命名",
                "href": e.get("href") or "chapter-001.xhtml", "children": []}
        lvl = max(1, int(e.get("level") or 1))
        while len(stack) > 1 and stack[-1][0] >= lvl:
            stack.pop()
        stack[-1][1].append(node)
        stack.append((lvl, node["children"]))
    return root


def _render_ol(nodes):
    if not nodes:
        return ""
    items = []
    for n in nodes:
        child = _render_ol(n["children"])
        items.append('<li><a href="%s">%s</a>%s</li>'
                     % (xml_escape(n["href"]), xml_escape(n["title"]), child))
    return "<ol>\n%s\n</ol>" % "\n".join(items)


def nav_xhtml(entries, title="目录"):
    ol = _render_ol(_nav_tree(entries))
    return ('<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE html>\n'
            '<html xmlns="%s" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="zh-CN">'
            '<head><title>%s</title><link rel="stylesheet" type="text/css" href="style.css" /></head>'
            '<body><nav epub:type="toc" id="toc" role="doc-toc"><h1>%s</h1>\n%s\n'
            '</nav></body></html>\n'
            % (XHTML_NS, xml_escape(title), xml_escape(title), ol))


def ncx_xml(entries, uid, title):
    points = []
    for i, e in enumerate(entries, 1):
        points.append(
            '<navPoint id="navPoint-%d" playOrder="%d"><navLabel><text>%s</text></navLabel>'
            '<content src="%s" /></navPoint>'
            % (i, i, xml_escape(e.get("title") or "未命名"),
               xml_escape(e.get("href") or "chapter-001.xhtml")))
    return ('<?xml version="1.0" encoding="utf-8"?>\n'
            '<ncx xmlns="%s" version="2005-1"><head>'
            '<meta name="dtb:uid" content="%s" />'
            '<meta name="dtb:depth" content="2" />'
            '<meta name="dtb:totalPageCount" content="0" />'
            '<meta name="dtb:maxPageNumber" content="0" /></head>'
            '<docTitle><text>%s</text></docTitle><navMap>%s</navMap></ncx>\n'
            % (NCX_NS, xml_escape(uid), xml_escape(title), "".join(points)))


def opf_xml(meta, chapter_files, resources, cover_file, nav_file, ncx_file):
    uid = meta.get("identifier") or "urn:uuid:ebook-all-done-%s" % datetime.date.today().isoformat()
    lang = meta.get("language") or "zh-CN"
    title = meta.get("title") or "未命名电子书"
    creators = meta.get("creator") or []
    if isinstance(creators, str):
        creators = [creators]

    def dc(tag, value, attrs=""):
        return "<dc:%s%s>%s</dc:%s>" % (tag, attrs, xml_escape(value), tag)

    md = [dc("title", title), dc("language", lang), dc("identifier", uid, ' id="bookid"')]
    for c in creators:
        md.append(dc("creator", c))
    for key in ("publisher", "description", "subject", "rights", "contributor", "date"):
        if meta.get(key):
            md.append(dc(key, meta[key]))
    md.append('<meta property="dcterms:modified">%s</meta>'
              % datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"))
    if cover_file:
        md.append('<meta name="cover" content="cover-image" />')

    items = ['<item id="nav" href="%s" media-type="application/xhtml+xml" properties="nav" />' % nav_file,
             '<item id="ncx" href="%s" media-type="application/x-dtbncx+xml" />' % ncx_file,
             '<item id="style" href="style.css" media-type="text/css" />']
    if cover_file:
        items.append('<item id="cover-image" href="%s" media-type="%s" properties="cover-image" />'
                     % (cover_file, mime_of(cover_file)))
    for i, fn in enumerate(chapter_files, 1):
        items.append('<item id="chap-%03d" href="%s" media-type="application/xhtml+xml" />'
                     % (i, fn))
    for i, fn in enumerate(sorted(resources), 1):
        items.append('<item id="res-%03d" href="%s" media-type="%s" />'
                     % (i, fn, mime_of(fn)))
    spine = "".join('<itemref idref="chap-%03d" />' % i
                    for i in range(1, len(chapter_files) + 1))
    guide = '<reference type="cover" title="封面" href="%s" />' % cover_file if cover_file else ""
    guide += '<reference type="toc" title="目录" href="%s" />' % nav_file
    return ('<?xml version="1.0" encoding="utf-8"?>\n'
            '<package xmlns="%s" xmlns:dc="%s" version="3.0" unique-identifier="bookid">'
            '<metadata>%s</metadata><manifest>%s</manifest>'
            '<spine toc="ncx">%s</spine><guide>%s</guide></package>\n'
            % (OPF_NS, DC_NS, "".join(md), "".join(items), spine, guide))


def build_epub(out, chapters, meta=None, cover=None, resources=None):
    """从零生成 EPUB3。

    chapters : [{'title': str, 'level': int, 'body': XHTML 片段 或 'md': Markdown}]
    cover    : (文件名, bytes) 或 None
    resources: {新 zip 内路径: bytes}，章节里的 src/href 应已指向这些路径
    """
    meta = dict(meta or {})
    resources = dict(resources or {})
    if not chapters:
        die("没有可写入的章节", EXIT_USAGE)
    members = {}
    chapter_files, entries = [], []
    for i, ch in enumerate(chapters, 1):
        fn = "OEBPS/chapter-%03d.xhtml" % i
        body = ch.get("body")
        if body is None:
            body = markdown_to_xhtml(ch.get("md") or "")
        body = normalize_xhtml(body)
        members[fn] = xhtml_document(ch.get("title") or ("第 %d 节" % i), body).encode("utf-8")
        chapter_files.append(fn)
        entries.append({"title": ch.get("title") or ("第 %d 节" % i),
                        "level": int(ch.get("level") or 1), "href": fn})
    nav_file, ncx_file = "OEBPS/nav.xhtml", "OEBPS/toc.ncx"
    members[nav_file] = nav_xhtml(entries, meta.get("title") or "目录").encode("utf-8")
    members[ncx_file] = ncx_xml(entries, meta.get("identifier") or "ebook-all-done",
                                meta.get("title") or "未命名电子书").encode("utf-8")
    members["OEBPS/style.css"] = STYLE_CSS.encode("utf-8")
    cover_file = None
    if cover:
        cname, cbytes = cover
        cover_file = "OEBPS/images/" + posixpath.basename(cname)
        members[cover_file] = cbytes
    for fn, b in resources.items():
        members[fn if fn.startswith("OEBPS/") else "OEBPS/" + fn] = b
    res_names = [n for n in members if n.startswith("OEBPS/")
                 and n not in chapter_files + [nav_file, ncx_file, "OEBPS/style.css"]
                 and n != cover_file]
    # OPF 在 OEBPS/ 下，所有 href 必须是相对 OEBPS 的路径，不能只取 basename
    rel_resources = {posixpath.relpath(n, "OEBPS"): members[n] for n in res_names}
    rel_cover = posixpath.relpath(cover_file, "OEBPS") if cover_file else None
    members["OEBPS/content.opf"] = opf_xml(
        meta, [posixpath.relpath(f, "OEBPS") for f in chapter_files],
        rel_resources, rel_cover,
        posixpath.relpath(nav_file, "OEBPS"),
        posixpath.relpath(ncx_file, "OEBPS")).encode("utf-8")
    return write_epub(out, members)


# ---------------------------------------------------------------------------
# 可选外部依赖
# ---------------------------------------------------------------------------
def find_browser():
    override = os.environ.get("EBOOK_BROWSER")
    if override and os.path.isfile(override):
        return override
    for name in ("msedge", "microsoft-edge", "chrome", "google-chrome",
                 "chromium", "chromium-browser"):
        p = shutil.which(name)
        if p:
            return p
    for p in (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
              "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
              "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              "/usr/bin/chromium", "/usr/bin/google-chrome"):
        if os.path.isfile(p):
            return p
    return None


def need_browser():
    p = find_browser()
    if not p:
        die("缺少依赖：本机未找到 Edge / Chrome。请安装浏览器，或用 EBOOK_BROWSER 指定可执行文件；"
            "也可装 Calibre 后改用 eb-convert 转 PDF。", EXIT_USAGE)
    return p


def html_to_pdf(html_text, out, assets=None, browser=None, timeout=180):
    """把完整 HTML 用无头浏览器打印成 PDF；assets={相对路径: bytes} 会写到临时目录。"""
    original = str(out)
    out = conflict_path(out)
    if out is None:
        print("已跳过（输出已存在，EBOOK_ON_CONFLICT=skip）：%s" % original)
        sys.exit(0)
    record_output(original, out)
    browser = browser or need_browser()
    ensure_parent(out)
    tmp = tempfile.mkdtemp(prefix="ebook-pdf-")
    try:
        for rel, data in (assets or {}).items():
            dst = os.path.join(tmp, rel.replace("/", os.sep))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "wb") as f:
                f.write(data)
        html_path = os.path.join(tmp, "source.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_text)
        profile = os.path.join(tmp, "profile")
        cmd = [browser, "--headless", "--disable-gpu", "--no-sandbox",
               "--no-first-run", "--no-default-browser-check",
               "--disable-extensions", "--allow-file-access-from-files",
               "--user-data-dir=" + profile, "--virtual-time-budget=10000",
               "--no-pdf-header-footer", "--print-to-pdf=" + os.path.abspath(str(out)),
               pathlib.Path(html_path).resolve().as_uri()]
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=timeout)
        if not os.path.isfile(out) or os.path.getsize(out) == 0:
            die("浏览器未能生成 PDF。stderr: %s" % (proc.stderr or "")[-800:], EXIT_FAIL)
        return os.path.getsize(out)
    except subprocess.TimeoutExpired:
        die("浏览器打印超时（%ss）" % timeout, EXIT_FAIL)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def find_calibre():
    p = shutil.which("ebook-convert") or shutil.which("ebook-convert.exe")
    if p:
        return p
    for c in (r"C:\Program Files\Calibre2\ebook-convert.exe",
              r"C:\Program Files (x86)\Calibre2\ebook-convert.exe",
              "/Applications/calibre.app/Contents/MacOS/ebook-convert",
              "/usr/bin/ebook-convert"):
        if os.path.isfile(c):
            return c
    return None


def need_calibre():
    p = find_calibre()
    if not p:
        die("缺少依赖 ebook-convert：请到 https://calibre-ebook.com 安装 Calibre 并把 "
            "ebook-convert 加入 PATH（Windows 默认在 C:\\Program Files\\Calibre2）。", EXIT_USAGE)
    return p


def need_pillow():
    try:
        from PIL import Image  # noqa: F401
        return True
    except Exception:
        die("缺少依赖 Pillow：请运行  pip install Pillow", EXIT_USAGE)


def edit_opf(epub, callback):
    """解析 OPF → callback(root) 原地修改 → 返回新 OPF 字节串。

    callback 里用 local(el.tag) 判断标签名即可；ET 会保留原命名空间前缀。
    """
    ET.register_namespace("", OPF_NS)
    ET.register_namespace("dc", DC_NS)
    root = ET.fromstring(epub.read(epub.opf_path))
    callback(root)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


REF_RE = re.compile(r"\b(src|href)\s*=\s*([\"'])([^\"']+)\2", re.I)


def chapter_payload(ep, chapters, prefix, cache=None):
    """把原书章节 XHTML 转成可重建的 body，并把引用资源重映射到 prefix 下。

    返回 (chapters_with_body, resources)；cache 可跨多本书复用，避免同名资源重复导出。
    """
    cache = cache if cache is not None else {}
    resources, out = {}, []

    def repl(m):
        raw = m.group(3)
        head = raw.split("#", 1)[0].split("?", 1)[0]
        anchor = raw[len(head):]
        p = norm_href(chapters_current["path"], raw)
        if not p or not ep.has(p):
            return m.group(0)
        if p not in cache:
            new = posixpath.join(prefix, safe_name(posixpath.basename(p), 40))
            cache[p] = new
            resources[new] = ep.read(p)
        return "%s=%s%s%s%s" % (m.group(1), m.group(2), cache[p], anchor, m.group(2))

    for ch in chapters:
        chapters_current = ch
        body = REF_RE.sub(repl, html_body(ep.read(ch["path"])))
        out.append({"title": ch["title"], "level": ch.get("level", 1),
                    "body": body})
    return out, resources


def meta_element(root):
    for el in root.iter():
        if local(el.tag) == "metadata":
            return el
    return None


def manifest_element(root):
    for el in root.iter():
        if local(el.tag) == "manifest":
            return el
    return None


def spine_element(root):
    for el in root.iter():
        if local(el.tag) == "spine":
            return el
    return None
