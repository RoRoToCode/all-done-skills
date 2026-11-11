"""aud-concat：多段音频首尾拼接合并。"""
import argparse
import glob
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aud_common import (need_ffmpeg, no_overwrite, require_input, ensure_parent,
                        run, fail, result, probe, audio_encode_args)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", required=True, help="逗号分隔的音频路径或通配符（按顺序）")
    ap.add_argument("--output", required=True)
    ap.add_argument("--reencode", action="store_true", help="重编码（各段编码/采样率不一致时必选）")
    ap.add_argument("--bitrate", default="192k")
    args = ap.parse_args()

    files = []
    for part in args.inputs.split(","):
        part = part.strip()
        if not part:
            continue
        matched = glob.glob(part)
        if matched:
            files += sorted(matched)
        elif os.path.isfile(part):
            files.append(part)
    if len(files) < 2:
        fail("至少需要 2 个输入片段，收到 %d 个。" % len(files), 3)

    ffmpeg = need_ffmpeg()
    for f in files:
        require_input(f)
        no_overwrite(f, args.output)
    ensure_parent(args.output)

    lst = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8")
    try:
        for f in files:
            lst.write("file '%s'\n" % os.path.abspath(f).replace("\\", "/"))
        lst.close()
        cmd = [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", lst.name,
               "-map", "0:a:0"]
        if args.reencode:
            cmd += audio_encode_args(args.output, bitrate=args.bitrate)
        else:
            cmd += ["-c", "copy"]
        cmd += [args.output]
        rc = run(cmd)
    finally:
        try:
            os.unlink(lst.name)
        except Exception:
            pass

    if rc != 0:
        fail("拼接失败（ffmpeg 退出码 %d）；各段编码不一致时请加 --reencode。" % rc)
    info = probe(args.output)
    result(args.output, info.get("duration"), info.get("sample_rate"),
           info.get("channels"), "合并=%d 段" % len(files))


if __name__ == "__main__":
    main()
