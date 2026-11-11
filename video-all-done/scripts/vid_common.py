"""视频动作共享工具：ffmpeg/ffprobe 定位、依赖守卫、不覆盖输入、结果输出，
以及幻灯片 / 文字卡片的渲染与合成。"""
import os
import re
import shutil
import subprocess
import sys
import tempfile


# ----------------------------------------------------------------------------
# 依赖定位
# ----------------------------------------------------------------------------
# ffmpeg / ffprobe 解析顺序：环境变量 → PATH → ~/.workbuddy/bin → imageio-ffmpeg 自带副本。
# 很多机器装有 ffmpeg 但没进 PATH（或装在某个 Python 包里），只查 which 会误报缺失。
BIN_DIRS = [os.path.join(os.path.expanduser("~"), ".workbuddy", "bin")]


def _resolve_binary(name):
    override = os.environ.get(name.upper())
    if override and os.path.isfile(override):
        return override
    found = shutil.which(name) or shutil.which(name + ".exe")
    if found:
        return found
    for folder in BIN_DIRS:
        for candidate in (name, name + ".exe"):
            path = os.path.join(folder, candidate)
            if os.path.isfile(path):
                return path
    if name == "ffmpeg":
        try:
            import imageio_ffmpeg
            return imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            pass
    return None


def ffmpeg_path():
    return _resolve_binary("ffmpeg")


def ffprobe_path():
    return _resolve_binary("ffprobe")


def filter_path(path):
    r"""把文件路径转成可以安全塞进 ffmpeg 滤镜参数的写法（含外层单引号）。

    Windows 盘符里的冒号会被当成滤镜选项分隔符，只有反斜杠不够——实测
    ``subtitles=F\:/a/b.srt`` 仍会被拆成 ``F:`` + ``/a/b.srt``，必须整体用
    单引号包住。所以这里返回 ``'F\:/a/b.srt'`` 这种形式。
    """
    text = os.path.abspath(path).replace("\\", "/")
    text = text.replace("'", "'\\''")
    text = text.replace(":", "\\:")
    return "'%s'" % text


def need_ffmpeg():
    p = ffmpeg_path()
    if not p:
        sys.stderr.write(
            "缺少依赖 ffmpeg，按任一方式补上即可：\n"
            "  1) python -m pip install imageio-ffmpeg   （Python 包自带 ffmpeg 二进制）\n"
            "  2) winget install Gyan.FFmpeg             （装完重开终端）\n"
            "  3) 手动下载 https://ffmpeg.org 后把 ffmpeg.exe 放到 %s\n"
            % BIN_DIRS[0])
        sys.exit(2)
    return p


def need_ffprobe():
    """ffprobe 只用于回填时长/分辨率等元信息，缺失时不该中断主流程。

    以前这里直接 sys.exit(2)，导致 aud-split / aud-fade / aud-info 在只有
    ffmpeg 的机器上完全不能用；现在返回 None，由 probe() 走 ffmpeg 解析兜底。
    """
    return ffprobe_path()


def need_pillow():
    try:
        from PIL import Image, ImageDraw, ImageFont
        return Image
    except Exception:
        sys.stderr.write("缺少依赖 Pillow：请运行  pip install Pillow\n")
        sys.exit(2)


# ----------------------------------------------------------------------------
# 通用守卫
# ----------------------------------------------------------------------------
def no_overwrite(inp, out):
    if os.path.abspath(inp) == os.path.abspath(out):
        sys.stderr.write("输出不得等于输入：%s\n" % inp)
        sys.exit(3)


def ensure_parent(out):
    d = os.path.dirname(os.path.abspath(out))
    if d:
        os.makedirs(d, exist_ok=True)


def run(cmd, capture=False):
    """运行命令；capture=True 时返回 (returncode, stdout)。"""
    if capture:
        proc = subprocess.run(cmd, capture_output=True, text=True)
        return proc.returncode, proc.stdout
    return subprocess.run(cmd).returncode


def _probe_via_ffmpeg(inp):
    """ffprobe 缺失时的兜底：从 ffmpeg 的 stderr 里抠时长与分辨率。

    ffmpeg 没有 JSON 输出，这里是正则解析，只保证拿到最常见的两个字段；
    解析不到就给 None，绝不编造数值。
    """
    ff = ffmpeg_path()
    if not ff:
        return (None, None, None)
    proc = subprocess.run([ff, "-hide_banner", "-i", inp],
                          capture_output=True, text=True)
    text = (proc.stderr or "") + (proc.stdout or "")
    dur = w = h = None
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", text)
    if m:
        dur = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    m = re.search(r"Video:.*?(\d{2,5})x(\d{2,5})", text)
    if m:
        w, h = int(m.group(1)), int(m.group(2))
    return (dur, w, h)


