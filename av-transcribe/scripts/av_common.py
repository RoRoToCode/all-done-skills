"""音视频转写 共享工具：ffmpeg/ffprobe 定位、依赖守卫、不覆盖输入、结果输出。"""
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
    """ffprobe 缺失时从 ffmpeg 的 stderr 抠时长与分辨率，解析不到就给 None。"""
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
    """返回 (duration 秒, width, height)，失败返回 (None, None, None)。"""
    ffprobe = ffprobe_path()
    if not ffprobe:
        return _probe_via_ffmpeg(inp)
    cmd = [ffprobe, "-v", "error",
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
