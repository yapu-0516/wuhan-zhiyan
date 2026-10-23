"""事件接口（docs/api.md §2）。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select

from ..context import AppContext, bad_request, get_ctx, not_found
from ..models import Event, EventLog
from ..schemas import CityEventOut, EventCreate, EventLogOut, EventPatch, EventSource, EventStatus, EventType, Severity
from ..services.events import apply_patch, create_event, event_to_dict, log_to_dict

router = APIRouter(prefix="/events", tags=["事件"])


@router.get("", response_model=list[CityEventOut], summary="事件列表（按发现时间倒序）")
def list_events(
    type: EventType | None = None,
    status: EventStatus | None = None,
    severity: Severity | None = None,
    source: EventSource | None = None,
    q: str | None = Query(default=None, max_length=64, description="名称 / 地址 / 编号模糊匹配"),
    limit: int = Query(default=500, ge=1, le=2000),
    ctx: AppContext = Depends(get_ctx),
) -> list[dict]:
    stmt = select(Event)
    if type:
        stmt = stmt.where(Event.event_type == type)
    if status:
        stmt = stmt.where(Event.status == status)
    if severity:
        stmt = stmt.where(Event.severity == severity)
    if source:
        stmt = stmt.where(Event.source == source)
    if q and q.strip():
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Event.name.like(like), Event.address.like(like), Event.id.like(like)))
    with ctx.session() as s:
        return [event_to_dict(e) for e in s.scalars(stmt.order_by(Event.timestamp.desc(), Event.id.desc()).limit(limit))]


@router.get("/{event_id}", response_model=CityEventOut, summary="事件详情")
def get_event(event_id: str, ctx: AppContext = Depends(get_ctx)) -> dict:
    with ctx.session() as s:
        e = s.get(Event, event_id)
        if e is None:
            raise not_found(f"事件 {event_id} 不存在")
        return event_to_dict(e)


@router.get("/{event_id}/logs", response_model=list[EventLogOut], summary="事件处置日志（时间正序）")
def get_logs(event_id: str, ctx: AppContext = Depends(get_ctx)) -> list[dict]:
    with ctx.session() as s:
        if s.get(Event, event_id) is None:
            raise not_found(f"事件 {event_id} 不存在")
        rows = s.scalars(select(EventLog).where(EventLog.event_id == event_id).order_by(EventLog.timestamp, EventLog.id))
        return [log_to_dict(r) for r in rows]


@router.post("", response_model=CityEventOut, status_code=201, summary="人工 / 市民上报事件")
def post_event(body: EventCreate, ctx: AppContext = Depends(get_ctx)) -> dict:
    if not ctx.geo.in_region(body.longitude, body.latitude):
        raise bad_request("坐标不在示范区范围内，请检查经纬度")
    creator = "市民上报" if body.source == "citizen" else "人工上报"
    with ctx.session() as s:
        e = create_event(
            ctx, s, event_type=body.event_type, name=body.name.strip(), longitude=body.longitude, latitude=body.latitude,
            severity=body.severity, source=body.source, confidence=body.confidence, description=body.description.strip(),
            creator=creator, metrics={"channel": creator},
        )
        data = event_to_dict(e)
    ctx.hub.publish("event.created", data)
    return data


@router.patch("/{event_id}", response_model=CityEventOut, summary="更新事件（状态流转 / 指派 / 备注）")
def patch_event(event_id: str, body: EventPatch, ctx: AppContext = Depends(get_ctx)) -> dict:
    with ctx.session() as s:
        e = s.get(Event, event_id)
        if e is None:
            raise not_found(f"事件 {event_id} 不存在")
        apply_patch(s, e, body)
        data = event_to_dict(e)
    ctx.hub.publish("event.updated", data)
    return data
