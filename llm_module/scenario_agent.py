"""城市情景推演 Agent：自然语言理解与受控动作决策。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from scenario_engine.models import ScenarioParameters, ScenarioType

from .client import LLMError, Settings, ask
from .task_parser import _decode_json

PROMPT_FILE = Path(__file__).with_name("prompts") / "scenario_agent.md"


class ScenarioAgentError(LLMError):
    """模型没有返回合法的情景动作。"""


class ScenarioAgentOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["update", "run", "compare", "clarify"]
    scenario_type: ScenarioType | None = None
    title: str | None = None
    parameters: ScenarioParameters = Field(default_factory=ScenarioParameters)
    reply: str
    missing_information: list[str] = Field(default_factory=list)
    compare_run_ids: list[str] = Field(default_factory=list)


def converse(
    message: str,
    *,
    history: list[dict[str, str]] | None = None,
    current_type: ScenarioType | None = None,
    current_parameters: dict[str, Any] | None = None,
    available_run_ids: list[str] | None = None,
    settings: Settings | None = None,
    client: Any | None = None,
) -> ScenarioAgentOutput:
    message = message.strip()
    if not message:
        raise ScenarioAgentError("情景描述不能为空")
    payload = {
        "user_message": message,
        "conversation": (history or [])[-12:],
        "current_scenario_type": current_type,
        "current_parameters": current_parameters or {},
        "available_run_ids": available_run_ids or [],
    }
    content = ask(
        json.dumps(payload, ensure_ascii=False),
        system_prompt=PROMPT_FILE.read_text(encoding="utf-8").strip(),
        settings=settings,
        client=client,
        temperature=0,
        max_tokens=1200,
        response_format={"type": "json_object"},
    )
    try:
        return ScenarioAgentOutput.model_validate(_decode_json(content))
    except (ValueError, TypeError) as exc:
        raise ScenarioAgentError(f"情景动作格式错误：{exc}") from exc
