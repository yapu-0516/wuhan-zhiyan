"""实时模拟器（FastAPI lifespan 中运行的 asyncio 后台任务）。

- 路况：每 traffic_interval 秒按车速模型推进一步并推送 traffic.updated；某路段持续严重拥堵时，
  用 TrafficPulse 分析其最近 10 分钟实时车速序列，检出持续拥堵才生成事件（限流）；
  路况恢复畅通后自动办结该路段未办结的拥堵事件；
- 数据源：每 sensor_interval 秒刷新吞吐与在线设备数，推送 sensor.tick；
- 巡检流水线：每 sim_interval 秒随机选一个场景，在示例数据（含反例）上**真实运行算法**，
  仅当算法检出时才生成事件；同类事件 150 m 内已有未办结事件时只追加复核日志；
- 生命周期：定期把少量超时事件按状态机自动推进（自动派单 / 办结），并清理过多的历史数据；
- 心跳：每 heartbeat_interval 秒推送 heartbeat（与模拟器开关无关）。
"""
from __future__ import annotations

import asyncio
import logging
import random
import tempfile
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

import cityeye_algo as ca
import numpy as np
from cityeye_algo.traffic import TrafficSeriesAnalyzer
from sqlalchemy import delete, func, select

from .. import timeutil
from ..models import Event, EventLog, Task
from .events import ACTIVE, STATUS_CN, add_log, default_assignee, event_from_result, event_to_dict, transition

if TYPE_CHECKING:
    from ..context import AppContext

log = logging.getLogger("cityeye.sim")

MAX_ACTIVE = 28
MAX_EVENTS = 200
MAX_TASKS = 100
PATROL_SCENARIOS = {  # 场景 → (权重, 数据源)
    "fire": (0.3, "drone"),
    "flood": (0.25, "sensor"),
    "building": (0.15, "satellite"),
    "traffic": (0.3, "video"),
}


def random_site(geo: Any, r: random.Random, scenario: str) -> tuple[float, float]:
    """演示场景的随机发生位置：交通 / 内涝取主干道上的点，火灾 / 建筑取汉口侧对应类别建筑质心。"""
    if scenario in ("traffic", "flood") and geo.roads:
        roads = geo.roads_named("解放大道", "京汉大道", "建设大道", "中山大道", "沿江大道", "香港路", "新华路") or geo.roads
        return geo.random_point_on_road(r, r.choice(roads))
    cats = ("commercial", "residential", "office", "other") if scenario == "fire" else ("residential", "other", "public")
    cands = [b for b in geo.buildings.values() if b.get("category") in cats and b.get("district") in ("江汉区", "江岸区")]
    if not cands:
        lon, lat = geo.region["center"]
        return lon, lat
    b = r.choice(cands)
    return b["longitude"], b["latitude"]


