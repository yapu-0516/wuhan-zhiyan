from types import SimpleNamespace

import pytest

from llm_module.chat import ChatTurn, answer_chat
from llm_module.client import Settings


class FakeCompletions:
    def __init__(self, content: str = "建议先补充现场核验信息。") -> None:
        self.content = content
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=self.content))])


class FakeClient:
    def __init__(self) -> None:
        self.completions = FakeCompletions()
        self.chat = SimpleNamespace(completions=self.completions)


def test_chat_includes_history_and_event_context() -> None:
    client = FakeClient()
    answer = answer_chat(
        [
            ChatTurn(role="user", content="这是什么数据？"),
            ChatTurn(role="assistant", content="这是模拟数据。"),
            ChatTurn(role="user", content="下一步应该确认什么？"),
        ],
        context={
            "data_type": "模拟器数据，不代表真实事件",
            "event": {"id": "E0001", "event_type": "fire"},
        },
        settings=Settings(api_key="test"),
        client=client,
    )

    assert answer == "建议先补充现场核验信息。"
    system = client.completions.kwargs["messages"][0]
    prompt = client.completions.kwargs["messages"][1]["content"]
    assert system["role"] == "system"
    assert "城市治理辅助决策助手" in system["content"]
    assert "模拟器数据，不代表真实事件" in prompt
    assert "用户：这是什么数据？" in prompt
    assert "助手：这是模拟数据。" in prompt
    assert "用户：下一步应该确认什么？" in prompt


def test_chat_requires_user_as_last_turn() -> None:
    with pytest.raises(ValueError, match="最后一条消息必须来自用户"):
        answer_chat(
            [ChatTurn(role="assistant", content="请补充事件地点。")],
            settings=Settings(api_key="test"),
            client=FakeClient(),
        )


def test_chat_rejects_empty_history() -> None:
    with pytest.raises(ValueError, match="对话记录不能为空"):
        answer_chat([], settings=Settings(api_key="test"), client=FakeClient())
