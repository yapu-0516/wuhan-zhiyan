"""城市运行总览统计（GET /api/stats/overview），全部由数据库实时计算。

城市安全指数 safety_score（0~100，越高越安全）：
    score = 100
            − Σ_未办结事件 w_等级 × w_状态
            − 1.5 × max(0, 路网TPI − 4)          # 路网进入轻度拥堵以上时扣分
            − 3 × 沉降预警建筑数 − 1 × 沉降关注建筑数
    w_等级：low 0.3 / medium 0.8 / high 1.6 / critical 3.5；
    w_状态：pending 1.0（未核查风险最高）/ processing 0.8 / monitoring 0.6；
    结果截断到 [0, 100] 并取整。
"""
from __future__ import annotations

from collections import Counter
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from cityeye_algo.traffic import tpi_level
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import timeutil
from ..models import Event, EventLog, SettlementSeries

if TYPE_CHECKING:
    from ..context import AppContext

TYPES = ("fire", "traffic", "building", "flood")
STATUSES = ("pending", "monitoring", "processing", "resolved")
SEVERITIES = ("low", "medium", "high", "critical")
W_SEVERITY = {"low": 0.3, "medium": 0.8, "high": 1.6, "critical": 3.5}
W_STATUS = {"pending": 1.0, "processing": 0.8, "monitoring": 0.6}


def safety_score(active: list[tuple[str, str]], city_tpi: float, n_warning: int, n_watch: int) -> int:
    score = 100.0
    score -= sum(W_SEVERITY[sev] * W_STATUS.get(st, 0.0) for sev, st in active)
    score -= 1.5 * max(0.0, city_tpi - 4.0)
    score -= 3.0 * n_warning + 1.0 * n_watch
    return int(round(min(100.0, max(0.0, score))))


def overview(ctx: "AppContext", session: Session) -> dict[str, Any]:
    now = timeutil.now()
    today = timeutil.start_of_day(now)
    rows = session.execute(select(Event.id, Event.event_type, Event.status, Event.severity, Event.district, Event.timestamp)).all()
    total = len(rows)
    by_type = Counter(r.event_type for r in rows)
    by_status = Counter(r.status for r in rows)
    by_sev = Counter(r.severity for r in rows)
    by_dist = Counter(r.district for r in rows if r.district)
    for d in ctx.geo.region.get("districts", []):
        by_dist.setdefault(d, 0)

    resolved_today = session.scalar(
        select(func.count(func.distinct(EventLog.event_id)))
        .join(Event, Event.id == EventLog.event_id)
        .where(EventLog.to_status == "resolved", EventLog.timestamp >= today, Event.status == "resolved")
    ) or 0

    # 平均响应时长：事件发现 → 首次状态变更（分钟），统计近 7 天
    first_change = (
        select(EventLog.event_id, func.min(EventLog.timestamp).label("t"))
        .where(EventLog.action == "status_changed")
        .group_by(EventLog.event_id)
        .subquery()
    )
    pairs = session.execute(
        select(Event.timestamp, first_change.c.t).join(first_change, first_change.c.event_id == Event.id).where(Event.timestamp >= now - timedelta(days=7))
    ).all()
    gaps = [(t - ts).total_seconds() / 60 for ts, t in pairs if t >= ts]
    avg_response = round(sum(gaps) / len(gaps), 1) if gaps else 0.0

    start = now.replace(minute=0, second=0) - timedelta(hours=23)
    hourly = [Counter() for _ in range(24)]
    for row in rows:
        index = int((row.timestamp - start).total_seconds() // 3600)
        if 0 <= index < len(hourly):
            hourly[index][row.event_type] += 1
    trend = [
        {
            "time": (start + timedelta(hours=index)).strftime("%H:00"),
            **{event_type: hourly[index].get(event_type, 0) for event_type in TYPES},
        }
        for index in range(24)
    ]

    risk = Counter(session.scalars(select(SettlementSeries.risk_level)).all())
    city_tpi = ctx.traffic.city_tpi()
    active = [(r.severity, r.status) for r in rows if r.status != "resolved"]
    online, total_dev = ctx.sources.totals(session)
    return {
        "total": total,
        "active": len(active),
        "today": sum(1 for r in rows if r.timestamp >= today),
        "resolved_today": int(resolved_today),
        "resolve_rate": round(by_status.get("resolved", 0) / total, 3) if total else 0.0,
        "avg_response_min": avg_response,
        "by_type": {t: by_type.get(t, 0) for t in TYPES},
        "by_status": {s: by_status.get(s, 0) for s in STATUSES},
        "by_severity": {s: by_sev.get(s, 0) for s in SEVERITIES},
        "by_district": [{"name": n, "count": c} for n, c in sorted(by_dist.items(), key=lambda kv: (-kv[1], kv[0]))],
        "trend": trend,
        "city_index": {
            "traffic_tpi": round(city_tpi, 2),
            "traffic_level": tpi_level(city_tpi),
            "safety_score": safety_score(active, city_tpi, risk.get("warning", 0), risk.get("watch", 0)),
            "sensors_online": online,
            "sensors_total": total_dev,
        },
        "updated_at": timeutil.fmt(now),
    }
