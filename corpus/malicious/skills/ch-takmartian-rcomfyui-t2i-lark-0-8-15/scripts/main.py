import argparse
import os
import sys
import t2i
import lark_send


def parse_args():
    parser = argparse.ArgumentParser(description="ComfyUI t2i → Lark Sender")
    parser.add_argument("--chat_id", type=str, help="Lark chat ID (oc_) or open ID (ou_)")
    parser.add_argument("--positive_prompt", type=str, default="", help="Positive prompt for image generation")
    parser.add_argument("--negative_prompt", type=str, default="", help="Negative prompt for image generation")
    parser.add_argument("--selfee", action="store_true", help="Use selfee model/size from config.ini")
    return parser.parse_args()


def validate(args):
    if not args.chat_id:
        print("Error: --chat_id is required", file=sys.stderr)
        sys.exit(1)
    if not args.positive_prompt:
        print("Error: --positive_prompt is required", file=sys.stderr)
        sys.exit(1)


def _run(args):
    try:
        generated_image_path = t2i.start(args.positive_prompt, args.negative_prompt, selfee=args.selfee)
        lark_send.start(generated_image_path, args.chat_id)
    except Exception:
        import traceback
        log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output", "error.log")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a") as f:
            traceback.print_exc(file=f)


def main():
    args = parse_args()
    validate(args)

    pid = os.fork()
    if pid > 0:
        print("OK")
        sys.exit(0)

    # 子进程：脱离终端，后台执行
    os.setsid()
    with open(os.devnull, 'r') as dn:
        os.dup2(dn.fileno(), sys.stdin.fileno())
    with open(os.devnull, 'w') as dn:
        os.dup2(dn.fileno(), sys.stdout.fileno())
        os.dup2(dn.fileno(), sys.stderr.fileno())

    _run(args)


if __name__ == "__main__":
    main()

# 运行示例：
# python main.py --chat_id "oc_05c5e4841b334bc11ec0a5c6678a1d7b" --positive_prompt "masterpiece, best quality, 1girl, solo, looking at viewer, smile"