from types import SimpleNamespace

import pytest

from llm_module.client import LLMError, Settings, ask


class FakeCompletions:
    def __init__(self, content: str | None = "模拟回答") -> None:
        self.content = content
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=self.content))])


class FakeClient:
    def __init__(self, content: str | None = "模拟回答") -> None:
        self.completions = FakeCompletions(content)
        self.chat = SimpleNamespace(completions=self.completions)


def settings() -> Settings:
    return Settings(api_key="test-key", model="deepseek-chat")


def test_ask_returns_model_content() -> None:
    client = FakeClient()
    answer = ask("测试问题", settings=settings(), client=client)
    assert answer == "模拟回答"
    assert client.completions.kwargs["messages"][-1] == {"role": "user", "content": "测试问题"}


def test_ask_includes_system_prompt() -> None:
    client = FakeClient()
    ask("测试问题", system_prompt="系统规则", settings=settings(), client=client)
    assert client.completions.kwargs["messages"] == [
        {"role": "system", "content": "系统规则"},
        {"role": "user", "content": "测试问题"},
    ]


def test_empty_prompt_is_rejected() -> None:
    with pytest.raises(LLMError, match="问题不能为空"):
        ask("   ", settings=settings(), client=FakeClient())


def test_empty_model_content_is_rejected() -> None:
    with pytest.raises(LLMError, match="空内容"):
        ask("测试问题", settings=settings(), client=FakeClient(None))
