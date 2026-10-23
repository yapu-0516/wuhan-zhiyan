import re

from conftest import wait_task

TS = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")
EVENT_KEYS = {
    "id", "event_type", "name", "longitude", "latitude", "confidence", "status", "timestamp", "severity", "source", "district",
    "address", "grid", "description", "building_id", "road_id", "task_id", "evidence_url", "metrics", "assignee", "updated_at",
}
LOG_KEYS = {"id", "event_id", "action", "from_status", "to_status", "operator", "note", "timestamp"}
TASK_KEYS = {"id", "type", "status", "createdAt", "finished_at", "progress", "file_count", "inputs", "algorithm", "location", "result", "error"}


# ------------------------------------------------------------------ 系统
def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["status"] == "ok" and TS.match(r.json()["time"])


def test_system_info(client):
    d = client.get("/api/system/info").json()
    assert d["name"] == "城市之眼 CityEye" and d["database"] == "sqlite"
    assert d["simulator"]["enabled"] is False
    assert len(d["region"]["center"]) == 2 and len(d["region"]["bbox"]) == 4
    assert {a["type"] for a in d["algorithms"]} == {"fire", "traffic", "building", "flood"}
    assert "OpenStreetMap" in d["data_attribution"]


def test_sources(client):
    rows = client.get("/api/sources").json()
    assert len(rows) >= 6
    assert {r["status"] for r in rows} <= {"在线", "采集中", "离线", "待接入"}
    assert all(TS.match(r["last_active"]) for r in rows)


# ------------------------------------------------------------------ 事件
def test_events_list_shape_and_order(client):
    ev = client.get("/api/events").json()
    assert isinstance(ev, list) and len(ev) >= 30
    assert set(ev[0]) == EVENT_KEYS
    assert [e["timestamp"] for e in ev] == sorted((e["timestamp"] for e in ev), reverse=True)
    assert {e["event_type"] for e in ev} == {"fire", "traffic", "building", "flood"}
    assert all(TS.match(e["timestamp"]) and TS.match(e["updated_at"]) for e in ev)
    assert all(re.match(r"^[A-Z]{2}-\d{2}-\d{2}$", e["grid"]) for e in ev)
    ai = [e for e in ev if e["source"] in ("drone", "video", "satellite", "ai_task") and e["evidence_url"]]
    assert ai, "AI 类事件应带算法证据图"


def test_events_filters(client):
    fire = client.get("/api/events", params={"type": "fire"}).json()
    assert fire and all(e["event_type"] == "fire" for e in fire)
    resolved = client.get("/api/events", params={"status": "resolved", "limit": 3}).json()
    assert len(resolved) == 3 and all(e["status"] == "resolved" for e in resolved)
    some = client.get("/api/events").json()[0]
    hit = client.get("/api/events", params={"q": some["id"]}).json()
    assert [e["id"] for e in hit] == [some["id"]]
    bad = client.get("/api/events", params={"type": "earthquake"})
    assert bad.status_code == 422 and "校验失败" in bad.json()["detail"]


def test_event_get_logs_and_404(client):
    e = client.get("/api/events", params={"status": "resolved"}).json()[0]
    assert client.get(f"/api/events/{e['id']}").json()["id"] == e["id"]
    logs = client.get(f"/api/events/{e['id']}/logs").json()
    assert set(logs[0]) == LOG_KEYS and logs[0]["action"] == "created"
    assert [x["timestamp"] for x in logs] == sorted(x["timestamp"] for x in logs)
    assert logs[-1]["to_status"] == "resolved" or any(x["to_status"] == "resolved" for x in logs)
    r = client.get("/api/events/E9999")
    assert r.status_code == 404 and "不存在" in r.json()["detail"]


