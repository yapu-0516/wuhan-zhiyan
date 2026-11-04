"""运行 CityEye 系统提示词测试案例。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .client import LLMError, ask
from .prompt import load_system_prompt

CASES_FILE = Path(__file__).with_name("prompt_cases.json")


def main() -> None:
    parser = argparse.ArgumentParser(description="运行系统提示词测试案例")
    parser.add_argument("--case", help="只运行指定案例 ID")
    args = parser.parse_args()

    cases = json.loads(CASES_FILE.read_text(encoding="utf-8"))
    if args.case:
        cases = [case for case in cases if case["id"] == args.case]
        if not cases:
            raise SystemExit(f"未找到案例：{args.case}")

    prompt = load_system_prompt()
    try:
        for case in cases:
            print(f"\n{'=' * 20} {case['id']} {'=' * 20}")
            print(f"用户：{case['user']}")
            print(f"预期：{case['expected']}\n")
            print(ask(case["user"], system_prompt=prompt, temperature=0.1, max_tokens=1200))
    except LLMError as exc:
        raise SystemExit(f"运行失败：{exc}") from exc


if __name__ == "__main__":
    main()
