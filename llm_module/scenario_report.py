"""结构化情景推演报告生成。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

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

    @field_validator(
        "data_and_methods",
        "development_process",
        "affected_objects",
        "uncertainties",
        "recommendations",
        "visualization_summary",
        mode="before",
    )
    @classmethod
    def normalize_report_items(cls, value: Any) -> Any:
        """兼容模型返回的结构化列表项，统一转换为前端可展示的文本。"""
        if not isinstance(value, list):
            return value
        normalized: list[str] = []
        for item in value:
            if isinstance(item, str):
                normalized.append(item)
                continue
            if isinstance(item, dict):
                prefix = ""
                if item.get("offset_min") is not None:
                    prefix = f"+{item['offset_min']} 分钟："
                description = item.get("description") or item.get("text") or item.get("summary")
                if description:
                    detail = str(description)
                    if item.get("risk_level"):
                        detail += f"（风险：{item['risk_level']}）"
                    normalized.append(prefix + detail)
                    continue
                label = item.get("label") or item.get("name") or item.get("id")
                if label:
                    details = [str(label)]
                    if item.get("type"):
                        details.append(f"类型：{item['type']}")
                    if item.get("data_classification"):
                        details.append(f"数据性质：{item['data_classification']}")
                    normalized.append("；".join(details))
                    continue
                normalized.append(json.dumps(item, ensure_ascii=False, separators=(",", ":")))
                continue
            normalized.append(str(item))
        return normalized


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
