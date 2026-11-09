"""路网实时路况（内存态）。

车速模型（模拟数据，用于驱动演示；TPI / 等级由 cityeye_algo.traffic 的真实算法计算）：
    v = v_ff · (1 − 0.88 · c(t) · s_road) · (1 + ε_t) · f_incident
    - c(t)：日内拥堵强度曲线，工作日早高峰 8:15、晚高峰 17:55、午间小高峰；周末早高峰推迟且减弱；
    - s_road：道路敏感度 = 道路等级系数 × 随机系数（按道路编号固定）+ 主干道加成；
    - ε_t：AR(1) 噪声（φ=0.85）；f_incident：随机交通事件（事故 / 施工）造成的车速折减。
"""
from __future__ import annotations

import math
import random
import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import numpy as np
from cityeye_algo.traffic import network_tpi, speed_to_tpi, tpi_level

from .. import timeutil
from ..geo import GeoRepository, Road

ARTERIALS = (
    "解放大道", "中山大道", "京汉大道", "建设大道", "沿江大道", "香港路", "发展大道", "江汉北路", "台北路", "新华路",
    "武珞路", "珞喻路", "雄楚大道", "友谊大道", "和平大道", "鹦鹉大道", "汉阳大道", "琴台大道", "光谷大道", "楚雄大道",
)
CLASS_SENSITIVITY = {"trunk": 1.05, "primary": 1.0, "secondary": 0.86, "tertiary": 0.7}


def congestion_curve(t: datetime) -> float:
    """日内拥堵强度 c ∈ [0, 1]。"""
    h = t.hour + t.minute / 60 + t.second / 3600
    if t.weekday() >= 5:
        am, am_c, pm, mid = 0.40, 10.2, 0.58, 0.40
    else:
        am, am_c, pm, mid = 0.70, 8.25, 0.76, 0.24
    c = (
        0.06
        + am * math.exp(-(((h - am_c) / 0.9) ** 2))
        + pm * math.exp(-(((h - 17.9) / 1.05) ** 2))
        + mid * math.exp(-(((h - 12.6) / 1.5) ** 2))
        - 0.05 * math.exp(-(((h - 3.5) / 2.0) ** 2))
    )
    return min(1.0, max(0.0, c))


@dataclass
class RoadLive:
    road: Road
    free_flow: float
    sensitivity: float
    speed: float = 0.0
    tpi: float = 0.0
    level: str = "smooth"
    noise: float = 0.0
    incident_until: datetime | None = None
    incident_factor: float = 1.0
    history: deque[tuple[datetime, float]] = field(default_factory=lambda: deque(maxlen=180))
    heavy_ticks: int = 0
    calm_ticks: int = 0
    last_event_at: datetime | None = None


class TrafficState:
    def __init__(self, geo: GeoRepository) -> None:
        self.geo = geo
        self.lock = threading.Lock()
        self.roads: dict[str, RoadLive] = {}
        self.rng = random.Random(7)
        self.reset()

    def reset(self, now: datetime | None = None) -> None:
        with self.lock:
            self.rng = random.Random(7)
            self.roads = {}
            for r in self.geo.roads:
                rr = random.Random(f"{r.id}:{r.name}")
                arterial = any(r.name.startswith(a) for a in ARTERIALS)
                sens = CLASS_SENSITIVITY.get(r.highway, 0.7) * rr.uniform(0.82, 1.1) + (0.1 if arterial else 0.0)
                self.roads[r.id] = RoadLive(road=r, free_flow=r.speed_limit * rr.uniform(0.95, 1.08), sensitivity=sens)
        self.step(now or timeutil.now(), initial=True)

    # ------------------------------------------------------------------ 模型
    def model_speed(self, st: RoadLive, t: datetime) -> float:
        return st.free_flow * max(0.08, 1 - 0.88 * congestion_curve(t) * st.sensitivity)

    def step(self, now: datetime, dt_sec: float = 10.0, initial: bool = False) -> None:
        with self.lock:
            for st in self.roads.values():
                if not initial:
                    st.noise = 0.85 * st.noise + self.rng.gauss(0, 0.035)
                    if st.incident_until and now >= st.incident_until:
                        st.incident_until, st.incident_factor = None, 1.0
                    elif st.incident_until is None and self.rng.random() < 0.00025 * dt_sec / 10.0:
                        st.incident_until = now + timedelta(minutes=self.rng.uniform(6, 18))
                        st.incident_factor = self.rng.uniform(0.3, 0.5)
                speed = self.model_speed(st, now) * (1 + st.noise) * st.incident_factor
                st.speed = float(np.clip(speed, 3.0, st.free_flow * 1.08))
                st.tpi = float(speed_to_tpi(st.speed, st.free_flow))
                st.level = tpi_level(st.tpi)
                st.history.append((now, st.speed))
                st.heavy_ticks = st.heavy_ticks + 1 if st.level == "heavy" else 0
                st.calm_ticks = st.calm_ticks + 1 if st.level in ("smooth", "basic") else 0

    def synth_series(
        self, road_id: str, end: datetime, minutes: int = 150, step_min: int = 2,
        incident: tuple[datetime, datetime, float] | None = None, seed: int = 0,
    ) -> tuple[list[datetime], np.ndarray]:
        """按同一车速模型生成某路段历史车速序列（用于种子数据），可叠加事故时段。"""
        st = self.roads[road_id]
        rng = np.random.default_rng(seed)
        times = [end - timedelta(minutes=minutes - i * step_min) for i in range(minutes // step_min + 1)]
        noise = np.zeros(len(times))
        for i in range(1, len(times)):
            noise[i] = 0.8 * noise[i - 1] + rng.normal(0, 0.035)
        speeds = np.array([self.model_speed(st, t) for t in times]) * (1 + noise)
        if incident:
            t0, t1, factor = incident
            ramp = np.array([1.0 if t0 <= t <= t1 else 0.0 for t in times])
            ramp = np.convolve(ramp, np.ones(3) / 3, mode="same")
            speeds *= 1 - (1 - factor) * ramp
        return times, np.clip(speeds, 3.0, st.free_flow * 1.08)

    # ------------------------------------------------------------------ 查询
    def city_tpi(self) -> float:
        with self.lock:
            if not self.roads:
                return 0.0
            return network_tpi([s.tpi for s in self.roads.values()], [max(s.road.length_m, 1.0) for s in self.roads.values()])

    def props(self, road_id: str) -> dict[str, Any]:
        st = self.roads.get(road_id)
        if st is None:
            return {"speed": 0.0, "tpi": 0.0, "level": "smooth"}
        return {"speed": round(st.speed, 1), "tpi": round(st.tpi, 2), "level": st.level}

    def snapshot(self) -> dict[str, Any]:
        tpi = self.city_tpi()
        with self.lock:
            roads = [{"id": rid, "speed": round(s.speed, 1), "tpi": round(s.tpi, 2), "level": s.level} for rid, s in self.roads.items()]
        return {"city_tpi": round(tpi, 2), "level": tpi_level(tpi), "roads": roads}

    def roads_geojson(self) -> dict[str, Any]:
        feats = []
        for r in self.geo.roads:
            p = {"id": r.id, "name": r.name, "highway": r.highway, "length_m": r.length_m, "speed_limit": r.speed_limit}
            p.update(self.props(r.id))
            feats.append({"type": "Feature", "id": r.id, "geometry": r.geometry, "properties": p})
        return {"type": "FeatureCollection", "features": feats}
