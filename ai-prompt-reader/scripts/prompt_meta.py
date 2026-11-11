"""容器层：只读文件头部元数据块，不解码像素。

支持 PNG（tEXt / zTXt / iTXt / eXIf）、JPEG（APP1 Exif、APP1 XMP、COM）、
WebP（EXIF / XMP）。全部走标准库，不需要 Pillow，几千张图也能一张张扫过去。
"""
import zlib

PNG_SIG = b"\x89PNG\r\n\x1a\n"
XMP_NS = b"http://ns.adobe.com/xap/1.0/"


class MetaReadError(Exception):
    """文件读不动：不是支持的容器格式，或头已损坏。"""


def read_meta(path):
    """返回 {"format", "size", "blocks"}。

    blocks 是统一后的文字块列表：{"name": 名称, "text": 文本, "source": 来源}。
    """
    with open(path, "rb") as f:
        head = f.read(12)
        f.seek(0)
        if head.startswith(PNG_SIG):
            return _read_png(f)
        if head.startswith(b"\xff\xd8"):
            return _read_jpeg(f)
        if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
            return _read_webp(f)
    raise MetaReadError("不支持的容器格式（只支持 PNG / JPEG / WebP）")


# ---------------------------------------------------------------- PNG

def _png_text(ctype, data):
    """解出 tEXt / zTXt / iTXt 三种文字块，返回 (关键字, 文本)。"""
    sep = data.find(b"\x00")
    if sep < 0:
        return None
    key = data[:sep].decode("latin-1", "replace")

    if ctype == b"tEXt":
        return key, data[sep + 1:].decode("latin-1", "replace")

    if ctype == b"zTXt":
        if len(data) < sep + 2:
            return None
        try:
            return key, zlib.decompress(data[sep + 2:]).decode("latin-1", "replace")
        except zlib.error:
            return None

    # iTXt: keyword \0 flag(1) method(1) lang\0 translated\0 text(utf-8)
    rest = data[sep + 1:]
    if len(rest) < 3:
        return None
    flag, _method = rest[0], rest[1]
    body = rest[2:]
    p = body.find(b"\x00")
    if p < 0:
        return None
    body = body[p + 1:]
    p = body.find(b"\x00")
    if p < 0:
        return None
    body = body[p + 1:]
    if flag:
        try:
            body = zlib.decompress(body)
        except zlib.error:
            return None
    return key, body.decode("utf-8", "replace")


def _read_png(f):
    blocks, size = [], None
    f.seek(8)
    while True:
        head = f.read(8)
        if len(head) < 8:
            break
        length = int.from_bytes(head[:4], "big")
        ctype = head[4:8]
        if ctype == b"IEND":
            break
        data = f.read(length)
        f.read(4)  # CRC 不校验：读提示词不需要完整性
        if ctype == b"IHDR" and len(data) >= 8:
            size = (int.from_bytes(data[:4], "big"), int.from_bytes(data[4:8], "big"))
        elif ctype in (b"tEXt", b"zTXt", b"iTXt"):
            got = _png_text(ctype, data)
            if got and got[1].strip():
                blocks.append({"name": got[0], "text": got[1],
                               "source": ctype.decode()})
        elif ctype == b"eXIf":
            for name, text in tiff_texts(data):
                blocks.append({"name": name, "text": text, "source": "eXIf"})
    return {"format": "PNG", "size": size, "blocks": blocks}


# ---------------------------------------------------------------- JPEG

def _read_jpeg(f):
    blocks, size = [], None
    f.seek(2)
    while True:
        b = f.read(1)
        while b and b != b"\xff":
            b = f.read(1)
        if not b:
            break
        marker = f.read(1)
        while marker == b"\xff":          # 填充字节
            marker = f.read(1)
        if not marker:
            break
        m = marker[0]
        if m == 0xD9:                     # EOI
            break
        if m in (0x01,) or 0xD0 <= m <= 0xD7:
            continue
        raw = f.read(2)
        if len(raw) < 2:
            break
        seg = int.from_bytes(raw, "big") - 2
        if seg < 0:
            break
        payload = f.read(seg)

        if m == 0xE1 and payload.startswith(b"Exif\x00\x00"):
            for name, text in tiff_texts(payload[6:]):
                blocks.append({"name": name, "text": text, "source": "Exif"})
        elif m == 0xE1 and payload.startswith(XMP_NS):
            text = payload[len(XMP_NS):].decode("utf-8", "replace")
            blocks.append({"name": "XMP", "text": text, "source": "XMP"})
        elif m == 0xFE:                   # COM 注释
            text = payload.decode("latin-1", "replace")
            if text.strip():
                blocks.append({"name": "Comment", "text": text, "source": "COM"})
        elif 0xC0 <= m <= 0xCF and m not in (0xC4, 0xC8, 0xCC) and len(payload) >= 5:
            size = (int.from_bytes(payload[3:5], "big"),
                    int.from_bytes(payload[1:3], "big"))
        elif m == 0xDA:                   # 图像数据开始，后面不会再有文字块
            break
    return {"format": "JPEG", "size": size, "blocks": blocks}


