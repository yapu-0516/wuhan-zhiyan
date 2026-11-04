from types import SimpleNamespace

import pytest

from llm_module.client import Settings
from llm_module.demo_tools import get_demo_event
from llm_module.tool_runner import execute_tool, run_with_tools


def tool_call(call_id: str, name: str, arguments: str):
    return SimpleNamespace(
        id=call_id,
        function=SimpleNamespace(name=name, arguments=arguments),
    )


class ScriptedCompletions:
    def __init__(self, messages):
        self.messages = iter(messages)
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        message = next(self.messages)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class ScriptedClient:
    def __init__(self, messages):
        self.completions = ScriptedCompletions(messages)
        self.chat = SimpleNamespace(completions=self.completions)


def test_execute_known_and_unknown_tool() -> None:
    assert execute_tool("get_demo_event", {"event_id": "DEMO-FIRE-001"})["ok"] is True
    assert execute_tool("missing_tool", {})["ok"] is False
    assert get_demo_event("DEMO-FIRE-001")["event_id"] == "DEMO-FIRE-001"


def test_tool_result_is_sent_back_to_model() -> None:
    first = SimpleNamespace(
        content=None,
        tool_calls=[tool_call("call-1", "get_demo_event", '{"event_id":"DEMO-FIRE-001"}')],
    )
    final = SimpleNamespace(content="这是 DEMO-FIRE-001 的示例结果。", tool_calls=[])
    client = ScriptedClient([first, final])
    result = run_with_tools("查询 DEMO-FIRE-001", settings=Settings(api_key="test"), client=client)
    assert result.answer.startswith("这是")
    assert result.tool_calls[0].name == "get_demo_event"
    second_messages = client.completions.requests[1]["messages"]
    assert second_messages[-1]["role"] == "tool"
    assert '"ok": true' in second_messages[-1]["content"]


def test_tool_failure_is_returned_to_model() -> None:
    first = SimpleNamespace(
        content=None,
        tool_calls=[tool_call("call-2", "get_demo_event", '{"event_id":"NOT-FOUND"}')],
    )
    final = SimpleNamespace(content="示例事件不存在。", tool_calls=[])
    client = ScriptedClient([first, final])
    result = run_with_tools("查询不存在的事件", settings=Settings(api_key="test"), client=client)
    assert result.tool_calls[0].result["ok"] is False
    assert "未找到" in result.tool_calls[0].result["error"]


def test_invalid_tool_arguments_are_returned_to_model() -> None:
    first = SimpleNamespace(
        content=None,
        tool_calls=[tool_call("call-3", "get_demo_event", "不是 JSON")],
    )
    final = SimpleNamespace(content="参数无效。", tool_calls=[])
    client = ScriptedClient([first, final])
    result = run_with_tools("错误参数", settings=Settings(api_key="test"), client=client)
    assert result.tool_calls[0].result["ok"] is False
    assert "参数无效" in result.tool_calls[0].result["error"]
