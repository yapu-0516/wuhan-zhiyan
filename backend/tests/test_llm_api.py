from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.routers import llm as llm_api
from llm_module.client import LLMError
from llm_module.report_generator import CityEventReport
from llm_module.task_parser import ParsedTask, TaskParseError


def parsed_task() -> ParsedTask:
    return ParsedTask(
        event_type="fire",
        analysis_targets=["impact_assessment"],
        location=None,
        event_time=None,
        extracted_facts={},
        missing_information=["事件地点"],
        needs_clarification=True,
    )


def report(data_type: str) -> CityEventReport:
    return CityEventReport.model_validate(
        {
            "report_title": "事件初步研判",
            "data_classification": data_type,
            "event_overview": {
                "event_id": "E0001",
                "event_type": "fire",
                "location": None,
                "event_time": None,
                "description": "输入中提供的事件描述",
                "data_type": data_type,
            },
            "analysis_targets": ["影响评估"],
            "known_information": ["事件位于示范区"],
            "analysis_results": [
                {"kind": "unknown", "statement": "现场情况未知", "basis": None},
            ],
            "risk_assessment": {
                "level": "unknown",
                "statement": "核心信息不足，无法定量判断风险",
                "basis": ["缺少现场核验信息"],
            },
            "recommendations": ["补充现场核验后再研判"],
            "data_gaps_and_uncertainty": ["缺少现场核验信息"],
        }
    )


def test_llm_status_availability_is_environment_independent(client, monkeypatch) -> None:
    monkeypatch.setattr(llm_api.Settings, "from_env", classmethod(lambda cls: SimpleNamespace(api_key="test")))
    assert client.get("/api/llm/status").json() == {"available": True}

    monkeypatch.setattr(
        llm_api.Settings,
        "from_env",
        classmethod(lambda cls: (_ for _ in ()).throw(LLMError("未配置 DEEPSEEK_API_KEY"))),
    )
    result = client.get("/api/llm/status").json()
    assert result["available"] is False
    assert "DEEPSEEK_API_KEY" in result["reason"]


def test_parse_task_route_and_provider_error(client, monkeypatch) -> None:
    received: list[str] = []

    def fake_parse(text: str) -> ParsedTask:
        received.append(text)
        return parsed_task()

    monkeypatch.setattr(llm_api, "parse_task", fake_parse)
    result = client.post("/api/llm/parse-task", json={"text": "  帮我分析一起火灾  "})
    assert result.status_code == 200
    assert result.json()["event_type"] == "fire"
    assert received == ["帮我分析一起火灾"]

    monkeypatch.setattr(
        llm_api,
        "parse_task",
        lambda text: (_ for _ in ()).throw(LLMError("大模型服务不可用")),
    )
    result = client.post("/api/llm/parse-task", json={"text": "分析火灾"})
    assert result.status_code == 503
    assert result.json()["detail"] == "大模型服务不可用"


def test_parse_task_retries_one_malformed_model_output(client, monkeypatch) -> None:
    calls = 0

    def flaky_parse(text: str) -> ParsedTask:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise TaskParseError("模型没有返回有效 JSON")
        return parsed_task()

    monkeypatch.setattr(llm_api, "parse_task", flaky_parse)
    result = client.post("/api/llm/parse-task", json={"text": "分析火灾"})
    assert result.status_code == 200
    assert calls == 2


def test_report_uses_seeded_example_classification(client, monkeypatch) -> None:
    events = client.get("/api/events").json()
    seeded = next(e for e in events if e["task_id"])
    captured: list[dict] = []

    def fake_report(report_input: dict) -> CityEventReport:
        captured.append(report_input)
        return report("模型误写的真实监测事件")

    monkeypatch.setattr(llm_api, "generate_report", fake_report)
    result = client.post("/api/llm/report", json={"event_id": seeded["id"]})
    assert result.status_code == 200
    assert captured[0]["data_type"] == "示例数据，不代表真实事件"
    assert captured[0]["known_gaps"]
    assert result.json()["data_classification"] == "示例数据，不代表真实事件"
    assert result.json()["event_overview"]["data_type"] == "示例数据，不代表真实事件"


