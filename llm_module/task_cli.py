"""自然语言任务解析命令行入口。"""

from __future__ import annotations

import argparse

from .client import LLMError
from .task_parser import parse_task


def main() -> None:
    parser = argparse.ArgumentParser(description="把自然语言解析为 CityEye 任务 JSON")
    parser.add_argument("question", help="用户自然语言问题")
    args = parser.parse_args()
    try:
        result = parse_task(args.question)
    except LLMError as exc:
        raise SystemExit(f"解析失败：{exc}") from exc
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
