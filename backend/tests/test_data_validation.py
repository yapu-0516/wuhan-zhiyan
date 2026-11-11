from __future__ import annotations


def test_data_validation_controls_task_admission(client):
    uploaded = client.post(
        "/api/data/upload",
        data={"type": "传感器数据"},
        files={"files": ("validated_series.csv", b"t,value\n2026-11-11,12\n", "text/csv")},
    )
    assert uploaded.status_code == 200
    asset = uploaded.json()[0]
    assert asset["analysis_status"] == "pending"
    asset_id = asset["id"]

    auto = client.post(f"/api/data/{asset_id}/auto-check")
    assert auto.status_code == 201
    assert auto.json()["operator"] == "系统自动预检"
    assert auto.json()["decision"] == "needs_repair"
    assert auto.json()["checks"]["fields"] is True

    blocked = client.post(
        "/api/monitoring-tasks",
        json={
            "name": "未校验数据任务",
            "event_type": "flood",
            "schedule_type": "instant",
            "data_source_ids": [asset_id],
        },
    )
    assert blocked.status_code == 409

    partial = client.post(
        f"/api/data/{asset_id}/validations",
        json={
            "decision": "pass",
            "coordinate_check": True,
            "time_check": False,
            "fields_check": True,
        },
    )
    assert partial.status_code == 400

    repaired = client.post(
        f"/api/data/{asset_id}/validations",
        json={
            "decision": "needs_repair",
            "coordinate_check": True,
            "time_check": False,
            "fields_check": True,
            "notes": ["时区字段待补全"],
        },
    )
    assert repaired.status_code == 201
    assert repaired.json()["checks"]["time"] is False

    passed = client.post(
        f"/api/data/{asset_id}/validations",
        json={
            "decision": "pass",
            "coordinate_check": True,
            "time_check": True,
            "fields_check": True,
            "operator": "数据管理员 周宁",
        },
    )
    assert passed.status_code == 201
    assert passed.json()["quality_score"] == 100

    task = client.post(
        "/api/monitoring-tasks",
        json={
            "name": "已校验数据任务",
            "event_type": "flood",
            "schedule_type": "instant",
            "data_source_ids": [asset_id],
        },
    )
    assert task.status_code == 201

    rejected = client.post(
        f"/api/data/{asset_id}/validations",
        json={"decision": "reject", "notes": ["源文件损坏"]},
    )
    assert rejected.status_code == 201
    run = client.post(
        f"/api/monitoring-tasks/{task.json()['id']}/execute",
        json={},
    )
    assert run.status_code == 409

    history = client.get(f"/api/data/{asset_id}/validations")
    assert history.status_code == 200
    assert [item["decision"] for item in history.json()] == ["reject", "pass", "needs_repair", "needs_repair"]


def test_data_list_supports_spatial_time_and_readiness_filters(client, ctx):
    lon, lat = ctx.geo.region["center"]
    result = client.get(
        "/api/data",
        params={
            "analysis_status": "ready",
            "longitude": lon,
            "latitude": lat,
            "radius_m": 20000,
            "time_from": "2026-01-01T00:00:00",
        },
    )
    assert result.status_code == 200
    rows = result.json()
    assert rows
    assert all(item["analysis_status"] == "ready" for item in rows)
    assert all(item["spatial_extent"]["bbox"] for item in rows)
