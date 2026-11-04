"""基于明确输入生成结构化 CityEye 研判报告。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .client import LLMError, Settings, ask
from .task_parser import TaskParseError, _decode_json

PROMPT_FILE = Path(__file__).with_name("prompts") / "report_system.md"


class ReportError(LLMError):
    """模型报告不是有效 JSON 或不符合报告结构。"""


class EventOverview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str
    event_type: str
    location: str | None = None
    event_time: str | None = None
    description: str
    data_type: str


class AnalysisFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["fact", "inference", "unknown"]
    statement: str
    basis: str | None = None


class RiskAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    level: Literal["unknown", "low", "medium", "high", "critical"]
    statement: str
    basis: list[str] = Field(default_factory=list)


class CityEventReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_title: str
    data_classification: str
    event_overview: EventOverview
    analysis_targets: list[str]
    known_information: list[str]
    analysis_results: list[AnalysisFinding]
    risk_assessment: RiskAssessment
    recommendations: list[str]
    data_gaps_and_uncertainty: list[str]


def load_report_prompt() -> str:
    return PROMPT_FILE.read_text(encoding="utf-8").strip()


def generate_report(
    report_input: dict[str, Any],
    *,
    settings: Settings | None = None,
    client: Any | None = None,
) -> CityEventReport:
    content = ask(
        json.dumps(report_input, ensure_ascii=False),
        system_prompt=load_report_prompt(),
        settings=settings,
        client=client,
        temperature=0,
        # 报告含 7 个段落且输入越丰富输出越长；1600 在真实事件 + 周边设施输入下会截断 JSON
        max_tokens=4096,
        response_format={"type": "json_object"},
    )
    try:
        data = _decode_json(content)
    except TaskParseError as exc:
        raise ReportError(str(exc)) from exc
    try:
        return CityEventReport.model_validate(data)
    except (ValueError, TypeError) as exc:
        raise ReportError(f"报告格式错误：{exc}") from exc
