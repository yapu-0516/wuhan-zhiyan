"""结构化情景推演报告生成。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .client import LLMError, Settings, ask
from .task_parser import TaskParseError, _decode_json

PROMPT_FILE = Path(__file__).with_name("prompts") / "scenario_report.md"


class HybridReportError(LLMError):
    """情景报告生成失败。"""


class ScenarioReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_title: str
    data_classification: str
    event_summary: str
    original_scenario: dict[str, Any]
    extracted_parameters: dict[str, Any]
    data_and_methods: list[str]
    development_process: list[str]
    affected_objects: list[str]
    risk_assessment: str
    comparison_summary: str
    uncertainties: list[str]
    recommendations: list[str]
    visualization_summary: list[str]


def generate_scenario_report(
    payload: dict[str, Any],
    *,
    settings: Settings | None = None,
    client: Any | None = None,
) -> ScenarioReport:
    content = ask(
        json.dumps(payload, ensure_ascii=False),
        system_prompt=PROMPT_FILE.read_text(encoding="utf-8").strip(),
        settings=settings,
        client=client,
        temperature=0,
        max_tokens=4096,
        response_format={"type": "json_object"},
    )
    try:
        data = _decode_json(content)
    except TaskParseError as exc:
        raise HybridReportError(str(exc)) from exc
    try:
        return ScenarioReport.model_validate(data)
    except (ValueError, TypeError) as exc:
        raise HybridReportError(f"情景报告格式错误：{exc}") from exc