class Simulator:
    def __init__(self, ctx: "AppContext") -> None:
        self.ctx = ctx
        self.rng = random.Random(2026)
        self._tasks: list[asyncio.Task[None]] = []
        self._last_traffic_event = timeutil.now() - timedelta(hours=1)
        self._traffic_analyzer = TrafficSeriesAnalyzer()

    def start(self) -> None:
        s = self.ctx.settings
        self._tasks.append(asyncio.create_task(self._loop(s.heartbeat_interval, self._heartbeat), name="heartbeat"))
        if s.simulator:
            self._tasks += [
                asyncio.create_task(self._loop(s.traffic_interval, self._traffic_tick), name="traffic"),
                asyncio.create_task(self._loop(s.sensor_interval, self._sensor_tick), name="sensor"),
                asyncio.create_task(self._loop(s.sim_interval, self._patrol, initial_delay=min(8.0, s.sim_interval)), name="patrol"),
                asyncio.create_task(self._loop(s.lifecycle_interval, self._lifecycle, initial_delay=20.0), name="lifecycle"),
            ]
            log.info("模拟器已启动：路况 %ss / 传感 %ss / 巡检 %ss", s.traffic_interval, s.sensor_interval, s.sim_interval)

    async def stop(self) -> None:
        for t in self._tasks:
            t.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

    async def _loop(self, interval: float, fn: Any, initial_delay: float | None = None) -> None:
        await asyncio.sleep(interval if initial_delay is None else initial_delay)
        while True:
            try:
                await fn()
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001 - 单次失败不应终止循环
                log.exception("模拟器任务 %s 执行失败", getattr(fn, "__name__", fn))
            await asyncio.sleep(interval)

    # ------------------------------------------------------------------ 心跳 / 传感
    async def _heartbeat(self) -> None:
        await self.ctx.hub.broadcast("heartbeat", {})

    async def _sensor_tick(self) -> None:
        await self.ctx.hub.broadcast("sensor.tick", {"sources": self.ctx.sources.tick(timeutil.now())})

    # ------------------------------------------------------------------ 路况
    async def _traffic_tick(self) -> None:
        now = timeutil.now()
        self.ctx.traffic.step(now, self.ctx.settings.traffic_interval)
        await self.ctx.hub.broadcast("traffic.updated", self.ctx.traffic.snapshot())
        created, updated = await asyncio.to_thread(self._traffic_events, now)
        for e in created:
            await self.ctx.hub.broadcast("event.created", e)
        for e in updated:
            await self.ctx.hub.broadcast("event.updated", e)

    def _traffic_events(self, now: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        ctx, created, updated = self.ctx, [], []
        need = max(3, int(60 / ctx.settings.traffic_interval))  # 持续约 1 分钟严重拥堵
        with ctx.session() as s:
            active = {e.road_id: e for e in s.scalars(select(Event).where(Event.event_type == "traffic", Event.status.in_(ACTIVE), Event.road_id.is_not(None)))}
            for rid, st in ctx.traffic.roads.items():
                ev = active.get(rid)
                if ev is not None and st.calm_ticks >= 3 * need:
                    transition(s, ev, "resolved", "系统", f"路况已恢复（TPI {st.tpi:.1f}，{st.speed:.0f} km/h），自动办结", now)
                    updated.append(event_to_dict(ev))
                    continue
                if ev is not None or st.heavy_ticks < need:
                    continue
                if (now - self._last_traffic_event).total_seconds() < 300:
                    continue
                if st.last_event_at and (now - st.last_event_at).total_seconds() < 3600:
                    continue
                hist = list(st.history)[-60:]
                times = [t for t, _ in hist]
                speeds = np.array([v for _, v in hist])
                chart = Path(tempfile.mkstemp(suffix=".png", dir=ctx.results_dir)[1])
                res = self._traffic_analyzer.analyze_series(
                    times, speeds, chart, free_flow_kmh=st.free_flow, road_name=st.road.base_name,
                    min_congestion_min=1.0, smooth_min=0.5, forecast_min=30,
                )
                if res.detected and res.metrics.get("ongoing"):
                    lon, lat = ctx.geo.random_point_on_road(self.rng, st.road)
                    e = event_from_result(
                        ctx, s, event_type="traffic", algorithm_name=self._traffic_analyzer.meta.name, result=res,
                        longitude=lon, latitude=lat, source="sensor", input_kind="csv", road_id=rid, evidence_src=chart,
                        input_label=f"输入：{st.road.base_name}实时车速序列（近 {len(hist) * ctx.settings.traffic_interval / 60:.0f} 分钟，模拟数据）",
                    )
                    created.append(event_to_dict(e))
                    st.last_event_at = self._last_traffic_event = now
                chart.unlink(missing_ok=True)
        return created, updated

    # ------------------------------------------------------------------ 巡检流水线
    async def _patrol(self) -> None:
        msg = await asyncio.to_thread(self.patrol_once)
        if msg:
            await self.ctx.hub.broadcast(*msg)

    def patrol_once(self, scenario: str | None = None) -> tuple[str, dict[str, Any]] | None:
        """执行一次巡检：返回 ("event.created" | "event.updated", 事件) 或 None（未检出）。"""
        ctx, r = self.ctx, self.rng
        kinds = list(PATROL_SCENARIOS)
        scenario = scenario or r.choices(kinds, weights=[PATROL_SCENARIOS[k][0] for k in kinds])[0]
        source = PATROL_SCENARIOS[scenario][1]
        pool = [smp for smp in ctx.samples.items if smp["type"] == scenario and (smp["kind"] != "csv" or scenario == "flood")]
        if not pool:
            return None
        smp = r.choice(pool)
        source = "sensor" if smp["kind"] == "csv" else ("drone" if scenario == "flood" else source)
        lon, lat = random_site(ctx.geo, r, scenario)
        with tempfile.TemporaryDirectory(dir=ctx.results_dir) as tmp:
            analyzer, res = ca.run(scenario, ctx.samples.paths(smp), Path(tmp), "patrol")
            if not res.detected:
                log.info("巡检 %s（%s）：未检出", scenario, smp["id"])
                return None
            now = timeutil.now()
            with ctx.session() as s:
                dup = self._nearby_active(s, scenario, lon, lat)
                if dup is not None:
                    add_log(s, dup.id, "comment", "巡检复核", f"{analyzer.meta.name} 复核仍检出异常（置信度 {res.confidence:.2f}）", now)
                    dup.updated_at = now
                    s.commit()
                    return "event.updated", event_to_dict(dup)
                art = res.primary_artifact
                e = event_from_result(
                    ctx, s, event_type=scenario, algorithm_name=analyzer.meta.name, result=res, longitude=lon, latitude=lat,
                    source=source, input_kind=analyzer.meta.input_kind, evidence_src=art.path if art else None,
                    input_label=f"输入：演示巡检示例「{smp['name']}」（合成演示数据）",
                )
                log.info("巡检 %s（%s）：检出 → %s", scenario, smp["id"], e.id)
                return "event.created", event_to_dict(e)

    def _nearby_active(self, s: Any, event_type: str, lon: float, lat: float) -> Event | None:
        cands = s.scalars(select(Event).where(Event.event_type == event_type, Event.status.in_(ACTIVE))).all()
        for e in cands:
            if np.hypot((e.longitude - lon) * 95_800, (e.latitude - lat) * 110_540) < 150:
                return e
        return None

    # ------------------------------------------------------------------ 生命周期
    async def _lifecycle(self) -> None:
        for e in await asyncio.to_thread(self.lifecycle_once):
            await self.ctx.hub.broadcast("event.updated", e)

    def lifecycle_once(self) -> list[dict[str, Any]]:
        """推进至多 1 个超时事件；未办结事件过多时批量归档最旧的；清理超量历史。"""
        ctx, now, out = self.ctx, timeutil.now(), []
        with ctx.session() as s:
            active = s.scalars(select(Event).where(Event.status.in_(ACTIVE)).order_by(Event.updated_at)).all()
            due = []
            for e in active:
                idle = (now - e.updated_at).total_seconds() / 60
                if e.status == "pending" and idle > 15:
                    due.append((e, "processing" if e.event_type in ("fire", "traffic") else "monitoring", "系统自动派单"))
                elif e.status == "monitoring" and idle > 30 and e.event_type != "building":
                    due.append((e, "processing", "系统自动派单"))
                elif e.status == "processing" and idle > 40 and e.event_type != "building":
                    due.append((e, "resolved", "系统"))
            if due:
                e, to, op = self.rng.choice(due[:5])
                unit = default_assignee(e.event_type, e.district) if to != "resolved" else None
                note = {"processing": f"超时未处置，已自动派单至{unit}", "monitoring": "已转入持续监测",
                        "resolved": "处置单位回告已完成，系统自动办结"}[to]
                transition(s, e, to, op, note, now, assignee=unit)
                out.append(event_to_dict(e))
            overflow = len(active) - MAX_ACTIVE
            for e in active[: max(0, overflow)]:
                if e.status in ("pending", "monitoring", "processing") and e.event_type != "building":
                    transition(s, e, "resolved", "系统", f"活跃事件超过 {MAX_ACTIVE} 件，{STATUS_CN[e.status]}事件按时间顺序归档办结", now)
                    out.append(event_to_dict(e))
            self._prune(s)
        return out

    def _prune(self, s: Any) -> None:
        total = s.scalar(select(func.count()).select_from(Event)) or 0
        if total > MAX_EVENTS:
            old = s.scalars(select(Event).where(Event.status == "resolved").order_by(Event.timestamp).limit(total - MAX_EVENTS)).all()
            for e in old:
                self._remove_file(e.evidence_url, only_prefix=f"/files/evidence/{e.id}")
                s.execute(delete(EventLog).where(EventLog.event_id == e.id))
                s.delete(e)
            s.commit()
        n_tasks = s.scalar(select(func.count()).select_from(Task)) or 0
        if n_tasks > MAX_TASKS:
            old_tasks = s.scalars(select(Task).where(Task.status.in_(("done", "failed")), Task.origin != "seed")
                                  .order_by(Task.created_at).limit(n_tasks - MAX_TASKS)).all()
            for t in old_tasks:
                for f in self.ctx.results_dir.glob(f"{t.id}_*"):
                    f.unlink(missing_ok=True)
                s.delete(t)
            s.commit()

    def _remove_file(self, url: str | None, only_prefix: str) -> None:
        if url and url.startswith(only_prefix):
            p = self.ctx.path_for(url)
            if p is not None:
                p.unlink(missing_ok=True)
