import json
from pathlib import Path

from llm_module.prompt import load_system_prompt

CASES_FILE = Path(__file__).parents[1] / "prompt_cases.json"


def test_prompt_contains_required_guardrails() -> None:
    prompt = load_system_prompt()
    for required in ("已知信息", "推断", "信息缺口", "不得补造", "119", "示例"):
        assert required in prompt


def test_cases_cover_all_supported_event_types() -> None:
    cases = json.loads(CASES_FILE.read_text(encoding="utf-8"))
    assert {case["event_type"] for case in cases} == {"fire", "traffic", "building", "flood"}
    assert len({case["id"] for case in cases}) == len(cases)
