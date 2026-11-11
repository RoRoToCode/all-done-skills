"""vid-extract-audio：从视频提取音轨。"""
import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vid_common import need_ffmpeg, no_overwrite, ensure_parent, result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--format", default="aac", choices=["mp3", "aac", "m4a", "wav", "ogg"])
    args = ap.parse_args()

    ffmpeg = need_ffmpeg()
    no_overwrite(args.input, args.output)
    ensure_parent(args.output)

    codec = {"mp3": "libmp3lame", "aac": "aac", "m4a": "aac",
             "wav": "pcm_s16le", "ogg": "libvorbis"}[args.format]
    cmd = [ffmpeg, "-y", "-i", args.input, "-vn", "-acodec", codec, args.output]
    rc = subprocess.run(cmd).returncode
    if rc == 0:
        print("已保存 %s  体积=%d 字节" % (args.output, os.path.getsize(args.output)))
    sys.exit(rc)


if __name__ == "__main__":
    main()
