#!/usr/bin/env python3
"""Check or install the optional dependencies used by av_transcribe.py.

两个层次的依赖：
  - ffmpeg / ffprobe：外部二进制，必须已在 PATH 上；本脚本只检查、不代装
    （Windows 下 pip 装不了可靠的 ffmpeg，交给 scoop/choco/官网）。
  - openai-whisper：Python 包（会连带 torch），默认装进技能目录之外的隔离
    venv，避免打包技能时把体积巨大的环境一并带走。

仅在你已告知用户「会从 PyPI 下载依赖」后运行 `install`。
faster-whisper 是可选替代，本脚本不预装，用户可自行 `pip install faster-whisper`。
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import venv
from pathlib import Path

DEFAULT_VENV = Path.home() / ".workbuddy" / "av-transcribe-env"
REQUIREMENT = "openai-whisper"


def venv_path():
    return Path(os.environ.get("AV_TRANSCRIBE_VENV", str(DEFAULT_VENV))).resolve()


def venv_python(root):
    if os.name == "nt":
        return root / "Scripts" / "python.exe"
    return root / "bin" / "python"


def _which(name):
    return shutil.which(name) or shutil.which(name + ".exe")


def _module_ok(py, code):
    proc = subprocess.run([py, "-c", code], capture_output=True, text=True)
    return proc.returncode == 0


def _whisper_status():
    # 当前解释器
    try:
        import whisper  # noqa: F401
        return {"status": "ok", "source": "current interpreter", "engine": "openai-whisper"}
    except Exception:
        pass
    try:
        import faster_whisper  # noqa: F401
        return {"status": "ok", "source": "current interpreter", "engine": "faster-whisper"}
    except Exception:
        pass
    # 隔离 venv
    root = venv_path()
    python = venv_python(root)
    if python.exists():
        probe = ("import importlib.util,sys;"
                 "sys.exit(0 if (importlib.util.find_spec('whisper') or "
                 "importlib.util.find_spec('faster_whisper')) else 1)")
        if _module_ok(str(python), probe):
            return {"status": "ok", "source": "isolated venv", "python": str(python)}
    return {"status": "missing", "python": str(python)}


def check():
    info = {
        "ffmpeg": _which("ffmpeg"),
        "ffprobe": _which("ffprobe"),
        "whisper": _whisper_status(),
    }
    ok = (bool(info["ffmpeg"]) and bool(info["ffprobe"])
          and info["whisper"]["status"] == "ok")
    print(json.dumps(info, ensure_ascii=False, indent=2))
    if not info["ffmpeg"] or not info["ffprobe"]:
        print("提示：ffmpeg / ffprobe 需单独安装并加入 PATH"
              "（scoop install ffmpeg 或官网下载）。", file=sys.stderr)
    return 0 if ok else 2


def install(args):
    if args.system:
        cmd = [sys.executable, "-m", "pip", "install", "--user", REQUIREMENT]
        python = sys.executable
    else:
        root = venv_path()
        root.parent.mkdir(parents=True, exist_ok=True)
        if not venv_python(root).exists():
            venv.EnvBuilder(with_pip=True).create(str(root))
        python = str(venv_python(root))
        cmd = [python, "-m", "pip", "install", "--disable-pip-version-check",
               REQUIREMENT]
    proc = subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    ok = proc.returncode == 0
    print(json.dumps({"status": "ok" if ok else "error", "python": python,
                      "stdout": proc.stdout[-800:], "stderr": proc.stderr[-800:]},
                     ensure_ascii=False))
    if ok and not args.system:
        print("后续请用该解释器运行转写：%s scripts/av_transcribe.py ..." % python,
              file=sys.stderr)
    print("注意：ffmpeg / ffprobe 不在本安装范围内，请确保它们在 PATH 上。",
          file=sys.stderr)
    return 0 if ok else 1


def main():
    p = argparse.ArgumentParser(description="管理 av-transcribe 依赖")
    sub = p.add_subparsers(dest="action", required=True)
    sub.add_parser("check", help="检查 ffmpeg / whisper 是否就绪")
    i = sub.add_parser("install", help="安装 openai-whisper")
    i.add_argument("--system", action="store_true",
                   help="装进当前解释器（--user），而不是隔离 venv")
    args = p.parse_args()
    return check() if args.action == "check" else install(args)


if __name__ == "__main__":
    sys.exit(main())
