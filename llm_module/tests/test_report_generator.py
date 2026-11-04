import pytest

from llm_module.client import Settings
from llm_module.report_generator import CityEventReport, ReportError, generate_report


class FakeCompletions:
    def __init__(self, content: str) -> None:
        self.content = content

    def create(self, **kwargs):
        from types import SimpleNamespace

        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=self.content))])


class FakeClient:
    def __init__(self, content: str) -> None:
        self.chat = type("Chat", (), {"completions": FakeCompletions(content)})()


def valid_report() -> str:
    return """
{
  "report_title": "示例火情初步研判",
  "data_classification": "示例数据，不代表真实事件",
  "event_overview": {
    "event_id": "DEMO-FIRE-001",
    "event_type": "fire",
    "location": "武汉市江汉区示例商圈",
    "event_time": "2026-10-29 14:30",
    "description": "代码内固定演示记录",
    "data_type": "示例数据"
  },
  "analysis_targets": ["impact_assessment"],
  "known_information": ["有一家示例医院距离800米"],
  "analysis_results": [
    {"kind": "fact", "statement": "示例设施中包含一家医院", "basis": null},
    {"kind": "unknown", "statement": "无法判断医院接诊能力", "basis": null}
  ],
  "risk_assessment": {
    "level": "unknown",
    "statement": "火势和伤亡未知，无法定量判断风险",
    "basis": ["缺少火势规模和伤亡信息"]
  },
  "recommendations": ["如为真实火情，应立即联系119"],
  "data_gaps_and_uncertainty": ["缺少真实事件核验信息"]
}
"""


def test_generate_valid_report() -> None:
    report = generate_report(
        {"data_type": "示例数据"},
        settings=Settings(api_key="test"),
        client=FakeClient(valid_report()),
    )
    assert isinstance(report, CityEventReport)
    assert report.risk_assessment.level == "unknown"


def test_reject_invalid_report_json() -> None:
    with pytest.raises(ReportError, match="有效 JSON"):
        generate_report({}, settings=Settings(api_key="test"), client=FakeClient("不是 JSON"))


def test_reject_invalid_risk_level() -> None:
    raw = valid_report().replace('"level": "unknown"', '"level": "severe"')
    with pytest.raises(ReportError, match="报告格式错误"):
        generate_report({}, settings=Settings(api_key="test"), client=FakeClient(raw))