def probe(inp):
    """返回 (duration 秒, width, height)，失败返回 (None, None, None)。

    注意：ffprobe 缺失时**不**致命退出——转换/生成本身可能已由 ffmpeg 成功完成，
    只是无法回填时长/分辨率；此时返回 None 让调用方安静降级。
    """
    fp = ffprobe_path()
    if not fp:
        return _probe_via_ffmpeg(inp)
    cmd = [fp, "-v", "error",
           "-show_entries", "format=duration:stream=width,height",
           "-of", "default=noprint_wrappers=1", inp]
    rc, out = run(cmd, capture=True)
    if rc != 0:
        return (None, None, None)
    dur = w = h = None
    for line in out.splitlines():
        if line.startswith("duration="):
            try:
                dur = float(line.split("=", 1)[1])
            except Exception:
                pass
        elif line.startswith("width="):
            try:
                w = int(line.split("=", 1)[1])
            except Exception:
                pass
        elif line.startswith("height="):
            try:
                h = int(line.split("=", 1)[1])
            except Exception:
                pass
    return (dur, w, h)


def result(path, duration=None, w=None, h=None):
    size = os.path.getsize(path)
    parts = ["已保存 %s" % path]
    if duration is not None:
        parts.append("时长=%.2f秒" % duration)
    if w and h:
        parts.append("分辨率=%dx%d" % (w, h))
    parts.append("体积=%d 字节" % size)
    print("  ".join(parts))


# ----------------------------------------------------------------------------
# Pillow 字体 / 渲染
# ----------------------------------------------------------------------------
def load_pil_font(size):
    """返回能渲染中文的 PIL 字体；找不到系统字体则回退默认字体。"""
    from PIL import ImageFont
    if sys.platform == "win32":
        candidates = [
            r"C:\Windows\Fonts\msyh.ttc",
            r"C:\Windows\Fonts\simhei.ttf",
            r"C:\Windows\Fonts\simsun.ttc",
            r"C:\Windows\Fonts\arial.ttf",
        ]
    elif sys.platform == "darwin":
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


def wrap_text(draw, text, font, max_w):
    """按像素宽度换行；保留显式换行符。"""
    lines = []
    for para in text.split("\n"):
        if not para:
            lines.append("")
            continue
        line = ""
        for ch in para:
            test = line + ch
            if draw.textlength(test, font=font) <= max_w:
                line = test
            else:
                if line:
                    lines.append(line)
                line = ch
        lines.append(line)
    return lines


