from __future__ import annotations


def test_drill_run_is_traceable_and_reviewable(client):
    created = client.post(
        "/api/drills/runs",
        json={
            "drill_key": "fire-wanda",
            "title": "万达商业广场消防演练",
            "event_type": "fire",
            "source_event_id": "E0049",
            "parameters": {"simulation_speed": 4, "risk_radius_m": 230},
            "metrics": {"affected_people": 42, "peak_waiting": 7},
            "timeline": [{"time": 0, "text": "识别建筑火情"}],
            "status": "running",
            "summary": "演练已启动",
            "operator": "演练组织员",
        },
    )
    assert created.status_code == 201
    run = created.json()
    assert run["id"].startswith("DR")
    assert run["scenario_session_id"].startswith("SC")
    assert run["version_id"].startswith("SV")
    assert run["data_classification"] == "simulated"
    assert run["provider"] == "local-crowd-simulator"

    updated = client.patch(
        f"/api/drills/runs/{run['id']}",
        json={
            "metrics": {
                "affected_people": 42,
                "peak_waiting": 11,
                "elapsed_sec": 48,
            },
            "timeline": [
                {"time": 0, "text": "识别建筑火情"},
                {"time": 8, "text": "启动人员疏散"},
                {"time": 48, "text": "疏散完成"},
            ],
            "frame": {"offset_sec": 48, "risk_radius_m": 230, "safe_people": 42},
            "status": "completed",
            "summary": "42 名模拟人员完成疏散，峰值排队 11 人。",
        },
    )
    assert updated.status_code == 200
    detail = updated.json()
    assert detail["status"] == "completed"
    assert len(detail["frames"]) == 1
    assert len(detail["timeline"]) == 3

    listing = client.get("/api/drills/runs")
    assert listing.status_code == 200
    assert any(item["id"] == run["id"] for item in listing.json())

    draft = client.get(
        "/api/reviews/draft",
        params={"entity_type": "drill", "entity_id": run["id"]},
    )
    assert draft.status_code == 200
    payload = draft.json()
    assert payload["entity_type"] == "drill"
    assert payload["metrics"]["peak_waiting"] == 11
    assert len(payload["timeline"]) == 3
    assert "模拟数据" in " ".join(payload["findings"])

    review = client.post(f"/api/drills/runs/{run['id']}/review")
    assert review.status_code == 200
    assert review.json()["entity_type"] == "drill"
    assert review.json()["entity_id"] == run["id"]
    duplicate = client.post(f"/api/drills/runs/{run['id']}/review")
    assert duplicate.status_code == 200
    assert duplicate.json()["id"] == review.json()["id"]

    missing = client.post("/api/reviews", json={"entity_type": "drill", "entity_id": "DR9999", "summary": "x"})
    assert missing.status_code == 404
