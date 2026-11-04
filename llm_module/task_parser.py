"""自然语言任务到结构化 JSON 的解析与校验。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .client import LLMError, Settings, ask

PROMPT_FILE = Path(__file__).with_name("prompts") / "task_parser_system.md"

EventType = Literal["fire", "traffic", "building", "flood", "unknown"]
AnalysisTarget = Literal[
    "impact_assessment",
    "nearby_hospitals",
    "road_impact",
    "casualty_assessment",
    "traffic_impact",
    "building_safety",
    "drainage_assessment",
    "response_advice",
    "other",
]


class TaskParseError(LLMError):
    """模型输出缺失、不是 JSON 或不符合结构。"""


class ParsedTask(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_type: EventType
    analysis_targets: list[AnalysisTarget] = Field(default_factory=list)
    location: str | None = None
    event_time: str | None = None
    extracted_facts: dict[str, str] = Field(default_factory=dict)
    missing_information: list[str] = Field(default_factory=list)
    needs_clarification: bool

    @field_validator("analysis_targets")
    @classmethod
    def unique_targets(cls, value: list[AnalysisTarget]) -> list[AnalysisTarget]:
        return list(dict.fromkeys(value))

    @field_validator("missing_information")
    @classmethod
    def unique_missing(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(item.strip() for item in value if item.strip()))


def load_parser_prompt() -> str:
    return PROMPT_FILE.read_text(encoding="utf-8").strip()


def _decode_json(content: str) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1]).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        raise TaskParseError("模型没有返回有效 JSON") from None
    if not isinstance(data, dict):
        raise TaskParseError("解析结果必须是 JSON 对象")
    return data


def parse_task(
    question: str,
    *,
    settings: Settings | None = None,
    client: Any | None = None,
) -> ParsedTask:
    question = question.strip()
    if not question:
        raise TaskParseError("问题不能为空")
    content = ask(
        question,
        system_prompt=load_parser_prompt(),
        settings=settings,
        client=client,
        temperature=0,
        max_tokens=800,
        response_format={"type": "json_object"},
    )
    try:
        return ParsedTask.model_validate(_decode_json(content))
    except (ValueError, TypeError) as exc:
        raise TaskParseError(f"解析结果格式错误：{exc}") from exc
