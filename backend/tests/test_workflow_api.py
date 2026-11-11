from __future__ import annotations

import re
from datetime import datetime, timedelta

from conftest import wait_task
from app.services.workflow import run_due_monitoring_tasks

TS = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")


def test_workflow_contracts_are_published(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert {
        "/api/monitoring-tasks",
        "/api/monitoring-runs",
        "/api/assessments",
        "/api/work-orders",
        "/api/reviews",
    } <= set(paths)


def test_seeded_flood_workflow_is_traceable(client):
    tasks = client.get("/api/monitoring-tasks").json()
    assert {"MT0001", "MT0002"} <= {task["id"] for task in tasks}
    assert next(task for task in tasks if task["id"] == "MT0001")["status"] == "completed"
    runs = client.get("/api/monitoring-runs", params={"task_id": "MT0001"}).json()
    assert len(runs) == 1 and runs[0]["event_ids"]
    event_id = runs[0]["event_ids"][0]
    assessments = client.get("/api/assessments", params={"event_id": event_id}).json()
    assert assessments[0]["decision"] == "confirmed"
    orders = client.get("/api/work-orders", params={"event_id": event_id}).json()
    assert len(orders) == 2 and all(order["status"] == "verified" for order in orders)
    reviews = client.get("/api/reviews", params={"entity_type": "event", "entity_id": event_id}).json()
    assert reviews[0]["status"] == "confirmed"
    active = client.get("/api/work-orders").json()
    assert any(order["id"] == "WO0003" and order["status"] == "in_progress" for order in active)


def test_task_templates_spatial_context_and_review_draft(client):
    templates = client.get("/api/task-templates")
    assert templates.status_code == 200
    assert len(templates.json()) >= 4
    created = client.post(
        "/api/task-templates",
        json={
            "name": "测试火灾模板",
            "event_type": "fire",
            "schedule_type": "instant",
            "data_source_ids": ["S-DRONE"],
            "rule_config": {"priority": "high"},
            "owner": "消防值班组",
        },
    )
    assert created.status_code == 201
    assert created.json()["id"].startswith("TP")
    updated = client.patch(
        f"/api/task-templates/{created.json()['id']}",
        json={"owner": "模板测试员", "rule_config": {"priority": "medium", "cooldown_minutes": 10}},
    )
    assert updated.status_code == 200
    assert updated.json()["owner"] == "模板测试员"
    revisions = client.get(f"/api/task-templates/{created.json()['id']}/revisions")
    assert revisions.status_code == 200
    assert revisions.json()[0]["rule_config"]["cooldown_minutes"] == 10
    assert client.delete(f"/api/task-templates/{created.json()['id']}").status_code == 200

    event = next(item for item in client.get("/api/events").json() if item["status"] != "resolved")
    context = client.get("/api/assessments/context", params={"event_id": event["id"], "radius_m": 300})
    assert context.status_code == 200
    payload = context.json()
    assert payload["event_id"] == event["id"]
    assert isinstance(payload["buildings"], list) and isinstance(payload["roads"], list)
    assert isinstance(payload["pois"], list)

    draft = client.get("/api/reviews/draft", params={"entity_type": "event", "entity_id": event["id"]})
    assert draft.status_code == 200
    draft_payload = draft.json()
    assert draft_payload["entity_id"] == event["id"]
    assert draft_payload["summary"] and draft_payload["timeline"]
    assert "work_order_count" in draft_payload["metrics"]


def test_review_case_report_and_template_revision(client):
    event = next(item for item in client.get("/api/events").json() if item["status"] != "resolved")
    review = client.post(
        "/api/reviews",
        json={
            "entity_type": "event",
            "entity_id": event["id"],
            "status": "draft",
            "summary": "案例审核测试",
            "findings": ["现场反馈需要纳入规则"],
            "recommendations": ["增加复核阈值"],
        },
    ).json()
    approved = client.patch(f"/api/reviews/{review['id']}", json={"status": "confirmed"})
    assert approved.status_code == 200
    cases = client.get("/api/reviews/cases", params={"q": event["id"]})
    assert cases.status_code == 200
    assert any(item["id"] == review["id"] for item in cases.json())

    template = client.get("/api/task-templates").json()[0]
    revision = client.post(
        f"/api/reviews/{review['id']}/apply-template",
        json={
            "template_id": template["id"],
            "rule_config": {"review_verified": True, "source_review_id": review["id"]},
            "operator": "审核员",
        },
    )
    assert revision.status_code == 201
    assert revision.json()["source_review_id"] == review["id"]
    exported = client.get(f"/api/reviews/{review['id']}/export")
    assert exported.status_code == 200
    assert "案例审核测试" in exported.content.decode("utf-8")


def test_nearby_events_can_be_hard_merged(client, ctx):
    lon, lat = ctx.geo.region["center"]
    primary = client.post(
        "/api/events",
        json={
            "event_type": "flood",
            "name": "主告警",
            "longitude": lon,
            "latitude": lat,
            "severity": "medium",
            "source": "citizen",
        },
    ).json()
    related = client.post(
        "/api/events",
        json={
            "event_type": "flood",
            "name": "重复告警",
            "longitude": lon + 0.0001,
            "latitude": lat + 0.0001,
            "severity": "medium",
            "source": "citizen",
        },
    ).json()
    merged = client.post(
        "/api/assessments/candidates/merge",
        json={
            "primary_event_id": primary["id"],
            "related_event_id": related["id"],
            "operator": "研判员",
            "note": "同一位置重复告警",
        },
    )
    assert merged.status_code == 200
    assert merged.json()["merged"]["status"] == "resolved"
    assert merged.json()["primary"]["metrics"]["merged_event_ids"] == [related["id"]]
    assert merged.json()["merged"]["metrics"]["merged_into"] == primary["id"]


def test_data_assets_describe_scope_quality_version_and_analysis_readiness(client):
    items = client.get("/api/data").json()
    assert items
    item = next(row for row in items if row["analysis_status"] == "ready")
    assert item["spatial_extent"]["bbox"]
    assert item["crs"] == "EPSG:4326"
    assert item["quality_score"] >= 80
    assert item["quality_notes"] and item["version"]
    stats = client.get("/api/data/stats").json()
    assert stats["analyzable"] >= 1
    assert sum(row["count"] for row in stats["by_analysis_status"]) == stats["total"]


def test_monitoring_task_run_and_flood_closure(client, ctx):
    lon, lat = ctx.geo.region["center"]
    event = client.post(
        "/api/events",
        json={
            "event_type": "flood",
            "name": "积水闭环测试",
            "longitude": lon,
            "latitude": lat,
            "severity": "medium",
            "source": "citizen",
        },
    ).json()

    task = client.post(
        "/api/monitoring-tasks",
        json={
            "name": "道路积水即时核查",
            "event_type": "flood",
            "schedule_type": "instant",
            "data_source_ids": ["S-IOT-WATER"],
            "rule_config": {"water_level_threshold_cm": 15},
            "owner": "防汛值班组",
        },
    )
    assert task.status_code == 201
    task = task.json()
    assert task["id"].startswith("MT") and task["status"] == "draft"
    assert TS.match(task["created_at"])
    assert client.patch(f"/api/monitoring-tasks/{task['id']}", json={"status": "completed"}).status_code == 409
    assert client.patch(f"/api/monitoring-tasks/{task['id']}", json={"status": "running"}).json()["status"] == "running"

    run = client.post(
        "/api/monitoring-runs",
        json={
            "monitoring_task_id": task["id"],
            "event_ids": [event["id"]],
            "status": "completed",
            "coverage": {"roads": 3},
            "quality": {"data_completeness": 0.9},
        },
    )
    assert run.status_code == 201
    run = run.json()
    assert run["event_ids"] == [event["id"]]

    assessment = client.post(
        "/api/assessments",
        json={
            "event_id": event["id"],
            "monitoring_run_id": run["id"],
            "decision": "confirmed",
            "summary": "现场水位与观测一致",
            "impact": {"roads": 3},
        },
    )
    assert assessment.status_code == 201
    assessment = assessment.json()

    order = client.post(
        "/api/work-orders",
        json={
            "event_id": event["id"],
            "assessment_id": assessment["id"],
            "title": "积水抽排",
            "unit": "水务排水中心",
            "priority": "high",
        },
    )
    assert order.status_code == 201
    order = order.json()
    assert order["status"] == "pending"
    assert client.patch(f"/api/work-orders/{order['id']}", json={"status": "verified"}).status_code == 409
    for status in ("accepted", "in_progress", "completed", "verified"):
        r = client.patch(
            f"/api/work-orders/{order['id']}",
            json={"status": status, "operator": "测试调度员", "note": f"变更为 {status}"},
        )
        assert r.status_code == 200
    assert r.json()["status"] == "verified" and len(r.json()["feedback"]) >= 4
    assert client.get(f"/api/events/{event['id']}").json()["status"] == "pending"

    review = client.post(
        "/api/reviews",
        json={
            "entity_type": "event",
            "entity_id": event["id"],
            "status": "confirmed",
            "summary": "闭环完成",
            "metrics": {"response_min": 4},
            "findings": ["工单状态与事件状态分离"],
            "recommendations": ["纳入降雨前巡检模板"],
        },
    )
    assert review.status_code == 201 and review.json()["entity_id"] == event["id"]


def test_workflow_reference_validation(client):
    assert client.post(
        "/api/monitoring-runs",
        json={"monitoring_task_id": "MT9999", "status": "pending"},
    ).status_code == 404


def test_task_threshold_is_applied_after_algorithm_detection(client):
    task = client.post(
        "/api/monitoring-tasks",
        json={
            "name": "高阈值积水任务",
            "event_type": "flood",
            "schedule_type": "instant",
            "rule_config": {"water_level_threshold_cm": 999},
        },
    ).json()
    result = client.post(f"/api/monitoring-tasks/{task['id']}/execute", json={"sample_id": "flood-01"})
    assert result.status_code == 200
    analysis_id = result.json()["analysis_task"]["id"]
    done = wait_task(client, analysis_id)
    assert done["status"] == "done"
    assert done["result"]["event_ids"] == []
    assert done["result"]["trigger"]["rule_triggered"] is False
    run = next(
        item for item in client.get("/api/monitoring-runs", params={"task_id": task["id"]}).json()
        if item["analysis_task_id"] == analysis_id
    )
    assert run["quality"]["rule_triggered"] is False


def test_task_composite_condition_can_block_event(client):
    task = client.post(
        "/api/monitoring-tasks",
        json={
            "name": "组合条件测试",
            "event_type": "flood",
            "schedule_type": "instant",
            "rule_config": {
                "water_level_threshold_cm": 0,
                "conditions": [
                    {"metric": "max_level_cm", "operator": ">", "value": 999}
                ],
            },
        },
    ).json()
    result = client.post(f"/api/monitoring-tasks/{task['id']}/execute", json={"sample_id": "flood-01"})
    analysis_id = result.json()["analysis_task"]["id"]
    done = wait_task(client, analysis_id)
    assert done["status"] == "done"
    assert done["result"]["event_ids"] == []
    assert done["result"]["trigger"]["rule_triggered"] is False


def test_task_algorithm_parameters_reach_analyzer(client):
    task = client.post(
        "/api/monitoring-tasks",
        json={
            "name": "算法参数测试",
            "event_type": "flood",
            "schedule_type": "instant",
            "rule_config": {
                "water_level_threshold_cm": 0,
                "algorithm_params": {"forecast_min": 30},
            },
        },
    ).json()
    result = client.post(f"/api/monitoring-tasks/{task['id']}/execute", json={"sample_id": "flood-01"})
    done = wait_task(client, result.json()["analysis_task"]["id"])
    forecast_points = [point for point in done["result"]["series"] if point["kind"] == "forecast"]
    assert 0 < len(forecast_points) <= 6


def test_work_order_can_use_inventory_resource(client):
    resources = client.get("/api/support/emergency-resources", params={"status": "available"}).json()
    resource = next(item for item in resources if item["available"] > 0)
    event = client.get("/api/events").json()[0]
    order = client.post(
        "/api/work-orders",
        json={"event_id": event["id"], "title": "资源协调测试", "unit": "联动处置组"},
    ).json()
    result = client.post(
        f"/api/work-orders/{order['id']}/resources/use",
        json={
            "resource_id": resource["id"],
            "quantity": 1,
            "note": "现场调度",
            "operator": "调度员 李娜",
        },
    )
    assert result.status_code == 200
    usage = result.json()["feedback"][-1]["resource_usage"]
    assert usage["resource_id"] == resource["id"]
    assert usage["quantity"] == 1


def test_monitoring_task_runs_real_analysis_and_updates_run(client):
    task = client.post(
        "/api/monitoring-tasks",
        json={"name": "内涝算法联动", "event_type": "flood", "schedule_type": "instant"},
    ).json()
    result = client.post(
        f"/api/monitoring-tasks/{task['id']}/execute",
        json={"sample_id": "flood-01"},
    )
    assert result.status_code == 200
    payload = result.json()
    assert payload["monitoring_run"]["status"] in ("pending", "running", "completed")
    analysis_id = payload["analysis_task"]["id"]
    done = wait_task(client, analysis_id)
    run = next(
        item for item in client.get("/api/monitoring-runs", params={"task_id": task["id"]}).json()
        if item["analysis_task_id"] == analysis_id
    )
    assert done["status"] == "done"
    assert run["status"] == "completed"
    assert run["event_ids"] == done["result"]["event_ids"]
    assert client.post(
        "/api/assessments",
        json={"event_id": "E9999", "decision": "candidate"},
    ).status_code == 404
    assert client.post(
        "/api/work-orders",
        json={"event_id": "E9999", "title": "无效工单"},
    ).status_code == 404


def test_due_periodic_task_runs_and_is_rescheduled(client, ctx):
    due = (datetime.now() - timedelta(minutes=1)).replace(microsecond=0).isoformat()
    task = client.post(
        "/api/monitoring-tasks",
        json={
            "name": "周期内涝监测测试",
            "event_type": "flood",
            "schedule_type": "periodic",
            "rule_config": {"interval_minutes": 15},
            "next_run_at": due,
        },
    ).json()
    assert task["status"] == "scheduled"
    runs = run_due_monitoring_tasks(ctx, datetime.now())
    assert len(runs) == 1 and runs[0].monitoring_task_id == task["id"]
    done = wait_task(client, runs[0].analysis_task_id)
    assert done["status"] == "done"
    refreshed = client.get(f"/api/monitoring-tasks/{task['id']}").json()
    assert refreshed["status"] == "scheduled"
    assert refreshed["next_run_at"]
    assert datetime.fromisoformat(refreshed["next_run_at"]) > datetime.fromisoformat(due)


def test_work_order_field_feedback_location_photo_and_sla(client, ctx):
    lon, lat = ctx.geo.region["center"]
    event = client.post(
        "/api/events",
        json={
            "event_type": "flood",
            "name": "现场反馈测试",
            "longitude": lon,
            "latitude": lat,
            "severity": "high",
            "source": "citizen",
        },
    ).json()
    due = (datetime.now() - timedelta(minutes=10)).replace(microsecond=0).isoformat()
    order = client.post(
        "/api/work-orders",
        json={
            "event_id": event["id"],
            "title": "现场核查与照片回传",
            "unit": "水务排水中心",
            "priority": "high",
            "due_at": due,
        },
    ).json()
    assert order["sla"]["overdue"] is True

    feedback = client.post(
        f"/api/work-orders/{order['id']}/feedback",
        data={
            "note": "现场积水已降至脚踝以下，雨水口仍有树叶。",
            "longitude": str(lon),
            "latitude": str(lat),
            "operator": "现场处置员",
        },
        files=[("files", ("field.png", b"demo-image-bytes", "image/png"))],
    )
    assert feedback.status_code == 200
    payload = feedback.json()
    entry = payload["feedback"][-1]
    assert entry["action"] == "field_feedback"
    assert entry["location"]["longitude"] == lon
    assert entry["attachments"][0]["url"].startswith("/files/uploads/work-orders/")
    reassessed = client.post(
        f"/api/work-orders/{order['id']}/feedback/{len(payload['feedback']) - 1}/assess",
        json={"operator": "研判员 张敏"},
    )
    assert reassessed.status_code == 201
    assert reassessed.json()["decision"] == "needs_review"
    assert reassessed.json()["impact"]["work_order_id"] == order["id"]

    for status in ("accepted", "in_progress", "completed", "verified"):
        result = client.patch(
            f"/api/work-orders/{order['id']}",
            json={"status": status, "operator": "测试调度员", "note": status},
        )
        assert result.status_code == 200
    sla = result.json()["sla"]
    assert sla["accepted_at"] and sla["started_at"] and sla["completed_at"] and sla["verified_at"]
    assert sla["overdue"] is False
    assert sla["response_min"] is not None
    assert client.post(
        f"/api/work-orders/{order['id']}/feedback",
        data={"note": "复核后再次反馈"},
    ).status_code == 400


def test_work_order_feedback_supports_media_documents_and_size_limits(client):
    order = next(item for item in client.get("/api/work-orders").json() if item["id"] == "WO0003")
    response = client.post(
        f"/api/work-orders/{order['id']}/feedback",
        data={"note": "回传现场视频、语音和核查报告", "operator": "现场处置员"},
        files=[
            ("files", ("scene.mp4", b"demo-video", "video/mp4")),
            ("files", ("voice.mp3", b"demo-audio", "audio/mpeg")),
            ("files", ("check.pdf", b"demo-pdf", "application/pdf")),
        ],
    )
    assert response.status_code == 200
    attachments = response.json()["feedback"][-1]["attachments"]
    assert [item["kind"] for item in attachments] == ["video", "audio", "document"]
    assert [item["mime_type"] for item in attachments] == ["video/mp4", "audio/mpeg", "application/pdf"]
    assert all(item["size_bytes"] > 0 and item["url"].startswith("/files/") for item in attachments)
    for item in attachments:
        served = client.get(item["url"])
        assert served.status_code == 200 and served.content

    unsupported = client.post(
        f"/api/work-orders/{order['id']}/feedback",
        data={"note": "不支持的附件"},
        files=[("files", ("payload.exe", b"not-allowed", "application/octet-stream"))],
    )
    assert unsupported.status_code == 400
    assert "不支持的文件类型" in unsupported.json()["detail"]

    updated = client.patch(
        "/api/support/config",
        json={"work_order_max_attachment_mb": 1},
    )
    assert updated.status_code == 200
    try:
        too_large = client.post(
            f"/api/work-orders/{order['id']}/feedback",
            data={"note": "超大附件"},
            files=[("files", ("large.mp4", b"x" * (1024 * 1024 + 1), "video/mp4"))],
        )
        assert too_large.status_code == 400
        assert "超过大小限制" in too_large.json()["detail"]
    finally:
        client.patch("/api/support/config", json={"work_order_max_attachment_mb": 200})
