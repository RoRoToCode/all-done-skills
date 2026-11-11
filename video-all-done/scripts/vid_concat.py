"""vid-concat：多段视频首尾拼接合并。"""
import argparse
import glob
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vid_common import need_ffmpeg, no_overwrite, ensure_parent, result, probe


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", required=True, help="逗号分隔的视频路径或通配符")
    ap.add_argument("--output", required=True)
    ap.add_argument("--reencode", action="store_true", help="重编码（编码不一致时必选）")
    args = ap.parse_args()

    files = []
    for part in args.inputs.split(","):
        part = part.strip()
        if not part:
            continue
        matched = glob.glob(part)
        if matched:
            files += sorted(matched)
        elif os.path.exists(part):
            files.append(part)

    if len(files) < 2:
        sys.stderr.write("至少需要 2 个输入片段，收到 %d 个。\n" % len(files))
        sys.exit(3)
    for f in files:
        no_overwrite(f, args.output)

    ffmpeg = need_ffmpeg()
    ensure_parent(args.output)

    lst = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8")
    try:
        for f in files:
            lst.write("file '%s'\n" % os.path.abspath(f))
        lst.close()
        cmd = [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", lst.name]
        if args.reencode:
            cmd += ["-c:v", "libx264", "-c:a", "aac"]
        else:
            cmd += ["-c", "copy"]
        cmd += [args.output]
        rc = subprocess.run(cmd).returncode
    finally:
        try:
            os.unlink(lst.name)
        except Exception:
            pass

    if rc == 0:
        d, w, h = probe(args.output)
        result(args.output, d, w, h)
    sys.exit(rc)


if __name__ == "__main__":
    main()
