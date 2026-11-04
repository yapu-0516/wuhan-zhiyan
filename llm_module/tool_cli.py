"""Tool Calling 命令行测试入口。"""

from __future__ import annotations

import argparse
import json

from .client import LLMError
from .tool_runner import run_with_tools


def main() -> None:
    parser = argparse.ArgumentParser(description="运行 CityEye Tool Calling 演示")
    parser.add_argument("question", help="需要模型查询演示数据的问题")
    args = parser.parse_args()
    try:
        result = run_with_tools(args.question)
    except LLMError as exc:
        raise SystemExit(f"运行失败：{exc}") from exc
    print(result.answer)
    print("\n工具调用记录：")
    print(json.dumps([call.model_dump() for call in result.tool_calls], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
