"""放在最后运行：重置会清空并重建数据。"""


def test_demo_reset_restores_seed(client):
    lon, lat = 114.2905, 30.5895
    client.post("/api/events", json={"event_type": "fire", "name": "重置前事件", "longitude": lon, "latitude": lat})
    assert client.post("/api/demo/reset").json() == {"ok": True}
    names = [e["name"] for e in client.get("/api/events", params={"limit": 2000}).json()]
    assert "重置前事件" not in names and len(names) >= 30
    assert len(client.get("/api/tasks").json()) >= 5
