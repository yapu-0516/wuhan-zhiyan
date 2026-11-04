"""CityEye 城市治理助手的受控多轮问答。"""

from __future__ import annotations

import json
from typing import Any, Literal, Sequence

from pydantic import BaseModel, ConfigDict, Field

from .client import Settings, ask
from .prompt import load_system_prompt


class ChatTurn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


def _build_prompt(messages: Sequence[ChatTurn], context: dict[str, Any] | None) -> str:
    sections: list[str] = []
    if context:
        sections.append(
            "以下是系统从现有事件目录读取的关联上下文。未知字段保持未知，"
            "不得把示例、模拟或未经核验的数据说成真实事件。\n"
            + json.dumps(context, ensure_ascii=False, separators=(",", ":"))
        )
    history = "\n\n".join(
        f"{'用户' if message.role == 'user' else '助手'}：{message.content.strip()}"
        for message in messages
    )
    sections.append("以下是本次对话记录：\n" + history)
    sections.append("请回答最后一条用户消息，只使用用户输入和关联上下文中明确存在的信息。")
    return "\n\n".join(sections)


def answer_chat(
    messages: Sequence[ChatTurn],
    *,
    context: dict[str, Any] | None = None,
    settings: Settings | None = None,
    client: Any | None = None,
) -> str:
    """生成一条治理助手回答；不执行工具，也不修改城市事件。"""
    if not messages:
        raise ValueError("对话记录不能为空")
    if messages[-1].role != "user":
        raise ValueError("最后一条消息必须来自用户")
    return ask(
        _build_prompt(messages, context),
        system_prompt=load_system_prompt(),
        settings=settings,
        client=client,
        temperature=0.1,
        max_tokens=1600,
    )
