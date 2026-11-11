"""img-batch：对目录下全部图片批量套用同一动作（convert/compress/resize）。"""
import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EXTS = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--action", required=True, choices=["convert", "compress", "resize"])
    ap.add_argument("--ext", default="jpg", help="convert 的输出扩展名")
    ap.add_argument("--quality", type=int, default=75)
    ap.add_argument("--long-edge", type=int, default=None)
    ap.add_argument("--scale", type=float, default=None)
    args = ap.parse_args()

    if not os.path.isdir(args.input_dir):
        sys.stderr.write("输入目录不存在：%s\n" % args.input_dir)
        sys.exit(1)
    os.makedirs(args.output_dir, exist_ok=True)

    files = sorted(f for f in os.listdir(args.input_dir)
                  if f.lower().endswith(EXTS) and os.path.isfile(os.path.join(args.input_dir, f)))
    if not files:
        print("目录中无图片文件。")
        return

    ok = 0
    for f in files:
        src = os.path.join(args.input_dir, f)
        if args.action == "convert":
            dst = os.path.join(args.output_dir, os.path.splitext(f)[0] + "." + args.ext)
            cmd = [sys.executable, os.path.join(HERE, "img_convert.py"),
                   "--input", src, "--output", dst, "--quality", str(args.quality)]
        elif args.action == "compress":
            dst = os.path.join(args.output_dir, f)
            cmd = [sys.executable, os.path.join(HERE, "img_compress.py"),
                   "--input", src, "--output", dst, "--quality", str(args.quality)]
        else:
            dst = os.path.join(args.output_dir, f)
            cmd = [sys.executable, os.path.join(HERE, "img_resize.py"),
                   "--input", src, "--output", dst]
            if args.long_edge:
                cmd += ["--long-edge", str(args.long_edge)]
            elif args.scale:
                cmd += ["--scale", str(args.scale)]
            else:
                sys.stderr.write("resize 需提供 --long-edge 或 --scale\n")
                sys.exit(1)
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0:
            ok += 1
            print("[OK]   %s" % f)
        else:
            print("[FAIL] %s\n%s" % (f, r.stderr.strip()))

    print("批量完成：%d/%d 成功，输出目录 %s" % (ok, len(files), args.output_dir))


if __name__ == "__main__":
    main()
