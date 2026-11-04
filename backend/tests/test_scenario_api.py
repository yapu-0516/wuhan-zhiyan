from app.services import scenario as scenario_service
from llm_module.scenario_agent import ScenarioAgentOutput
from scenario_engine.models import ScenarioParameters


def agent_output(action: str, **params) -> ScenarioAgentOutput:
    return ScenarioAgentOutput(
        action=action,
        scenario_type="flood",
        title="江汉路暴雨情景",
        parameters=ScenarioParameters(**params),
        reply="已处理。",
        missing_information=[],
    )


def test_scenario_session_and_run(client, monkeypatch) -> None:
    monkeypatch.setattr(
        scenario_service,
        "converse",
        lambda *args, **kwargs: agent_output(
            "run",
            location_name="江汉路",
            start_time="2026-10-31 14:00",
            duration_min=60,
            rainfall_mm_h=80,
        ),
    )
    created = client.post("/api/scenario/sessions")
    assert created.status_code == 200
    session_id = created.json()["session_id"]
    result = client.post(
        f"/api/scenario/sessions/{session_id}/messages",
        json={"message": "江汉路降雨80毫米每小时，持续60分钟，开始推演"},
    )
    assert result.status_code == 200
    data = result.json()
    assert data["latest_run"]["data_classification"] == "simulated"
    assert len(data["latest_run"]["frames"]) >= 4
    run_id = data["latest_run"]["run_id"]
    assert client.get(f"/api/scenario/runs/{run_id}").status_code == 200


def test_scenario_missing_parameters_are_reported(client, monkeypatch) -> None:
    monkeypatch.setattr(
        scenario_service,
        "converse",
        lambda *args, **kwargs: agent_output("update", location_name="江汉路"),
    )
    session_id = client.post("/api/scenario/sessions").json()["session_id"]
    result = client.post(
        f"/api/scenario/sessions/{session_id}/messages",
        json={"message": "在江汉路模拟暴雨"},
    ).json()
    assert result["action"] == "clarify"
    assert "降雨强度" in result["assistant_reply"]


def test_demo_auto_run_fills_assumptions_and_builds_three_variants(client, monkeypatch) -> None:
    monkeypatch.setattr(
        scenario_service,
        "converse",
        lambda *args, **kwargs: agent_output("update", location_name="江汉路"),
    )
    session_id = client.post("/api/scenario/sessions").json()["session_id"]
    result = client.post(
        f"/api/scenario/sessions/{session_id}/messages",
        json={"message": "江汉路发生暴雨，推演影响", "auto_run": True},
    ).json()
    labels = [run["variant_label"] for run in result["variant_runs"]]
    assert labels == ["常规响应", "不利响应", "提前干预"]
    assert result["latest_run"]["variant_label"] == "常规响应"
    assert "自动补全" in result["assistant_reply"]
    assert result["latest_run"]["frames"][0]["people"]

    rerun = client.post(f"/api/scenario/sessions/{session_id}/runs/variants")
    assert rerun.status_code == 200
    rerun_data = rerun.json()
    assert [item["variant_label"] for item in rerun_data["variant_runs"]] == [
        "常规响应",
        "不利响应",
        "提前干预",
    ]
    assert rerun_data["latest_run"]["variant_label"] == "常规响应"


def test_compare_does_not_require_current_parameters(client, monkeypatch) -> None:
    session_id = client.post("/api/scenario/sessions").json()["session_id"]
    outputs = iter(
        [
            agent_output(
                "run",
                location_name="江汉路",
                start_time="2026-10-31 14:00",
                duration_min=30,
                rainfall_mm_h=40,
            ),
            agent_output(
                "run",
                location_name="江汉路",
                start_time="2026-10-31 14:00",
                duration_min=60,
                rainfall_mm_h=80,
            ),
        ]
    )
    monkeypatch.setattr(scenario_service, "converse", lambda *args, **kwargs: next(outputs))
    first = client.post(
        f"/api/scenario/sessions/{session_id}/messages",
        json={"message": "第一版推演"},
    ).json()
    second = client.post(
        f"/api/scenario/sessions/{session_id}/messages",
        json={"message": "第二版推演"},
    ).json()
    run_ids = [first["latest_run"]["run_id"], second["latest_run"]["run_id"]]
    compare_reply = ScenarioAgentOutput(
        action="compare",
        scenario_type=None,
        parameters=ScenarioParameters(),
        reply="比较完成",
        compare_run_ids=run_ids,
    )
    monkeypatch.setattr(scenario_service, "converse", lambda *args, **kwargs: compare_reply)
    result = client.post(
        f"/api/scenario/sessions/{session_id}/messages",
        json={"message": "比较最近两次"},
    ).json()
    assert result["action"] == "compare"
    assert result["last_comparison"]["summary"]
