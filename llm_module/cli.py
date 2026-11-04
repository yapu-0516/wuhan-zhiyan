"""命令行调用入口。"""

from __future__ import annotations

import argparse

from .client import LLMError, ask


def main() -> None:
    parser = argparse.ArgumentParser(description="调用 DeepSeek")
    parser.add_argument("prompt", help="要发送给模型的问题")
    parser.add_argument("--system", default=None, help="可选的系统提示词")
    args = parser.parse_args()
    try:
        print(ask(args.prompt, system_prompt=args.system))
    except LLMError as exc:
        raise SystemExit(f"调用失败：{exc}") from exc


if __name__ == "__main__":
    main()