def test_report_marks_citizen_input_unverified(client, ctx, monkeypatch) -> None:
    lon, lat = ctx.geo.region["center"]
    created = client.post(
        "/api/events",
        json={
            "event_type": "flood",
            "name": "大模型测试上报",
            "longitude": lon,
            "latitude": lat,
            "source": "citizen",
            "description": "市民反映路面积水",
        },
    ).json()
    captured: list[dict] = []

    def fake_report(report_input: dict) -> CityEventReport:
        captured.append(report_input)
        return report("真实监测事件")

    monkeypatch.setattr(llm_api, "generate_report", fake_report)
    result = client.post("/api/llm/report", json={"event_id": created["id"]})
    assert result.status_code == 200
    assert captured[0]["data_type"] == "市民上报事件，尚未经现场核验"
    assert result.json()["data_classification"] == "市民上报事件，尚未经现场核验"


def test_report_missing_event_and_provider_failure(client, monkeypatch) -> None:
    assert client.post("/api/llm/report", json={"event_id": "E9999"}).status_code == 404

    event_id = client.get("/api/events").json()[0]["id"]
    monkeypatch.setattr(
        llm_api,
        "generate_report",
        lambda report_input: (_ for _ in ()).throw(LLMError("请求过于频繁或额度不足")),
    )
    result = client.post("/api/llm/report", json={"event_id": event_id})
    assert result.status_code == 503
    assert result.json()["detail"] == "请求过于频繁或额度不足"


def test_chat_without_event_context(client, monkeypatch) -> None:
    captured: list[tuple[list, dict | None]] = []

    def fake_chat(messages, *, context=None):
        captured.append((messages, context))
        return "一般性建议：先明确事件类型和现场信息。"

    monkeypatch.setattr(llm_api, "answer_chat", fake_chat)
    result = client.post(
        "/api/llm/chat",
        json={
            "messages": [
                {"role": "user", "content": "城市内涝应优先确认哪些信息？"},
            ]
        },
    )
    assert result.status_code == 200
    assert result.json() == {
        "answer": "一般性建议：先明确事件类型和现场信息。",
        "event_id": None,
        "data_type": None,
    }
    assert captured[0][0][0].role == "user"
    assert captured[0][1] is None


def test_chat_attaches_seeded_event_context(client, monkeypatch) -> None:
    seeded = next(e for e in client.get("/api/events").json() if e["task_id"])
    captured: list[dict] = []

    def fake_chat(messages, *, context=None):
        captured.append(context)
        return "先核对现场，再决定处置。"

    monkeypatch.setattr(llm_api, "answer_chat", fake_chat)
    result = client.post(
        "/api/llm/chat",
        json={
            "event_id": seeded["id"],
            "messages": [
                {"role": "user", "content": "这件事件的数据能直接用于真实处置吗？"},
                {"role": "assistant", "content": "需要先确认数据性质。"},
                {"role": "user", "content": "那下一步做什么？"},
            ],
        },
    )
    assert result.status_code == 200
    assert captured[0]["data_type"] == "示例数据，不代表真实事件"
    assert captured[0]["event"]["event_id"] == seeded["id"]
    assert captured[0]["known_gaps"]
    assert result.json()["event_id"] == seeded["id"]
    assert result.json()["data_type"] == "示例数据，不代表真实事件"


@pytest.mark.parametrize(
    ("payload", "detail"),
    [
        (
            {"messages": [{"role": "assistant", "content": "请补充地点。"}]},
            "最后一条消息必须来自用户",
        ),
        (
            {"messages": [{"role": "user", "content": "   "}]},
            "对话内容不能为空",
        ),
        (
            {"messages": [{"role": "user", "content": "问"}] * 9},
            "请求参数校验失败",
        ),
    ],
)
def test_chat_rejects_invalid_history(client, payload: dict, detail: str) -> None:
    result = client.post("/api/llm/chat", json=payload)
    assert result.status_code == 422
    assert detail in result.json()["detail"]


@pytest.mark.parametrize("text", ["", "x"])
def test_parse_task_rejects_invalid_length(client, text: str) -> None:
    result = client.post("/api/llm/parse-task", json={"text": text})
    assert result.status_code == 422