def test_create_and_patch_event_state_machine(client, ctx):
    lon, lat = ctx.geo.region["center"]
    r = client.post("/api/events", json={"event_type": "flood", "name": "路面积水", "longitude": lon, "latitude": lat,
                                         "severity": "medium", "description": "测试上报", "source": "citizen", "confidence": 1.0})
    assert r.status_code == 201
    e = r.json()
    assert e["status"] == "pending" and e["district"] and e["address"] and e["grid"]
    eid = e["id"]
    # pending → processing（含指派）
    r = client.patch(f"/api/events/{eid}", json={"status": "processing", "assignee": "武汉市水务局排水中心", "operator": "值班员 张敏", "note": "已派单"})
    assert r.status_code == 200 and r.json()["status"] == "processing" and r.json()["assignee"] == "武汉市水务局排水中心"
    # 非法：processing → monitoring
    r = client.patch(f"/api/events/{eid}", json={"status": "monitoring"})
    assert r.status_code == 409 and "非法状态流转" in r.json()["detail"]
    # 同状态 + 备注 → comment
    assert client.patch(f"/api/events/{eid}", json={"status": "processing", "note": "现场排水中"}).status_code == 200
    # processing → resolved → processing（重新打开）
    assert client.patch(f"/api/events/{eid}", json={"status": "resolved"}).json()["status"] == "resolved"
    assert client.patch(f"/api/events/{eid}", json={"status": "processing", "note": "积水复现"}).json()["status"] == "processing"
    actions = [x["action"] for x in client.get(f"/api/events/{eid}/logs").json()]
    assert actions[0] == "created" and actions.count("status_changed") == 3
    assert "assigned" in actions and "comment" in actions


def test_create_event_validation(client):
    r = client.post("/api/events", json={"event_type": "flood", "name": "x", "longitude": 120.0, "latitude": 30.0})
    assert r.status_code == 400 and "示范区" in r.json()["detail"]
    r = client.post("/api/events", json={"event_type": "quake", "name": "x", "longitude": 114.29, "latitude": 30.59})
    assert r.status_code == 422 and isinstance(r.json()["detail"], str)
    assert client.patch("/api/events/E9999", json={"status": "resolved"}).status_code == 404


# ------------------------------------------------------------------ 城市对象
def test_buildings_and_detail(client, ctx):
    fc = client.get("/api/buildings").json()
    assert fc["type"] == "FeatureCollection" and len(fc["features"]) == len(ctx.geo.buildings)
    f = fc["features"][0]
    assert f["geometry"]["type"] == "Polygon" and f["id"] == f["properties"]["id"]
    assert {"monitored", "risk_level", "height", "category", "district", "grid", "longitude", "latitude"} <= set(f["properties"])
    monitored = [x for x in fc["features"] if x["properties"]["monitored"]]
    assert 30 <= len(monitored) <= 40
    assert {x["properties"]["risk_level"] for x in monitored} >= {"normal", "watch", "warning"}
    bid = monitored[0]["id"]
    d = client.get(f"/api/buildings/{bid}").json()
    assert d["monitoring"]["risk_level"] in ("normal", "watch", "warning") and len(d["monitoring"]["series"]) == 180
    plain = next(x["id"] for x in fc["features"] if not x["properties"]["monitored"])
    assert client.get(f"/api/buildings/{plain}").json()["monitoring"] is None
    assert client.get("/api/buildings/B99999").status_code == 404


def test_roads_and_pois(client):
    fc = client.get("/api/roads").json()
    assert fc["features"]
    p = fc["features"][0]["properties"]
    assert {"id", "name", "highway", "length_m", "speed_limit", "speed", "tpi", "level"} <= set(p)
    assert p["level"] in ("smooth", "basic", "light", "moderate", "heavy") and 0 <= p["tpi"] <= 10
    pois = client.get("/api/pois").json()
    assert pois and {"id", "name", "kind", "longitude", "latitude"} == set(pois[0])


