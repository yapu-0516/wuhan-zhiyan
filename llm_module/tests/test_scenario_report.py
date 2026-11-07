from types import SimpleNamespace

from llm_module.client import Settings
from llm_module.scenario_report import generate_scenario_report


class FakeClient:
    def __init__(self, content: str) -> None:
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(
                create=lambda **kwargs: SimpleNamespace(
                    choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
                )
            )
        )


def test_scenario_report_normalizes_structured_items() -> None:
    content = """
{
  "report_title": "火灾模拟推演",
  "data_classification": "模拟数据",
  "event_summary": "江汉路发生模拟火灾",
  "original_scenario": {},
  "extracted_parameters": {},
  "data_and_methods": ["模拟情景引擎"],
  "development_process": [
    {"offset_min": 0, "risk_level": "high", "description": "风险区域形成。"}
  ],
  "affected_objects": [
    {"type": "zone", "id": "fire-1", "label": "江汉路风险区", "data_classification": "simulated"}
  ],
  "risk_assessment": "仅依据模拟参数进行判断。",
  "comparison_summary": "未进行方案对比。",
  "uncertainties": ["缺少现场核查信息。"],
  "recommendations": ["开展现场核实。"],
  "visualization_summary": ["展示风险范围。"]
}
"""

    report = generate_scenario_report(
        {"data_classification": "simulated"},
        settings=Settings(api_key="test"),
        client=FakeClient(content),
    )

    assert report.development_process == ["+0 分钟：风险区域形成。（风险：high）"]
    assert report.affected_objects == ["江汉路风险区；类型：zone；数据性质：simulated"]
    assert all(isinstance(item, str) for item in report.visualization_summary)
