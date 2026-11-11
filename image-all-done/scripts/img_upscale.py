"""img-upscale：图片高清放大 / 修复。

优先用本地 AI 模型 Real-ESRGAN（需 pip install realesrgan，首次运行下载权重）；
若不可用则自动回退到双三次插值（Pillow），保证动作始终可跑。
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from img_common import need_pillow, no_overwrite, save_image, result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--scale", type=int, default=4, choices=[2, 4])
    ap.add_argument("--ai", dest="ai", action="store_true", default=True,
                    help="尝试 AI 超分（默认开）")
    ap.add_argument("--no-ai", dest="ai", action="store_false", help="仅用插值")
    args = ap.parse_args()

    Image = need_pillow()
    no_overwrite(args.input, args.output)
    img = Image.open(args.input).convert("RGB")
    w, h = img.size

    used_ai = False
    if args.ai:
        try:
            from realesrgan import RealESRGANer
            from basicsr.archs.rrdbnet_arch import RRDBNet
            from PIL import Image as _I
            model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64,
                           num_block=23, num_grow_ch=32, scale=args.scale)
            upscaler = RealESRGANer(scale=args.scale, model_path=None,
                                    model=model, tile=0, tile_pad=10,
                                    pre_pad=0, half=False)
            out, _ = upscaler.enhance(img, outscale=args.scale)
            used_ai = True
        except Exception as e:
            print("AI 超分不可用（%s），回退到双三次插值。" % type(e).__name__)

    if not used_ai:
        out = img.resize((w * args.scale, h * args.scale), Image.BICUBIC)

    save_image(out, args.output, quality=90, optimize=True)
    result(args.output, out)
    if not used_ai:
        print("提示：安装 realesrgan 后可获得 AI 级画质（pip install realesrgan）。")


if __name__ == "__main__":
    main()
