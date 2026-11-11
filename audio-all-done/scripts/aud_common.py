"""音频动作共享工具：ffmpeg/ffprobe 定位、依赖守卫、不覆盖输入、时间解析、
输出编码参数推断、探测信息与结果输出。纯标准库，无第三方 Python 依赖。"""
import json
import os
import re
import shutil
import subprocess
import sys


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


# ----------------------------------------------------------------------------
# 通用守卫
# ----------------------------------------------------------------------------
def no_overwrite(inp, out):
    if os.path.abspath(inp) == os.path.abspath(out):
        sys.stderr.write("输出不得等于输入：%s\n" % inp)
        sys.exit(3)


def require_input(path):
    if not os.path.isfile(path):
        sys.stderr.write("输入文件不存在或不是文件：%s\n" % path)
        sys.exit(3)


def ensure_parent(out):
    d = os.path.dirname(os.path.abspath(out))
    if d:
        os.makedirs(d, exist_ok=True)


def unique_path(path):
    """输出名与已有文件冲突时自动加 " (2)" / " (3)"，绝不覆盖旧产物。"""
    if not os.path.exists(path):
        return path
    stem, ext = os.path.splitext(path)
    n = 2
    while os.path.exists("%s (%d)%s" % (stem, n, ext)):
        n += 1
    return "%s (%d)%s" % (stem, n, ext)


def ensure_dir(path):
    if os.path.exists(path) and not os.path.isdir(path):
        sys.stderr.write("输出路径已存在且不是目录：%s\n" % path)
        sys.exit(3)
    os.makedirs(path, exist_ok=True)


def run(cmd, capture=False):
    """运行命令；capture=True 时返回 (returncode, stdout, stderr)。"""
    if capture:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
        return proc.returncode, proc.stdout or "", proc.stderr or ""
    return subprocess.run(cmd).returncode


def fail(msg, code=5):
    sys.stderr.write(msg.rstrip() + "\n")
    sys.exit(code)


# ----------------------------------------------------------------------------
# 时间与格式
# ----------------------------------------------------------------------------
def parse_time(s):
    """把 5 / 5.0 / 00:00:05 / 01:30.5 解析成秒；失败返回 None。"""
    if s is None:
        return None
    s = str(s).strip()
    if not s:
        return None
    try:
        if ":" in s:
            sec = 0.0
            for part in s.split(":"):
                sec = sec * 60 + float(part)
            return sec
        return float(s)
    except (ValueError, TypeError):
        return None


def hms(sec):
    if sec is None:
        return "?"
    sec = max(float(sec), 0)
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return "%02d:%02d:%06.3f" % (h, m, s)


def atempo_chain(speed):
    """atempo 只接受 0.5-2.0；把极端倍率拆成多个因子串联。"""
    if abs(speed - 1.0) < 1e-9:
        return "atempo=1.0"
    factors = []
    r = float(speed)
    while r > 2.0:
        factors.append(2.0)
        r /= 2.0
    while r < 0.5:
        factors.append(0.5)
        r /= 0.5
    factors.append(r)
    return ",".join("atempo=%.6g" % f for f in factors)


# ----------------------------------------------------------------------------
# 输出编码推断
# ----------------------------------------------------------------------------
DEFAULT_CODEC = {
    ".mp3": "libmp3lame",
    ".m4a": "aac",
    ".aac": "aac",
    ".mp4": "aac",
    ".wav": "pcm_s16le",
    ".flac": "flac",
    ".ogg": "libvorbis",
    ".oga": "libvorbis",
    ".opus": "libopus",
    ".wma": "wmav2",
    ".aiff": "pcm_s16be",
}
LOSSY_EXTS = {".mp3", ".m4a", ".aac", ".mp4", ".ogg", ".oga", ".opus", ".wma"}
PCM_CODEC = {
    16: {".wav": "pcm_s16le", ".aiff": "pcm_s16be"},
    24: {".wav": "pcm_s24le", ".aiff": "pcm_s24be"},
    32: {".wav": "pcm_s32le", ".aiff": "pcm_s32be"},
    "float": {".wav": "pcm_f32le", ".aiff": "pcm_f32be"},
}


