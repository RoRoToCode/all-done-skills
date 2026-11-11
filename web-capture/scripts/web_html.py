#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A small, dependency-free HTML DOM used by every web-capture action.

Provides: tolerant parsing (html.parser), metadata/link/image/table extraction,
readability-style main-content scoring, Markdown rendering and re-serialization
for the single-file offline archive.
"""
from __future__ import annotations

import html
import html.parser
import mimetypes
import re
from urllib.parse import urljoin

from web_common import DEFAULT_UA, MAX_RESOURCE, WebError, fetch

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
        "meta", "param", "source", "track", "wbr"}
BLOCK = {"html", "body", "div", "section", "article", "main", "aside", "header",
         "footer", "nav", "figure", "figcaption", "details", "summary", "center",
         "address", "dl", "dt", "dd", "fieldset", "legend"}
SKIP = {"script", "style", "noscript", "template", "svg", "iframe", "object",
        "canvas", "form", "button", "select", "option", "textarea", "head",
        "math", "video", "audio", "map", "dialog"}
HEADINGS = {"h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}
NOISE_HINT = re.compile(
    r"(comment|sidebar|advert|promo|related|footer|header|nav|menu|share|"
    r"subscribe|cookie|banner|popup|modal|recommend|breadcrumb|pagination|"
    r"\bad[s_-]?\b)", re.I)
MAIN_HINT = re.compile(r"(article|content|main|post|entry|markdown|detail|story)", re.I)


class Node:
    __slots__ = ("tag", "attrs", "children", "parent")

    def __init__(self, tag, attrs=None, parent=None):
        self.tag = tag
        self.attrs = dict(attrs or [])
        self.children: list = []
        self.parent = parent

    def attr(self, name, default=""):
        return self.attrs.get(name) or default

    def has(self, name):
        return name in self.attrs


class _Builder(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#document")
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs, self.stack[-1])
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        node = Node(tag, attrs, self.stack[-1])
        self.stack[-1].children.append(node)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        if data:
            self.stack[-1].children.append(data)


def parse(markup: str) -> Node:
    b = _Builder()
    try:
        b.feed(markup)
        b.close()
    except Exception:                        # html.parser is tolerant; be defensive
        pass
    return b.root


def iter_nodes(node: Node):
    for child in node.children:
        if isinstance(child, Node):
            yield child
            yield from iter_nodes(child)


def raw_text(node) -> str:
    if isinstance(node, str):
        return node
    out = []
    for child in node.children:
        if isinstance(child, str):
            out.append(child)
        elif child.tag not in SKIP:
            out.append(raw_text(child))
    return "".join(out)


def clean_text(node) -> str:
    return re.sub(r"[ \t\r\f\v]+", " ", raw_text(node)).strip()


def visible_text(node) -> str:
    """Text with block boundaries, for diffing and content scoring."""
    if isinstance(node, str):
        return node
    if node.tag in SKIP:
        return ""
    parts = []
    for child in node.children:
        parts.append(visible_text(child) if isinstance(child, Node) else child)
        if isinstance(child, Node) and (child.tag in BLOCK or child.tag in HEADINGS
                                        or child.tag in ("p", "li", "tr", "br")):
            parts.append("\n")
    return re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+", " ", "".join(parts))).strip()


def serialize(node) -> str:
    """Re-serialize the DOM (offline archive does not need byte identity)."""
    if isinstance(node, str):
        return html.escape(node, quote=False)
    if node.tag == "#document":
        return "".join(serialize(c) for c in node.children)
    raw = node.tag in ("script", "style", "textarea")
    attrs = "".join(' %s="%s"' % (k, html.escape(str(v or ""), quote=True))
                    for k, v in node.attrs.items())
    head = "<%s%s" % (node.tag, attrs)
    if node.tag in VOID:
        return head + ">"
    inner = "".join(serialize(c) if not raw else
                    (c if isinstance(c, str) else raw_text(c))
                    for c in node.children)
    return "%s>%s</%s>" % (head, inner, node.tag)


class Document:
    def __init__(self, markup: str, base_url: str = ""):
        self.html = markup
        self.base_url = base_url
        self.root = parse(markup)
        self.doctype = markup.lstrip()[:120].lower().startswith("<!doctype")
        base_tag = next((n for n in iter_nodes(self.root) if n.tag == "base"
                         and n.attr("href")), None)
        self.href_base = urljoin(base_url, base_tag.attr("href")) if base_tag and base_url else (base_tag.attr("href") if base_tag else base_url)
        html_tag = next((n for n in iter_nodes(self.root) if n.tag == "html"), None)
        self.lang = html_tag.attr("lang") if html_tag else ""
        title_node = next((n for n in iter_nodes(self.root) if n.tag == "title"), None)
        self.title = clean_text(title_node) if title_node else ""
        self.metas = {}
        for n in iter_nodes(self.root):
            if n.tag != "meta":
                continue
            key = n.attr("name") or n.attr("property") or n.attr("http-equiv")
            if key:
                self.metas[key.lower()] = n.attr("content")
        canonical = next((n for n in iter_nodes(self.root)
                          if n.tag == "link" and "canonical" in n.attr("rel").lower()), None)
        self.canonical = self.abs(canonical.attr("href")) if canonical else ""
        self.jsonld = []
        for n in iter_nodes(self.root):
            if n.tag == "script" and "ld+json" in n.attr("type").lower():
                self.jsonld.append(raw_text(n).strip())

    def abs(self, url: str) -> str:
        url = (url or "").strip()
        if not url or url.startswith(("data:", "javascript:", "mailto:", "tel:", "#", "blob:")):
            return ""
        if not self.href_base:
            return ""
        try:
            return urljoin(self.href_base, url)
        except ValueError:
            return ""

    def headings(self, node: Node | None = None) -> list[dict]:
        out = []
        for n in iter_nodes(node or self.root):
            if n.tag in HEADINGS:
                text = clean_text(n)
                if text:
                    out.append({"level": HEADINGS[n.tag], "text": text})
        return out

    def links(self) -> list[dict]:
        out = []
        for n in iter_nodes(self.root):
            if n.tag != "a" or not n.has("href"):
                continue
            url = self.abs(n.attr("href"))
            if not url:
                continue
            out.append({"text": clean_text(n), "href": url,
                        "rel": n.attr("rel"), "title": n.attr("title")})
        return out

    def images(self) -> list[dict]:
        out = []
        for n in iter_nodes(self.root):
            if n.tag == "img":
                src = n.attr("src")
                if not src and n.has("srcset"):
                    src = n.attr("srcset").split(",")[0].strip().split(" ")[0]
                out.append({"src": self.abs(src) or src, "alt": n.attr("alt"),
                            "width": n.attr("width"), "height": n.attr("height"),
                            "title": n.attr("title")})
        return out

    def tables(self) -> list[Node]:
        return [n for n in iter_nodes(self.root) if n.tag == "table"]

    def resources(self) -> list[dict]:
        """External css/js/image/icon references, for --assets and single-file."""
        out = []
        for n in iter_nodes(self.root):
            if n.tag == "link":
                rel = n.attr("rel").lower()
                if "stylesheet" in rel and n.attr("href"):
                    kind = "css"
                elif "icon" in rel and n.attr("href"):
                    kind = "image"
                else:
                    continue
                url = self.abs(n.attr("href"))
                attr = "href"
            elif n.tag == "script" and n.attr("src"):
                kind, url, attr = "js", self.abs(n.attr("src")), "src"
            elif n.tag == "img":
                src = n.attr("src") or (n.attr("srcset").split(",")[0].strip().split(" ")[0] if n.has("srcset") else "")
                if not src:
                    continue
                kind, url, attr = "image", self.abs(src), "src"
            elif n.tag == "source" and n.has("srcset"):
                kind = "image"
                url = self.abs(n.attr("srcset").split(",")[0].strip().split(" ")[0])
                attr = "srcset"
            elif n.tag == "video" and n.attr("poster"):
                kind, url, attr = "image", self.abs(n.attr("poster")), "poster"
            else:
                continue
            if url and not url.startswith("data:"):
                out.append({"kind": kind, "url": url, "node": n, "attr": attr,
                            "original": n.attr(attr)})
        return out

    def main(self) -> Node:
        """Pick the densest plausible content container (readability-lite)."""
        body = next((n for n in iter_nodes(self.root) if n.tag == "body"), self.root)
        candidates = [n for n in iter_nodes(body)
                      if n.tag in ("article", "main", "div", "section", "td")]
        best, best_score = body, -1e9
        for n in candidates:
            text = clean_text(n)
            if len(text) < 80:
                continue
            hint = " ".join([n.attr("id"), n.attr("class"), n.attr("role"), n.attr("itemprop")])
            score = len(text)
            score -= sum(len(clean_text(a)) for a in iter_nodes(n) if a.tag == "a") * 0.65
            score += 25 * sum(1 for a in iter_nodes(n) if a.tag == "p")
            if MAIN_HINT.search(hint) or n.tag in ("article", "main"):
                score += 220
            if NOISE_HINT.search(hint):
                score -= 500
            if n.tag == "section" and len(text) < 200:
                score -= 80
            if score > best_score:
                best, best_score = n, score
        return best

    # ---------------------------------------------------------------- Markdown
    def markdown(self, node: Node | None = None, all_content: bool = False) -> tuple[str, list[dict]]:
        root = self.root if all_content else (node or self.main())
        blocks: list[str] = []
        self._render(root, blocks)
        text = re.sub(r"\n{3,}", "\n\n", "\n\n".join(b for b in blocks if b.strip())).strip()
        return text + ("\n" if text else ""), self.headings(root)

    def _render(self, node: Node, out: list[str], buf: list[str] | None = None) -> None:
        own = buf is None
        buf = [] if own else buf

        def flush():
            value = re.sub(r"[ \t]+", " ", "".join(buf)).strip()
            if value:
                out.append(value)
            buf.clear()

        for child in node.children:
            if isinstance(child, str):
                buf.append(child)
                continue
            tag = child.tag
            if tag in SKIP:
                continue
            if tag in HEADINGS:
                flush()
                out.append("#" * HEADINGS[tag] + " " + self._inline(child))
            elif tag == "p":
                flush()
                out.append(self._inline(child))
            elif tag in ("ul", "ol"):
                flush()
                out.append(self._list(child, tag == "ol"))
            elif tag == "table":
                flush()
                out.append(self._table_md(child))
            elif tag == "pre":
                flush()
                out.append("```\n" + raw_text(child).strip("\n") + "\n```")
            elif tag == "blockquote":
                flush()
                inner: list[str] = []
                self._render(child, inner)
                out.append("\n".join("> " + line for line in inner))
            elif tag == "hr":
                flush()
                out.append("---")
            elif tag == "br":
                buf.append("\n")
            elif tag in BLOCK:
                flush()
                self._render(child, out)
            else:
                buf.append(self._inline(child))
        if own:
            flush()

    def _inline(self, node: Node) -> str:
        if isinstance(node, str):
            return re.sub(r"\s+", " ", node)
        if node.tag in SKIP:
            return ""
        if node.tag == "br":
            return " "
        text = "".join(self._inline(c) for c in node.children).strip()
        if node.tag == "a":
            url = self.abs(node.attr("href"))
            return "[%s](%s)" % (text, url) if url else text
        if node.tag == "img":
            src = self.abs(node.attr("src")) or node.attr("src")
            return "![%s](%s)" % (node.attr("alt"), src)
        if node.tag in ("strong", "b"):
            return "**%s**" % text if text else ""
        if node.tag in ("em", "i"):
            return "*%s*" % text if text else ""
        if node.tag == "code":
            return "`%s`" % text if text else ""
        return text

    def _list(self, node: Node, ordered: bool, depth: int = 0) -> str:
        lines, idx = [], 1
        for li in node.children:
            if not isinstance(li, Node) or li.tag != "li":
                continue
            nested = [c for c in li.children if isinstance(c, Node) and c.tag in ("ul", "ol")]
            parts = [self._inline(c) for c in li.children
                     if not (isinstance(c, Node) and c.tag in ("ul", "ol"))]
            body = re.sub(r"\s+", " ", "".join(parts)).strip()
            prefix = "%d. " % idx if ordered else "- "
            lines.append("  " * depth + prefix + body)
            for sub in nested:
                lines.append(self._list(sub, sub.tag == "ol", depth + 1))
            idx += 1
        return "\n".join(lines)

    def _table_md(self, node: Node) -> str:
        rows = table_rows(node)
        if not rows:
            return ""
        width = max(len(r) for r in rows)
        lines = []
        for i, row in enumerate(rows):
            cells = [re.sub(r"\s+", " ", c).replace("|", "\\|") for c in row]
            cells += [""] * (width - len(cells))
            lines.append("| " + " | ".join(cells) + " |")
            if i == 0:
                lines.append("| " + " | ".join(["---"] * width) + " |")
        return "\n".join(lines)


def table_rows(table: Node) -> list[list[str]]:
    out = []
    for tr in iter_nodes(table):
        if tr.tag != "tr" or any(isinstance(p, Node) and p.tag == "tr"
                                 for p in _parents(tr, table)):
            continue
        cells = [c for c in tr.children if isinstance(c, Node) and c.tag in ("td", "th")]
        if not cells:
            cells = [c for c in iter_nodes(tr) if c.tag in ("td", "th")]
        out.append([clean_text(c) for c in cells])
    return out


def _parents(node: Node, stop: Node) -> list[Node]:
    out, cur = [], node.parent
    while cur is not None and cur is not stop:
        out.append(cur)
        cur = cur.parent
    return out


# ---------------------------------------------------------------- resources
def guess_mime(url: str, kind: str, header: str = "") -> str:
    if header:
        return header.split(";")[0].strip()
    if kind == "css":
        return "text/css"
    if kind == "js":
        return "application/javascript"
    return mimetypes.guess_type(url.split("?")[0])[0] or "application/octet-stream"


def data_uri(content: bytes, mime: str) -> str:
    import base64
    return "data:%s;base64,%s" % (mime, base64.b64encode(content).decode("ascii"))


def download_resource(url: str, *, timeout: float = 15, ua: str = "",
                      max_bytes: int = MAX_RESOURCE) -> tuple[bytes, str]:
    """GET a page sub-resource. Never raises for a single missing asset."""
    if url.startswith("data:"):
        return b"", ""
    try:
        src = fetch(url, timeout=timeout, ua=ua or DEFAULT_UA,
                    max_bytes=max_bytes, respect_robots=False)
        return src.body, guess_mime(url, "asset", src.headers.get("content-type", ""))
    except (WebError, OSError, ValueError) as exc:
        raise WebError(str(exc)) from exc


CSS_URL = re.compile(r"url\(\s*(['\"]?)([^'\")\s]+)\1\s*\)", re.I)


def inline_css(text: str, css_url: str, timeout: float = 15) -> tuple[str, list[str]]:
    """Inline url() references inside a stylesheet (one level deep)."""
    warnings = []

    def repl(m):
        target = urljoin(css_url, m.group(2).strip())
        if target.startswith("data:"):
            return m.group(0)
        try:
            body, mime = download_resource(target, timeout=timeout)
            return "url(%s)" % data_uri(body, guess_mime(target, "image", mime))
        except WebError as exc:
            warnings.append("CSS 资源未内联 %s: %s" % (target, exc))
            return m.group(0)
    return CSS_URL.sub(repl, text), warnings