# ------------------------------------------------------------------ 统计
def test_stats_overview(client):
    d = client.get("/api/stats/overview").json()
    total = len(client.get("/api/events", params={"limit": 2000}).json())
    assert d["total"] == total and d["active"] == total - d["by_status"]["resolved"]
    assert set(d["by_type"]) == {"fire", "traffic", "building", "flood"}
    assert set(d["by_severity"]) == {"low", "medium", "high", "critical"}
    assert len(d["trend"]) == 24 and re.match(r"^\d{2}:00$", d["trend"][0]["time"])
    ci = d["city_index"]
    assert 0 <= ci["safety_score"] <= 100 and ci["sensors_online"] <= ci["sensors_total"]
    assert d["avg_response_min"] > 0 and 0 <= d["resolve_rate"] <= 1


# ------------------------------------------------------------------ 数据资产
def test_data_list_stats_upload(client):
    items = client.get("/api/data").json()
    assert len(items) >= 10 and re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$", items[0]["time"])
    assert any("OpenStreetMap" in i["source"] for i in items)
    st = client.get("/api/data/stats").json()
    assert st["total"] == len(items) and st["total_size"].endswith("B")
    r = client.post("/api/data/upload", files=[("files", ("level.csv", b"time,water_level_cm\n12:00,3\n", "text/csv"))])
    assert r.status_code == 200 and r.json()[0]["type"] == "传感器数据"
    assert client.get(r.json()[0]["url"]).status_code == 200
    r = client.post("/api/data/upload", files=[("files", ("a.xyz", b"1", "application/octet-stream"))])
    assert r.status_code == 400 and "type" in r.json()["detail"]
    r = client.post("/api/data/upload", data={"type": "卫星"}, files=[("files", ("a.csv", b"1", "text/csv"))])
    assert r.status_code == 400 and "不支持的数据类型" in r.json()["detail"]


# ------------------------------------------------------------------ AI 任务
def test_samples(client):
    s = client.get("/api/samples").json()
    assert len(s) >= 12 and {"id", "type", "name", "description", "kind", "thumbnail_url", "files", "longitude", "latitude"} == set(s[0])
    fire = client.get("/api/samples", params={"type": "fire"}).json()
    assert fire and all(x["type"] == "fire" for x in fire)
    assert client.get(fire[0]["thumbnail_url"]).status_code == 200


def test_task_with_positive_sample_creates_event(client):
    r = client.post("/api/tasks", json={"type": "fire", "fileCount": 0, "sample_id": "fire-01", "create_event": True})
    assert r.status_code == 200
    t = r.json()
    assert set(t) == TASK_KEYS and t["status"] in ("pending", "running", "done")
    t = wait_task(client, t["id"])
    assert t["status"] == "done" and t["progress"] == 100 and t["algorithm"]["name"] == "FlameNet-Lite"
    res = t["result"]
    assert res["detected"] and res["detections"] and len(res["event_ids"]) == 1
    assert client.get(res["artifacts"][0]["url"]).status_code == 200
    ev = client.get(f"/api/events/{res['event_ids'][0]}").json()
    assert ev["task_id"] == t["id"] and ev["source"] == "ai_task" and ev["status"] == "pending"
    assert client.get(ev["evidence_url"]).headers["content-type"].startswith("image/")
    assert client.get("/api/tasks").json()[0]["id"] == t["id"]


def test_task_with_negative_sample_no_event(client):
    t = wait_task(client, client.post("/api/tasks", json={"type": "fire", "fileCount": 0, "sample_id": "fire-05"}).json()["id"])
    assert t["status"] == "done" and t["result"]["detected"] is False and t["result"]["event_ids"] == []


def test_task_series_result(client):
    t = wait_task(client, client.post("/api/tasks", json={"type": "flood", "fileCount": 0, "sample_id": "flood-01", "create_event": False}).json()["id"])
    assert t["result"]["detected"] and t["result"]["series"] and t["result"]["event_ids"] == []
    assert t["result"]["artifacts"][0]["kind"] == "chart"