def audio_encode_args(output, codec=None, bitrate="192k", sample_rate=None,
                      channels=None, bit_depth=None):
    """按输出扩展名生成 ffmpeg 输出侧参数片段。

    无损格式（wav / flac / aiff）不传码率；--codec 显式指定时优先。
    """
    ext = os.path.splitext(output)[1].lower()
    c = codec or DEFAULT_CODEC.get(ext)
    if bit_depth is not None and codec is None and ext in (".wav", ".aiff"):
        key = int(bit_depth) if str(bit_depth) != "float" else "float"
        c = PCM_CODEC.get(key, {}).get(ext, c)
    args = []
    if c:
        args += ["-c:a", c]
    if bitrate and ext in LOSSY_EXTS:
        args += ["-b:a", str(bitrate)]
    if sample_rate:
        args += ["-ar", str(sample_rate)]
    if channels:
        args += ["-ac", str(channels)]
    return args


# ----------------------------------------------------------------------------
# 探测信息
# ----------------------------------------------------------------------------
def _probe_via_ffmpeg(inp):
    """ffprobe 缺失时的兜底：解析 ffmpeg 的 stderr（无 JSON 输出）。"""
    ff = ffmpeg_path()
    if not ff:
        return {}
    proc = subprocess.run([ff, "-hide_banner", "-i", inp],
                          capture_output=True, text=True)
    text = (proc.stderr or "") + (proc.stdout or "")
    info = {"source": "ffmpeg"}
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", text)
    if m:
        info["duration"] = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    m = re.search(r"Audio:\s*([A-Za-z0-9_\-]+).*?,?\s*(\d+)\s*Hz,\s*([^,\n]+)", text)
    if m:
        info["codec"] = m.group(1)
        info["sample_rate"] = int(m.group(2))
        info["channel_layout"] = m.group(3).strip()
    return info if len(info) > 1 else {}


def probe(inp):
    """返回音频信息 dict；ffprobe 缺失或解析失败时安静返回 {}。"""
    fp = ffprobe_path()
    if not fp:
        return _probe_via_ffmpeg(inp)
    cmd = [fp, "-v", "error", "-show_format", "-show_streams",
           "-of", "json", inp]
    rc, out, _ = run(cmd, capture=True)
    if rc != 0 or not out.strip():
        return {}
    try:
        data = json.loads(out)
    except Exception:
        return {}
    fmt = data.get("format") or {}
    streams = data.get("streams") or []
    st = next((s for s in streams if s.get("codec_type") == "audio"), None) or {}

    def num(v):
        try:
            f = float(v)
            return f if f > 0 else None
        except (ValueError, TypeError):
            return None

    return {
        "duration": num(fmt.get("duration") or st.get("duration")),
        "sample_rate": int(st["sample_rate"]) if st.get("sample_rate") else None,
        "channels": st.get("channels"),
        "channel_layout": st.get("channel_layout"),
        "codec": st.get("codec_name"),
        "codec_long": st.get("codec_long_name"),
        "bit_rate": num(fmt.get("bit_rate") or st.get("bit_rate")),
        "bits_per_sample": st.get("bits_per_sample"),
        "format_name": fmt.get("format_name"),
        "size": num(fmt.get("size")),
        "tags": fmt.get("tags") or st.get("tags") or {},
        "streams": streams,
        "format": fmt,
    }


def result(path, duration=None, sample_rate=None, channels=None, extra=None):
    if not os.path.exists(path):
        fail("未生成产物：%s" % path)
    size = os.path.getsize(path)
    parts = ["已保存 %s" % path]
    if duration is not None:
        parts.append("时长=%.2f秒" % duration)
    if sample_rate:
        parts.append("采样率=%d Hz" % sample_rate)
    if channels:
        parts.append("声道=%d" % channels)
    parts.append("体积=%d 字节" % size)
    if extra:
        parts.append(extra)
    print("  ".join(parts))
