"""最小 DeepSeek Tool Calling 执行循环。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from .client import LLMError, Settings, _client
from .demo_tools import TOOLS, get_demo_event, list_demo_facilities

PROMPT_FILE = Path(__file__).with_name("prompts") / "tool_calling_system.md"
TOOL_FUNCTIONS = {
    "get_demo_event": get_demo_event,
    "list_demo_facilities": list_demo_facilities,
}


class ToolCallRecord(BaseModel):
    name: str
    arguments: dict[str, Any]
    result: dict[str, Any]


class ToolRunResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str
    tool_calls: list[ToolCallRecord]


def execute_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    function = TOOL_FUNCTIONS.get(name)
    if function is None:
        return {"ok": False, "error": f"未知工具：{name}"}
    try:
        result = function(**arguments)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "result": result}


def run_with_tools(
    question: str,
    *,
    settings: Settings | None = None,
    client: Any | None = None,
    max_steps: int = 4,
) -> ToolRunResult:
    question = question.strip()
    if not question:
        raise LLMError("问题不能为空")
    active_settings = settings or Settings.from_env()
    active_client = client or _client(active_settings)
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": PROMPT_FILE.read_text(encoding="utf-8").strip()},
        {"role": "user", "content": question},
    ]
    calls: list[ToolCallRecord] = []

    for _ in range(max_steps):
        response = active_client.chat.completions.create(
            model=active_settings.model,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0,
            max_tokens=1000,
        )
        message = response.choices[0].message
        if not message.tool_calls:
            if not message.content:
                raise LLMError("大模型在工具调用后返回了空内容")
            return ToolRunResult(answer=message.content, tool_calls=calls)

        assistant = {
            "role": "assistant",
            "content": message.content,
            "tool_calls": [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.function.name,
                        "arguments": call.function.arguments,
                    },
                }
                for call in message.tool_calls
            ],
        }
        messages.append(assistant)

        for call in message.tool_calls:
            try:
                arguments = json.loads(call.function.arguments)
                if not isinstance(arguments, dict):
                    raise ValueError("工具参数必须是 JSON 对象")
            except (json.JSONDecodeError, ValueError) as exc:
                result = {"ok": False, "error": f"工具参数无效：{exc}"}
                arguments = {}
            else:
                result = execute_tool(call.function.name, arguments)

            calls.append(
                ToolCallRecord(name=call.function.name, arguments=arguments, result=result)
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )

    raise LLMError(f"工具调用超过最大轮数 {max_steps}")
