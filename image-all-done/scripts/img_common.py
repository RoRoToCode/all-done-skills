"""图片动作共享工具：依赖守卫、不覆盖输入、保存与结果输出。"""
import os
import sys


def need_pillow():
    try:
        from PIL import Image
        return Image
    except Exception:
        sys.stderr.write("缺少依赖 Pillow：请运行  pip install Pillow\n")
        sys.exit(2)


def guard_import(module, hint):
    try:
        return __import__(module)
    except Exception:
        sys.stderr.write("缺少依赖 %s：%s\n" % (module, hint))
        sys.exit(2)


def no_overwrite(inp, out):
    if os.path.abspath(inp) == os.path.abspath(out):
        sys.stderr.write("输出不得等于输入：%s\n" % inp)
        sys.exit(3)


def ensure_parent(out):
    d = os.path.dirname(os.path.abspath(out))
    if d:
        os.makedirs(d, exist_ok=True)


def save_image(img, out, **kwargs):
    ensure_parent(out)
    img.save(out, **kwargs)
    return out


def result(path, img=None):
    size = os.path.getsize(path)
    fmt = getattr(img, "format", None) if img is not None else None
    if fmt:
        print("已保存 %s  格式=%s 尺寸=%dx%d 体积=%d 字节"
              % (path, fmt, img.size[0], img.size[1], size))
    else:
        print("已保存 %s  体积=%d 字节" % (path, size))


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def load_font(size):
    """返回能渲染中文的字体；找不到系统字体则回退默认字体。

    默认字体不含 CJK 字形，中文水印会变成方块，所以优先探测各平台
    自带的中文字体（微软雅黑 / 黑体 / 苹方 / Noto / 文泉驿）。
    """
    import sys as _sys
    from PIL import ImageFont

    if _sys.platform == "win32":
        candidates = [
            r"C:\Windows\Fonts\msyh.ttc",
            r"C:\Windows\Fonts\simhei.ttf",
            r"C:\Windows\Fonts\simsun.ttc",
            r"C:\Windows\Fonts\arial.ttf",
        ]
    elif _sys.platform == "darwin":
        candidates = [
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/STHeiti Light.ttc",
            "/Library/Fonts/Arial Unicode.ttf",
        ]
    else:
        candidates = [
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]

    for c in candidates:
        if os.path.exists(c):
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                pass
    try:
        return ImageFont.truetype("arial.ttf", size)
    except Exception:
        return ImageFont.load_default()
