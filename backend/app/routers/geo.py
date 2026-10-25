"""城市三维对象接口（docs/api.md §3）：建筑、道路（含实时路况）、应急资源点位。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select

from ..context import AppContext, get_ctx, not_found
from ..models import Event, SettlementSeries
from ..schemas import BuildingDetailOut, PoiOut
from ..services.events import event_to_dict

router = APIRouter(tags=["城市对象"])


@router.get("/buildings", summary="建筑轮廓 GeoJSON（OpenStreetMap，含沉降风险等级）")
def buildings(ctx: AppContext = Depends(get_ctx)) -> Response:
    return Response(content=ctx.buildings_json(), media_type="application/json")


@router.get("/buildings/fine", summary="武汉精细建筑轮廓 GeoJSON（本地派生数据）")
def fine_buildings(ctx: AppContext = Depends(get_ctx)) -> Response:
    try:
        payload = ctx.fine_buildings_json()
    except FileNotFoundError as exc:
        raise not_found("精细建筑图层不存在，请运行 data/scripts/build_wuhan_buildings.py") from exc
    return Response(content=payload, media_type="application/json")


@router.get("/buildings/{building_id}", response_model=BuildingDetailOut, summary="建筑详情（含沉降监测与关联事件）")
def building_detail(building_id: str, ctx: AppContext = Depends(get_ctx)) -> dict:
    props = ctx.geo.building_props(building_id)
    if props is None:
        raise not_found(f"建筑 {building_id} 不存在")
    with ctx.session() as s:
        row = s.get(SettlementSeries, building_id)
        events = s.scalars(select(Event).where(Event.building_id == building_id).order_by(Event.timestamp.desc())).all()
        monitoring = None
        if row is not None:
            monitoring = {
                "series": row.series,
                "rate_mm_per_month": row.rate_mm_per_month,
                "acceleration": row.acceleration,
                "cumulative_mm": row.cumulative_mm,
                "risk_level": row.risk_level,
                "analysis": row.analysis,
            }
        return {"properties": props, "monitoring": monitoring, "events": [event_to_dict(e) for e in events]}


@router.get("/roads", summary="主干路网 GeoJSON + 实时路况（speed / tpi / level）")
def roads(ctx: AppContext = Depends(get_ctx)) -> dict:
    return ctx.traffic.roads_geojson()


@router.get("/pois", response_model=list[PoiOut], summary="应急资源点位")
def pois(ctx: AppContext = Depends(get_ctx)) -> list[dict]:
    return ctx.geo.pois
