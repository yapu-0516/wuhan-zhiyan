"""监测数据源：数据库保存基线配置，模拟器在内存中刷新实时吞吐与在线设备数。"""
from __future__ import annotations

import random
import threading
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import timeutil
from ..models import Source

LIVE_STATUSES = ("在线", "采集中")


def source_to_dict(s: Source, live: dict[str, Any] | None = None) -> dict[str, Any]:
    live = live or {}
    return {
        "id": s.id,
        "name": s.name,
        "type": s.type,
        "icon": s.icon,
        "desc": s.desc,
        "status": s.status,
        "devices_online": int(live.get("devices_online", s.devices_online)),
        "devices_total": s.devices_total,
        "throughput": round(float(live.get("throughput", s.throughput)), 1),
        "unit": s.unit,
        "last_active": timeutil.fmt(live.get("last_active", s.last_active)),
        "coverage": s.coverage,
    }


class SourceState:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._base: dict[str, Source] = {}
        self._live: dict[str, dict[str, Any]] = {}
        self._rng = random.Random(11)

    def load(self, session: Session) -> None:
        rows = session.scalars(select(Source).order_by(Source.sort_order)).all()
        with self._lock:
            self._base = {r.id: r for r in rows}
            self._live = {}

    def tick(self, now: datetime) -> list[dict[str, Any]]:
        """刷新一次实时值，返回 sensor.tick 推送内容。"""
        out = []
        with self._lock:
            for sid, s in self._base.items():
                if s.status not in LIVE_STATUSES:
                    continue
                prev = self._live.get(sid, {"devices_online": s.devices_online})
                online = prev["devices_online"]
                if self._rng.random() < 0.25:
                    online = online + self._rng.choice((-1, 1))
                online = max(int(s.devices_total * 0.85), min(s.devices_total, online))
                throughput = max(0.0, s.throughput * (online / max(1, s.devices_online)) * (1 + self._rng.gauss(0, 0.06)))
                self._live[sid] = {"devices_online": online, "throughput": throughput, "last_active": now}
                out.append({"id": sid, "throughput": round(throughput, 1), "devices_online": online})
        return out

    def list(self, session: Session) -> list[dict[str, Any]]:
        rows = session.scalars(select(Source).order_by(Source.sort_order)).all()
        with self._lock:
            return [source_to_dict(r, self._live.get(r.id)) for r in rows]

    def totals(self, session: Session) -> tuple[int, int]:
        items = self.list(session)
        return sum(i["devices_online"] for i in items), sum(i["devices_total"] for i in items)
