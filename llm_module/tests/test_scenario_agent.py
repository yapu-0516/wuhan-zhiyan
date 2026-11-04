from types import SimpleNamespace

from llm_module.client import Settings
from llm_module.scenario_agent import converse


class FakeClient:
    def __init__(self, content: str) -> None:
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(
                create=lambda **kwargs: SimpleNamespace(
                    choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
                )
            )
        )


def test_scenario_agent_normalizes_chinese_numeric_values() -> None:
    client = FakeClient(
        """
{
  "action": "run",
  "scenario_type": "fire",
  "title": "火灾",
  "parameters": {
    "location_name": "江汉路",
    "start_time": "2026-10-31 18:00",
    "duration_min": "30分钟",
    "fire_severity": "中型",
    "danger_radius_m": "200米",
    "people_count": "200人"
  },
  "reply": "开始推演",
  "missing_information": [],
  "compare_run_ids": []
}
"""
    )
    result = converse("江汉路中型火灾", settings=Settings(api_key="test"), client=client)
    assert result.action == "run"
    assert result.parameters.fire_severity == "medium"
    assert result.parameters.duration_min == 30
    assert result.parameters.people_count == 200