def test_task_errors(client):
    r = client.post("/api/tasks", json={"type": "fire", "fileCount": 0})
    assert r.status_code == 400 and "sample_id" in r.json()["detail"]
    assert client.post("/api/tasks", json={"type": "fire", "fileCount": 0, "sample_id": "nope"}).status_code == 404
    assert client.post("/api/tasks", json={"type": "flood", "fileCount": 0, "sample_id": "fire-01"}).status_code == 400
    assert client.post("/api/tasks", json={"type": "smoke", "fileCount": 0, "sample_id": "fire-01"}).status_code == 400
    assert client.get("/api/tasks/T9999").status_code == 404


def test_task_upload(client, ctx):
    csv = (ctx.settings.samples_dir / "traffic" / "yanjiang_ave_incident.csv").read_bytes()
    r = client.post("/api/tasks/upload", data={"type": "traffic", "longitude": "114.29", "latitude": "30.585", "create_event": "false"},
                    files=[("files", ("speed.csv", csv, "text/csv"))])
    assert r.status_code == 200
    t = wait_task(client, r.json()["id"])
    assert t["status"] == "done" and t["algorithm"]["name"] == "TrafficPulse" and t["result"]["event_ids"] == []
    assert t["inputs"][0]["name"] == "speed.csv" and t["location"] == {"longitude": 114.29, "latitude": 30.585}
    img = (ctx.settings.samples_dir / "fire" / "drone_fire_01.jpg").read_bytes()
    r = client.post("/api/tasks/upload", data={"type": "building"}, files=[("files", ("a.jpg", img, "image/jpeg"))])
    assert r.status_code == 400 and "2 张图片" in r.json()["detail"]
    r = client.post("/api/tasks/upload", data={"type": "flood"}, files=[("files", ("x.csv", b"time,level\n1,2\n", "text/csv"))])
    assert r.status_code == 400 and "water_level_cm" in r.json()["detail"]
    r = client.post("/api/tasks/upload", data={"type": "fire"}, files=[("files", ("a.txt", b"hi", "text/plain"))])
    assert r.status_code == 400 and "不支持的文件格式" in r.json()["detail"]


# ------------------------------------------------------------------ 演示 / 实时 / 静态
def test_demo_scenario(client):
    r = client.post("/api/demo/scenario", json={"scenario": "flood"})
    assert r.status_code == 200
    d = r.json()
    t = client.get(f"/api/tasks/{d['task_id']}").json()
    assert t["status"] == "done" and t["type"] == "flood"
    if t["result"]["detected"]:
        assert d["event_id"] and client.get(f"/api/events/{d['event_id']}").json()["task_id"] == d["task_id"]
    else:
        assert d["event_id"] is None
    assert client.post("/api/demo/scenario", json={"scenario": "volcano"}).status_code == 422


def test_websocket_hello_ping_and_broadcast(client, ctx):
    with client.websocket_connect("/api/ws") as ws:
        hello = ws.receive_json()
        assert hello["type"] == "hello" and hello["data"]["demo_mode"] is True and TS.match(hello["ts"])
        ws.send_text('{"type":"ping"}')
        assert ws.receive_json()["type"] == "pong"
        lon, lat = ctx.geo.region["center"]
        created = client.post("/api/events", json={"event_type": "fire", "name": "WS 测试", "longitude": lon, "latitude": lat}).json()
        msg = ws.receive_json()
        assert msg["type"] == "event.created" and msg["data"]["id"] == created["id"]


def test_static_files_and_spa(client):
    assert client.get("/files/samples/manifest.json").status_code == 200
    assert "CityEye" in client.get("/").text
    assert "CityEye" in client.get("/events/E0001").text  # SPA 回退
    assert client.get("/assets/app.js").text == "console.log('ok')"
    r = client.get("/api/not-exist")
    assert r.status_code == 404 and "接口不存在" in r.json()["detail"]
    assert client.get("/docs").status_code == 200
    for probe in ("/files/../app/main.py", "/files/..%2F..%2Fapp%2Fmain.py", "/..%2Fbackend%2Fapp%2Fmain.py"):
        assert "create_app" not in client.get(probe).text  # 不得越权读取源码