# ---------------------------------------------------------------- WebP

def _read_webp(f):
    blocks, size = [], None
    f.seek(12)
    while True:
        head = f.read(8)
        if len(head) < 8:
            break
        fourcc = head[:4]
        length = int.from_bytes(head[4:8], "little")
        data = f.read(length)
        if length % 2:
            f.read(1)
        if fourcc == b"EXIF":
            tiff = data[6:] if data.startswith(b"Exif\x00\x00") else data
            for name, text in tiff_texts(tiff):
                blocks.append({"name": name, "text": text, "source": "EXIF"})
        elif fourcc == b"XMP ":
            blocks.append({"name": "XMP", "text": data.decode("utf-8", "replace"),
                           "source": "XMP"})
        elif fourcc == b"VP8X" and len(data) >= 10:
            w = int.from_bytes(data[4:7], "little") + 1
            h = int.from_bytes(data[7:10], "little") + 1
            size = (w, h)
    return {"format": "WebP", "size": size, "blocks": blocks}


# ---------------------------------------------------------------- TIFF / EXIF

_TIFF_TAGS = {
    0x010E: "ImageDescription",
    0x010F: "Make",
    0x0110: "Model",
    0x0131: "Software",
    0x8298: "Copyright",
    0x9286: "UserComment",
    0x9C9B: "XPTitle",
    0x9C9C: "XPComment",
    0x9C9D: "XPAuthor",
    0xA430: "CameraOwner",
}

_TYPE_SIZE = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 6: 1, 7: 1, 8: 2, 9: 4, 10: 8, 11: 4, 12: 8}


def _decode_user_comment(raw, order):
    """UserComment 前 8 字节是字符集标记，之后才是正文。"""
    tag, body = raw[:8], raw[8:]
    if tag.startswith(b"ASCII"):
        return body.decode("latin-1", "replace")
    if tag.startswith(b"UNICODE"):
        if body.startswith(b"\xff\xfe"):
            return body[2:].decode("utf-16-le", "replace")
        if body.startswith(b"\xfe\xff"):
            return body[2:].decode("utf-16-be", "replace")
        enc = "utf-16-le" if order == "<" else "utf-16-be"
        return body.decode(enc, "replace")
    if tag.startswith(b"JIS"):
        return body.decode("shift_jis", "replace")
    for enc in ("utf-8", "latin-1"):
        try:
            return body.decode(enc)
        except UnicodeDecodeError:
            continue
    return ""


def tiff_texts(buf):
    """从一个 TIFF/EXIF 数据块里取出可读文字字段，返回 [(名称, 文本)]。"""
    if len(buf) < 8:
        return []
    if buf[:2] == b"II":
        order, bo = "<", "little"
    elif buf[:2] == b"MM":
        order, bo = ">", "big"
    else:
        return []
    ifd = int.from_bytes(buf[4:8], bo)
    if not (8 <= ifd < len(buf)):
        return []

    out, seen = [], set()

    def read_value(typ, count, field_off):
        n = _TYPE_SIZE.get(typ, 1) * count
        if n <= 4:
            raw = buf[field_off:field_off + n]
        else:
            ptr = int.from_bytes(buf[field_off:field_off + 4], bo)
            if ptr + n > len(buf):
                return None
            raw = buf[ptr:ptr + n]
        return raw

    def walk(offset, depth=0):
        if depth > 2 or offset <= 0 or offset >= len(buf) - 2 or offset in seen:
            return
        seen.add(offset)
        count = int.from_bytes(buf[offset:offset + 2], bo)
        if count <= 0 or count > 4096:
            return
        base = offset + 2
        for i in range(count):
            entry = base + i * 12
            if entry + 12 > len(buf):
                return
            tag = int.from_bytes(buf[entry:entry + 2], bo)
            typ = int.from_bytes(buf[entry + 2:entry + 4], bo)
            n = int.from_bytes(buf[entry + 4:entry + 8], bo)
            if tag == 0x8769:  # Exif 子 IFD，UserComment 就在里面
                ptr = int.from_bytes(buf[entry + 8:entry + 12], bo)
                walk(ptr, depth + 1)
                continue
            name = _TIFF_TAGS.get(tag)
            if not name or n == 0 or n > 1 << 20:
                continue
            raw = read_value(typ, n, entry + 8)
            if not raw:
                continue
            if name in ("UserComment",):
                text = _decode_user_comment(raw, order)
            elif name.startswith("XP"):
                text = raw.decode("utf-16-le", "replace")
            else:
                text = raw.split(b"\x00")[0].decode("utf-8", "replace")
                if not text.strip():
                    text = raw.split(b"\x00")[0].decode("latin-1", "replace")
            text = text.rstrip("\x00").strip()
            if text:
                out.append((name, text))

    walk(ifd)
    return out
