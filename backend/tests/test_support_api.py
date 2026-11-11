from __future__ import annotations


def test_support_directory_notifications_and_sla(client):
    accounts = client.get("/api/support/accounts")
    assert accounts.status_code == 200
    assert {"duty", "analyst", "dispatcher", "field", "data_admin", "admin"} <= {
        item["role"] for item in accounts.json()
    }

    grids = client.get("/api/support/grids")
    assert grids.status_code == 200
    assert grids.json() and all(item["organization"] and item["risk_types"] for item in grids.json())
    grid = grids.json()[0]
    edited = client.patch(
        f"/api/support/grids/{grid['id']}",
        json={"owner": "测试网格员", "contact": "027-12345678"},
    )
    assert edited.status_code == 200
    assert edited.json()["owner"] == "测试网格员"

    resources = client.get("/api/support/emergency-resources")
    assert resources.status_code == 200
    assert resources.json()
    resource = resources.json()[0]
    updated = client.patch(
        f"/api/support/emergency-resources/{resource['id']}",
        json={"status": "limited", "available": max(0, resource["capacity"] - 1), "contact": "值班调度席"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "limited"
    assert updated.json()["available"] <= updated.json()["capacity"]

    notifications = client.get("/api/support/notifications")
    assert notifications.status_code == 200
    if notifications.json():
        first = notifications.json()[0]
        marked = client.patch(f"/api/support/notifications/{first['id']}/read")
        assert marked.status_code == 200 and marked.json()["is_read"] is True

    summary = client.get("/api/support/sla-summary")
    assert summary.status_code == 200
    payload = summary.json()
    assert payload["total_orders"] >= 3
    assert payload["orders"] and "sla" in payload["orders"][0]
    assert payload["trend"] and payload["trend"][0]["total"] >= 1
    assert payload["avg_response_min"] is not None
    assert payload["avg_execution_min"] is not None
    sla_csv = client.get("/api/support/sla-summary/export")
    assert sla_csv.status_code == 200
    assert "cityeye-sla-summary.csv" in sla_csv.headers["content-disposition"]
    assert "工单编号" in sla_csv.content.decode("utf-8-sig")


def test_write_requests_are_audited_with_current_demo_operator(client, ctx):
    lon, lat = ctx.geo.region["center"]
    response = client.post(
        "/api/events",
        headers={"X-Operator-Id": "A0003"},
        json={
            "event_type": "traffic",
            "name": "审计身份测试事件",
            "longitude": lon,
            "latitude": lat,
            "severity": "medium",
            "source": "citizen",
        },
    )
    assert response.status_code == 201
    assert response.json()["id"].startswith("E")
    rows = client.get("/api/support/audit").json()
    row = next(
        item for item in rows
        if item["path"] == "/api/events" and item["operator_id"] == "A0003"
    )
    assert row["operator_name"] == "李娜"
    assert row["role"] == "dispatcher"
    assert row["status_code"] == 201
    assert row["after_data"]["name"] == "审计身份测试事件"
    audit_csv = client.get("/api/support/audit/export")
    assert audit_csv.status_code == 200
    assert "操作人" in audit_csv.content.decode("utf-8-sig")
    status = client.get("/api/support/service-status")
    assert status.status_code == 200
    assert status.json()["algorithms"]
    assert "task_counts" in status.json()
    review_stats = client.get("/api/support/review-stats")
    assert review_stats.status_code == 200
    assert "by_entity_type" in review_stats.json()
    updated = client.patch(
        "/api/support/config",
        json={"task_pacing_sec": 0, "workflow_interval_sec": 30, "max_upload_mb": 25},
    )
    assert updated.status_code == 200
    assert updated.json()["workflow_interval_sec"] == 30
    assert updated.json()["max_upload_mb"] == 25


def test_audit_records_before_and_after_values_for_updates(client):
    grid = client.get("/api/support/grids").json()[0]
    old_owner = grid["owner"]
    response = client.patch(
        f"/api/support/grids/{grid['id']}",
        headers={"X-Operator-Id": "A0006"},
        json={"owner": "审计更新后的责任人", "contact": "027-99999999"},
    )
    assert response.status_code == 200
    rows = client.get("/api/support/audit").json()
    row = next(item for item in rows if item["path"] == f"/api/support/grids/{grid['id']}")
    assert row["before_data"]["owner"] == old_owner
    assert row["after_data"]["owner"] == "审计更新后的责任人"
    assert row["operator_id"] == "A0006"
    exported = client.get("/api/support/audit/export")
    assert exported.status_code == 200
    assert "修改前" in exported.content.decode("utf-8-sig")


def test_traceability_graph_can_filter_and_export(client):
    graph = client.get("/api/traceability/graph")
    assert graph.status_code == 200
    payload = graph.json()
    assert payload["stats"]["nodes"] >= 5
    assert payload["edges"]
    event = next(item for item in payload["nodes"] if item["entity_type"] == "event")
    focused = client.get(
        "/api/traceability/graph",
        params={"entity_type": "event", "entity_id": event["entity_id"], "limit": 60},
    )
    assert focused.status_code == 200
    assert any(item["id"] == event["id"] for item in focused.json()["nodes"])
    exported = client.get("/api/traceability/export")
    assert exported.status_code == 200
    assert "cityeye-traceability.json" in exported.headers["content-disposition"]
    assert '"nodes"' in exported.text
