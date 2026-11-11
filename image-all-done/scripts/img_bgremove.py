"""img-bgremove：智能抠图 / 去背景，输出透明 PNG（本地 rembg 模型）。"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from img_common import need_pillow, no_overwrite, save_image, result, guard_import


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--model", default="u2net", help="rembg 模型名")
    args = ap.parse_args()

    need_pillow()
    no_overwrite(args.input, args.output)
    rembg = guard_import("rembg", "pip install rembg  （首次运行会自动下载模型）")
    from rembg import remove
    from PIL import Image

    img = Image.open(args.input)
    # rembg 2.0 的 remove() 直接把参数转给 new_session()，再用关键字传
    # model_name 会报 "got multiple values"；而且它的默认模型换成了
    # bria-rmbg（约 1GB），国内网络基本拉不动。这里显式建 session 并指定
    # 模型，新旧版本都能用，默认仍是 176MB 的 u2net。
    try:
        from rembg import new_session
        session = new_session(args.model)
        out = remove(img, session=session)
    except ImportError:
        out = remove(img, model_name=args.model)
    except TypeError:
        out = remove(img, args.model)
    except Exception as exc:
        home = os.environ.get("U2NET_HOME") or os.path.join(
            os.path.expanduser("~"), ".u2net")
        sys.stderr.write(
            "抠图失败：%s\n"
            "  首次运行要下载模型 %s（u2net ≈176MB，bria-rmbg ≈1GB）。\n"
            "  rembg 2.x 从 GitHub Release 拉模型，国内常常超时；两条路任选：\n"
            "    1) 走代理让上面的下载成功，然后重跑一次；\n"
            "    2) 手动下载 %s.onnx 放到 %s\\%s.onnx 后重跑。\n"
            "  （这个目录可用环境变量 U2NET_HOME 改到别处）\n"
            % (exc, args.model, args.model, home, args.model))
        sys.exit(5)
    if os.path.splitext(args.output)[1].lower().lstrip(".") not in ("png",):
        sys.stderr.write("去背景输出含透明通道，建议输出为 .png\n")
    save_image(out, args.output)
    result(args.output, out)


if __name__ == "__main__":
    main()
