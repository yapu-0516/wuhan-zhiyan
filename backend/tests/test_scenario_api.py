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


def test_selected_scenario_can_become_traceable_work_orders(client, ctx, monkeypatch) -> None:
    monkeypatch.setattr(
        scenario_service,
        "converse",
        lambda *args, **kwargs: agent_output(
            "update",
            location_name="江汉路",
            start_time="2026-10-31 14:00",
            duration_min=60,
            rainfall_mm_h=80,
        ),
    )
    session_id = client.post("/api/scenario/sessions").json()["session_id"]
    result = client.post(
        f"/api/scenario/sessions/{session_id}/messages",
        json={"message": "江汉路暴雨推演", "auto_run": True},
    ).json()
    run_id = result["latest_run"]["run_id"]
    lon, lat = ctx.geo.region["center"]
    event = client.post(
        "/api/events",
        json={
            "event_type": "flood",
            "name": "情景方案转工单测试",
            "longitude": lon,
            "latitude": lat,
            "severity": "high",
            "source": "citizen",
        },
    ).json()
    response = client.post(
        f"/api/scenario-runs/{run_id}/dispatch",
        json={"event_id": event["id"]},
    )
    assert response.status_code == 201
    orders = response.json()
    assert len(orders) == 2
    assert all(order["scenario_run_id"] == run_id and order["status"] == "pending" for order in orders)
    assert "常规响应" in orders[0]["description"]
    duplicate = client.post(
        f"/api/scenario-runs/{run_id}/dispatch",
        json={"event_id": event["id"]},
    )
    assert duplicate.status_code == 409


def test_scenario_can_start_from_event_and_export_affected_objects(client, ctx, monkeypatch):
    lon, lat = ctx.geo.region["center"]
    event = client.post(
        "/api/events",
        json={
            "event_type": "flood",
            "name": "事件来源情景测试",
            "longitude": lon,
            "latitude": lat,
            "severity": "high",
            "source": "citizen",
        },
    ).json()
    created = client.post("/api/scenario/sessions", json={"event_id": event["id"]})
    assert created.status_code == 200
    session = created.json()
    assert session["scenario_type"] == "flood"
    assert session["parameters"]["source_event_id"] == event["id"]
    assert session["parameters"]["available_resource_count"] >= 1

    monkeypatch.setattr(
        scenario_service,
        "converse",
        lambda *args, **kwargs: agent_output(
            "update",
            location_name=None,
            start_time="2026-11-11 10:00",
            duration_min=60,
            rainfall_mm_h=60,
        ),
    )
    result = client.post(
        f"/api/scenario/sessions/{session['session_id']}/messages",
        json={"message": "补充降雨假设并运行", "auto_run": True},
    )
    assert result.status_code == 200
    latest = result.json()["latest_run"]
    frame = latest["frames"][0]
    assert isinstance(frame["affected_building_ids"], list)
    assert isinstance(frame["affected_road_ids"], list)
    assert frame["metrics"]["available_resource_count"] >= 0
    exported = client.get(f"/api/scenario/runs/{latest['run_id']}/export")
    assert exported.status_code == 200
    assert latest["run_id"] in exported.headers["content-disposition"]


def test_scenario_template_can_create_and_run_session(client):
    templates = client.get("/api/scenario/templates")
    assert templates.status_code == 200
    assert len(templates.json()) >= 3
    created = client.post(
        "/api/scenario/templates",
        json={
            "name": "测试暴雨模板",
            "description": "固定内涝推演参数",
            "scenario_type": "flood",
            "parameters": {
                "location_name": "江汉区",
                "start_time": "2026-11-11 12:00",
                "duration_min": 60,
                "rainfall_mm_h": 60,
                "people_count": 300,
                "response_delay_min": 3,
                "available_resource_count": 4,
            },
        },
    )
    assert created.status_code == 201
    template = created.json()
    history = client.get(f"/api/scenario/templates/{template['id']}/revisions")
    assert history.status_code == 200
    assert history.json()[0]["version_no"] == 1
    edited = client.patch(
        f"/api/scenario/templates/{template['id']}",
        json={
            "name": "测试暴雨模板（修订）",
            "description": "增加响应延迟",
            "parameters": {
                **template["parameters"],
                "response_delay_min": 6,
            },
            "operator": "测试模板编辑员",
        },
    )
    assert edited.status_code == 200
    assert edited.json()["name"].endswith("（修订）")
    revisions = client.get(f"/api/scenario/templates/{template['id']}/revisions").json()
    assert [item["version_no"] for item in revisions] == [2, 1]
    assert revisions[0]["parameters"]["response_delay_min"] == 6
    session = client.post("/api/scenario/sessions", json={"template_id": template["id"]}).json()
    assert session["scenario_type"] == "flood"
    assert session["current_version_id"]
    result = client.post(f"/api/scenario/sessions/{session['session_id']}/runs/variants")
    assert result.status_code == 200
    assert result.json()["latest_run"]["scenario_type"] == "flood"
    assert client.delete(f"/api/scenario/templates/{template['id']}").status_code == 200


def test_scenario_can_reserve_specific_inventory_resources(client):
    resources = client.get("/api/support/emergency-resources", params={"status": "available"}).json()
    first = next(item for item in resources if item["available"] > 0)
    second = next(
        (item for item in resources if item["available"] > 0 and item["id"] != first["id"]),
        first,
    )
    session = client.post("/api/scenario/sessions").json()
    selected = list(dict.fromkeys([first["id"], second["id"]]))
    updated = client.put(
        f"/api/scenario/sessions/{session['session_id']}/resources",
        json={"resource_ids": selected},
    )
    assert updated.status_code == 200
    assert updated.json()["parameters"]["available_resource_count"] == len(selected)
    assert set(updated.json()["parameters"]["resource_ids"]) == set(selected)
