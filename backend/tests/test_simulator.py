"""模拟器单步逻辑（不启动后台循环）。"""
from app import timeutil
from app.models import Event
from app.services.simulator import Simulator


def test_patrol_creates_events_only_on_detection(client, ctx):
    sim = Simulator(ctx)
    before = client.get("/api/stats/overview").json()["total"]
    outcomes = [sim.patrol_once(k) for k in ("fire", "flood", "building", "traffic") * 3]
    after = client.get("/api/stats/overview").json()["total"]
    created = [o for o in outcomes if o and o[0] == "event.created"]
    assert after - before == len(created)
    for _, ev in created:
        assert ev["evidence_url"] and ev["status"] == "pending" and "合成演示数据" in ev["description"]
    assert any(o is None for o in outcomes) or any(o and o[0] == "event.updated" for o in outcomes)


def test_traffic_tick_and_events(ctx):
    sim = Simulator(ctx)
    now = timeutil.now()
    ctx.traffic.step(now)
    snap = ctx.traffic.snapshot()
    assert snap["roads"] and 0 <= snap["city_tpi"] <= 10
    created, updated = sim._traffic_events(now)
    for e in created:
        assert e["event_type"] == "traffic" and e["road_id"]


def test_lifecycle_advances_and_respects_state_machine(client, ctx):
    sim = Simulator(ctx)
    with ctx.session() as s:
        e = s.query(Event).filter(Event.status == "pending").first()
        assert e is not None
        e.updated_at = timeutil.now().replace(year=2000)
        s.commit()
        eid = e.id
    out = sim.lifecycle_once()
    assert out
    logs = client.get(f"/api/events/{out[0]['id']}/logs").json()
    assert logs[-1]["action"] in ("status_changed", "assigned")
    assert client.get(f"/api/events/{eid}").status_code == 200


def test_sensor_tick(ctx):
    rows = ctx.sources.tick(timeutil.now())
    assert rows and all({"id", "throughput", "devices_online"} == set(r) for r in rows)