def hex_rgb(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def cover_fit(src, dst, W, H, bg="#000000"):
    """把图片等比铺满 WxH（cover），多余部分居中裁掉。"""
    Image = need_pillow()
    im = Image.open(src).convert("RGB")
    sw, sh = im.size
    scale = max(W / sw, H / sh)
    nw, nh = int(round(sw * scale)), int(round(sh * scale))
    im = im.resize((nw, nh), Image.LANCZOS)
    canvas = Image.new("RGB", (W, H), bg)
    canvas.paste(im, ((W - nw) // 2, (H - nh) // 2))
    canvas.save(dst)
    return dst


def render_text_card(W, H, title, body, bg="#10142b", fg="#ffffff",
                     accent="#5b8cff", title_size=None, body_size=None):
    """渲染一张文字卡片为 PIL Image。"""
    Image = need_pillow()
    from PIL import ImageDraw
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)
    tsize = title_size or max(28, H // 10)
    bsize = body_size or max(18, H // 22)
    tfont = load_pil_font(tsize)
    bfont = load_pil_font(bsize)

    pad = int(W * 0.08)
    # 顶部装饰条
    d.rectangle([pad, int(H * 0.16), pad + int(W * 0.18), int(H * 0.16) + max(6, H // 80)],
                fill=accent)

    if title:
        tlines = wrap_text(d, title, tfont, W - 2 * pad)
        ty = int(H * 0.22)
        for ln in tlines:
            d.text((pad, ty), ln, font=tfont, fill=fg)
            ty += int(tsize * 1.25)

    if body:
        blines = wrap_text(d, body, bfont, W - 2 * pad)
        by = int(H * 0.45)
        for ln in blines:
            d.text((pad, by), ln, font=bfont, fill=fg)
            by += int(bsize * 1.4)
    return img


# ----------------------------------------------------------------------------
# 合成：图片序列 -> 视频
# ----------------------------------------------------------------------------
def image_to_clip(png, out_mp4, duration, fps, ffmpeg, kenburns, W, H):
    """把一张图（已是 WxH）转成固定时长的 mp4 片段。"""
    cmd = [ffmpeg, "-y", "-loop", "1", "-i", png,
           "-t", str(duration), "-r", str(fps), "-pix_fmt", "yuv420p"]
    if kenburns:
        d = int(round(duration * fps))
        zp = ("zoompan=z='min(zoom+0.0015,1.12)':d=%d:s=%dx%d:fps=%d:"
              "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'" % (d, W, H, fps))
        cmd += ["-vf", zp]
    cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", out_mp4]
    rc = run(cmd)
    if rc != 0:
        sys.stderr.write("生成片段失败：%s\n" % out_mp4)
        sys.exit(5)
    return out_mp4


def _build_xfade_filter(n, L, t, trans):
    """构建把 n 个等长(L)片段用 transition 衔接的 filter_complex 字符串，
    返回 (filter_str, last_label)。

    n == 1 时没有转场可做，返回 (None, "0:v")；调用方必须跳过
    -filter_complex，并直接用 0:v 作 -map 值（写成 "[0:v]" 会被
    ffmpeg 当成滤镜标签而报 Invalid argument）。
    """
    if n == 1:
        return None, "0:v"
    last = "[0:v]"
    stages = []
    for k in range(1, n):
        out = "[v%d]" % k
        offset = k * (L - t)
        stages.append("%s[%d:v]xfade=transition=%s:duration=%s:offset=%s%s"
                      % (last, k, trans, t, offset, out))
        last = out
    # 每一段 xfade 之间必须有分号，否则第 2 段起会被当成上一段的尾巴，
    # ffmpeg 报 "Trailing garbage after a filter"（n>=3 才会暴露）。
    return ";".join(stages), last


def concat_via_demuxer(mp4s, output, ffmpeg):
    """用 concat demuxer 直接拼接（流拷贝，最快）。"""
    lst = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8")
    try:
        for m in mp4s:
            lst.write("file '%s'\n" % os.path.abspath(m))
        lst.close()
        cmd = [ffmpeg, "-y", "-f", "concat", "-safe", "0",
               "-i", lst.name, "-c", "copy", output]
        rc = run(cmd)
    finally:
        try:
            os.unlink(lst.name)
        except Exception:
            pass
    if rc != 0:
        sys.stderr.write("拼接失败。\n")
        sys.exit(5)
    return output


def concat_via_xfade(mp4s, output, L, t, trans, fps, audio, ffmpeg):
    """用 xfade 做淡入淡出转场拼接；可选循环背景音乐。"""
    n = len(mp4s)
    flt, last = _build_xfade_filter(n, L, t, trans)
    cmd = [ffmpeg, "-y"]
    for m in mp4s:
        cmd += ["-i", m]
    if audio:
        cmd += ["-stream_loop", "-1", "-i", audio]
    if flt:  # 只有一段素材时没有滤镜链，直接映射原流
        cmd += ["-filter_complex", flt]
    # 有滤镜时 last 是 "[vN]" 标签；无滤镜时是 "0:v"，前面不能带方括号
    cmd += ["-map", last, "-pix_fmt", "yuv420p"]
    cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20"]
    if audio:
        cmd += ["-map", "%d:a" % n, "-c:a", "aac", "-shortest"]
    cmd += [output]
    rc = run(cmd)
    if rc != 0:
        sys.stderr.write("转场拼接失败。\n")
        sys.exit(5)
    return output


def assemble(png_paths, output, duration, transition, fade_dur, fps,
             audio, kenburns, W, H, ffmpeg):
    """把一批图（已 WxH）合成为视频，返回输出路径。"""
    tmp = tempfile.mkdtemp(prefix="vid_")
    try:
        clips = []
        for i, p in enumerate(png_paths):
            clip = os.path.join(tmp, "clip_%03d.mp4" % i)
            image_to_clip(p, clip, duration, fps, ffmpeg, kenburns, W, H)
            clips.append(clip)
        if transition == "none" or fade_dur <= 0:
            concat_via_demuxer(clips, output, ffmpeg)
        else:
            concat_via_xfade(clips, output, duration, fade_dur, "fade", fps,
                             audio, ffmpeg)
    finally:
        for f in os.listdir(tmp):
            try:
                os.unlink(os.path.join(tmp, f))
            except Exception:
                pass
        try:
            os.rmdir(tmp)
        except Exception:
            pass
    return output
