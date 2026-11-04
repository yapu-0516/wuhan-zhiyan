import pytest

from llm_module.client import Settings
from llm_module.task_parser import ParsedTask, TaskParseError, parse_task


class FakeCompletions:
    def __init__(self, content: str) -> None:
        self.content = content
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        from types import SimpleNamespace

        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=self.content))])


class FakeClient:
    def __init__(self, content: str) -> None:
        self.completions = FakeCompletions(content)
        self.chat = type("Chat", (), {"completions": self.completions})()


def test_parse_valid_json() -> None:
    raw = """{"event_type":"fire","analysis_targets":["impact_assessment","nearby_hospitals"],
    "location":null,"event_time":null,"extracted_facts":{},"missing_information":["事件地点"],
    "needs_clarification":true}"""
    client = FakeClient(raw)
    result = parse_task("分析一起火灾", settings=Settings(api_key="test"), client=client)
    assert isinstance(result, ParsedTask)
    assert result.event_type == "fire"
    assert result.location is None
    assert client.completions.kwargs["response_format"] == {"type": "json_object"}


def test_parse_markdown_wrapped_json() -> None:
    raw = '```json\n{"event_type":"unknown","analysis_targets":[],"location":null,"event_time":null,"extracted_facts":{},"missing_information":["事件类型"],"needs_clarification":true}\n```'
    result = parse_task("帮我看看", settings=Settings(api_key="test"), client=FakeClient(raw))
    assert result.event_type == "unknown"


def test_reject_invalid_json() -> None:
    with pytest.raises(TaskParseError, match="有效 JSON"):
        parse_task("测试", settings=Settings(api_key="test"), client=FakeClient("不是 JSON"))


def test_reject_unknown_event_type() -> None:
    raw = '{"event_type":"earthquake","analysis_targets":[],"location":null,"event_time":null,"extracted_facts":{},"missing_information":[],"needs_clarification":false}'
    with pytest.raises(TaskParseError, match="格式错误"):
        parse_task("地震", settings=Settings(api_key="test"), client=FakeClient(raw))
