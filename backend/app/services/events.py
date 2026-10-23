"""事件服务：序列化、编号、创建、状态机流转，以及由算法分析结果生成事件。"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from cityeye_algo import AnalysisResult
from cityeye_algo.flood import FLOOD_LEVEL_CN
from cityeye_algo.traffic import LEVEL_CN
from fastapi import HTTPException
from sqlalchemy import Integer, cast, func, select
from sqlalchemy.orm import Session

from .. import timeutil
from ..models import Event, EventLog
from ..schemas import EventPatch

if TYPE_CHECKING:
    from ..context import AppContext

STATUS_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "pending": ("monitoring", "processing", "resolved"),
    "monitoring": ("processing", "resolved"),
    "processing": ("resolved",),
    "resolved": ("processing",),
}
STATUS_CN = {"pending": "待核查", "monitoring": "监测中", "processing": "处置中", "resolved": "已办结"}
TYPE_CN = {"fire": "火灾", "traffic": "交通拥堵", "building": "建筑异常", "flood": "内涝积水"}
ACTIVE = ("pending", "monitoring", "processing")

_UNIT_BY_TYPE = {
    "fire": "{d}消防救援大队",
    "traffic": "武汉市公安局交通管理局{s}大队",
    "building": "{d}住建局房屋安全鉴定站",
    "flood": "武汉市水务局排水中心",
}


def default_assignee(event_type: str, district: str) -> str:
    """按事件类型与行政区给出责任单位。"""
    d = district or "江岸区"
    return _UNIT_BY_TYPE[event_type].format(d=d, s=d.removesuffix("区"))


# ------------------------------------------------------------------ 序列化

def event_to_dict(e: Event) -> dict[str, Any]:
    return {
        "id": e.id,
        "event_type": e.event_type,
        "name": e.name,
        "longitude": round(e.longitude, 6),
        "latitude": round(e.latitude, 6),
        "confidence": round(e.confidence, 3),
        "status": e.status,
        "timestamp": timeutil.fmt(e.timestamp),
        "severity": e.severity,
        "source": e.source,
        "district": e.district,
        "address": e.address,
        "grid": e.grid,
        "description": e.description,
        "building_id": e.building_id,
        "road_id": e.road_id,
        "task_id": e.task_id,
        "evidence_url": e.evidence_url,
        "metrics": e.metrics or {},
        "assignee": e.assignee,
        "updated_at": timeutil.fmt(e.updated_at),
    }


def log_to_dict(entry: EventLog) -> dict[str, Any]:
    return {
        "id": entry.id,
        "event_id": entry.event_id,
        "action": entry.action,
        "from_status": entry.from_status,
        "to_status": entry.to_status,
        "operator": entry.operator,
        "note": entry.note,
        "timestamp": timeutil.fmt(entry.timestamp),
    }


def next_id(session: Session, column: Any, prefix: str, width: int = 4) -> str:
    """生成下一个编号（调用方需持有 ctx.id_lock）。"""
    n = session.scalar(select(func.max(cast(func.substr(column, len(prefix) + 1), Integer)))) or 0
    return f"{prefix}{int(n) + 1:0{width}d}"


def add_log(
    session: Session, event_id: str, action: str, operator: str, note: str, ts: datetime,
    from_status: str | None = None, to_status: str | None = None,
) -> EventLog:
    entry = EventLog(event_id=event_id, action=action, operator=operator, note=note, timestamp=ts, from_status=from_status, to_status=to_status)
    session.add(entry)
    return entry


# ------------------------------------------------------------------ 创建

def create_event(
    ctx: "AppContext",
    session: Session,
    *,
    event_type: str,
    name: str,
    longitude: float,
    latitude: float,
    severity: str,
    source: str,
    confidence: float,
    description: str,
    timestamp: datetime | None = None,
    building_id: str | None = None,
    road_id: str | None = None,
    task_id: str | None = None,
    evidence_src: Path | None = None,
    evidence_url: str | None = None,
    metrics: dict[str, Any] | None = None,
    creator: str = "系统",
    created_note: str = "",
    ai_note: str | None = None,
) -> Event:
    """新建事件（status=pending），补齐行政区 / 地址 / 网格，写入 created（及 ai_detected）日志并提交。"""
    ts = timestamp or timeutil.now()
    district, address, grid = ctx.geo.locate(longitude, latitude)
    with ctx.id_lock:
        eid = next_id(session, Event.id, "E")
        if evidence_src is not None:
            evidence_url = ctx.copy_evidence(evidence_src, eid)
        e = Event(
            id=eid, event_type=event_type, name=name[:128], longitude=longitude, latitude=latitude,
            confidence=float(confidence), status="pending", timestamp=ts, severity=severity, source=source,
            district=district, address=address, grid=grid, description=description, building_id=building_id,
            road_id=road_id, task_id=task_id, evidence_url=evidence_url, metrics=metrics or {},
            assignee=None, created_at=ts, updated_at=ts,
        )
        session.add(e)
        session.flush()
        add_log(session, eid, "created", creator, created_note or f"{TYPE_CN[event_type]}事件入库：{name}", ts, None, "pending")
        if ai_note:
            add_log(session, eid, "ai_detected", creator, ai_note, ts)
        session.commit()
    return e


# ------------------------------------------------------------------ 流转

def apply_patch(session: Session, e: Event, patch: EventPatch, now: datetime | None = None) -> Event:
    """按状态机更新事件并写日志；非法流转抛出 409。"""
    now = now or timeutil.now()
    operator = (patch.operator or "").strip() or "值班员"
    note = (patch.note or "").strip()
    changed = False
    if patch.status and patch.status != e.status:
        if patch.status not in STATUS_TRANSITIONS[e.status]:
            allowed = "、".join(STATUS_CN[s] for s in STATUS_TRANSITIONS[e.status])
            raise HTTPException(
                status_code=409,
                detail=f"非法状态流转：{STATUS_CN[e.status]} → {STATUS_CN[patch.status]}（当前状态仅可流转至：{allowed}）",
            )
        add_log(session, e.id, "status_changed", operator, note or f"状态变更为{STATUS_CN[patch.status]}", now, e.status, patch.status)
        e.status = patch.status
        changed = True
    if patch.assignee is not None and patch.assignee.strip() and patch.assignee.strip() != (e.assignee or ""):
        e.assignee = patch.assignee.strip()
        add_log(session, e.id, "assigned", operator, f"指派至 {e.assignee}" + (f"：{note}" if note and changed else ""), now)
        changed = True
    if not changed and note:
        add_log(session, e.id, "comment", operator, note, now)
        changed = True
    if changed:
        e.updated_at = now
    session.commit()
    return e


def transition(session: Session, e: Event, to_status: str, operator: str, note: str, now: datetime, assignee: str | None = None) -> None:
    """系统内部流转（模拟器自动派单 / 办结），同样遵守状态机。"""
    apply_patch(session, e, EventPatch(status=to_status, assignee=assignee, operator=operator, note=note), now)  # type: ignore[arg-type]


# ------------------------------------------------------------------ 由算法结果生成事件

def severity_for(event_type: str, r: AnalysisResult) -> str:
    """算法指标 → 事件等级（Ⅳ low / Ⅲ medium / Ⅱ high / Ⅰ critical）。"""
    m = r.metrics
    if event_type == "fire":
        ratio, regions, smoke = float(m.get("flame_area_ratio", 0)), int(m.get("flame_regions", 1)), float(m.get("smoke_score", 0))
        if ratio >= 0.02 or regions >= 4:
            return "critical"
        if ratio >= 0.006 or regions >= 2 or smoke >= 0.6:
            return "high"
        return "medium"
    if event_type == "traffic":  # 常发性拥堵多为Ⅲ/Ⅳ级，TPI≥9（接近停滞）升为Ⅱ级
        tpi = float(m.get("max_tpi", m.get("equivalent_tpi", 0)))
        if r.level == "heavy":
            return "high" if tpi >= 9.0 else "medium"
        return "low"
    if event_type == "building":
        if r.level in ("warning", "watch"):
            return "high" if r.level == "warning" else "medium"
        dominant = str(m.get("dominant_change", ""))
        return "high" if float(m.get("change_ratio", 0)) >= 0.05 or "破损" in dominant else "medium"
    # flood
    if r.level == "severe":
        return "critical" if float(m.get("forecast_peak_cm", 0)) >= 50 or float(m.get("water_area_ratio", 0)) >= 0.35 else "high"
    return {"moderate": "medium", "minor": "low"}.get(r.level or "", "low")


def event_name_for(ctx: "AppContext", event_type: str, r: AnalysisResult, lon: float, lat: float, kind: str) -> tuple[str, str | None, str | None]:
    """返回 (事件名称, building_id, road_id)。"""
    geo = ctx.geo
    nb = geo.nearest_building(lon, lat, max_m=45)
    roads = geo.nearest_roads(lon, lat, within_m=80, k=1)
    road = roads[0][0] if roads else None
    building_id = nb[0]["id"] if nb and event_type in ("fire", "building") else None
    road_id = road.id if road and event_type in ("traffic", "flood") else None
    place_b = geo.building_label(nb[0]) if nb else geo.address_of(lon, lat)
    place_r = road.base_name if road else geo.address_of(lon, lat)
    if event_type == "fire":
        name = f"{place_b}疑似火情"
    elif event_type == "traffic":
        name = f"{place_r}{LEVEL_CN.get(r.level or '', '交通拥堵')}" + ("（车辆排队）" if kind == "image" else "")
    elif event_type == "building":
        if kind == "csv":
            name = f"{place_b}沉降{'预警' if r.level == 'warning' else '速率超关注阈值'}"
        else:
            name = f"{place_b}结构异常变化"
    else:
        lvl = FLOOD_LEVEL_CN.get(r.level or "", "积水")
        name = f"{place_r}路面{lvl}"
    return name, building_id, road_id


def event_from_result(
    ctx: "AppContext",
    session: Session,
    *,
    event_type: str,
    algorithm_name: str,
    result: AnalysisResult,
    longitude: float,
    latitude: float,
    source: str,
    input_kind: str,
    input_label: str,
    task_id: str | None = None,
    timestamp: datetime | None = None,
    evidence_src: Path | None = None,
    evidence_url: str | None = None,
    building_id: str | None = None,
    road_id: str | None = None,
    creator: str = "系统",
) -> Event:
    """用一次真实算法分析的结论生成事件（仅在 result.detected 为真时调用）。"""
    name, bid, rid = event_name_for(ctx, event_type, result, longitude, latitude, input_kind)
    metrics = {k: v for k, v in result.metrics.items() if k != "elapsed_ms"}
    metrics["algorithm"] = algorithm_name
    description = f"{algorithm_name} 分析结论：{result.summary}。{input_label}"
    return create_event(
        ctx, session, event_type=event_type, name=name, longitude=longitude, latitude=latitude,
        severity=severity_for(event_type, result), source=source, confidence=result.confidence,
        description=description, timestamp=timestamp, building_id=building_id or bid, road_id=road_id or rid,
        task_id=task_id, evidence_src=evidence_src, evidence_url=evidence_url, metrics=metrics, creator=creator,
        ai_note=f"{algorithm_name} 检出异常（置信度 {result.confidence:.2f}）：{result.summary}",
    )
