"""城市三维对象接口（docs/api.md §3）：建筑、道路（含实时路况）、应急资源点位。"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import select

from ..context import AppContext, get_ctx, not_found
from ..models import Event, SettlementSeries
from ..schemas import BuildingDetailOut, PoiOut, SpatialFeatureOut, SpatialFeaturePatch
from ..services.events import event_to_dict

router = APIRouter(tags=["城市对象"])


def _write_geojson(ctx: AppContext, filename: str, features: list[dict]) -> None:
    path = ctx.settings.geo_dir / filename
    tmp = path.with_suffix(".tmp")
    tmp.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    tmp.replace(path)
    ctx.reload_geo()


@router.get(
    "/spatial/{entity_type}/{entity_id}",
    response_model=SpatialFeatureOut,
    summary="查询建筑或道路空间对象",
)
def spatial_feature(
    entity_type: str,
    entity_id: str,
    ctx: AppContext = Depends(get_ctx),
) -> dict:
    if entity_type == "building":
        feature = next((f for f in ctx.geo.building_features if f["properties"]["id"] == entity_id), None)
    elif entity_type == "road":
        feature = next((f for f in ctx.geo.road_features if f["properties"]["id"] == entity_id), None)
    else:
        raise not_found("空间对象类型必须是 building 或 road")
    if feature is None:
        raise not_found(f"{entity_type} {entity_id} 不存在")
    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "geometry": feature.get("geometry") or {},
        "properties": feature.get("properties") or {},
    }


@router.patch(
    "/spatial/{entity_type}/{entity_id}",
    response_model=SpatialFeatureOut,
    summary="维护建筑或道路属性和几何",
)
def patch_spatial_feature(
    entity_type: str,
    entity_id: str,
    body: SpatialFeaturePatch,
    ctx: AppContext = Depends(get_ctx),
) -> dict:
    if entity_type == "building":
        features = ctx.geo.building_features
        filename = "buildings.geojson"
    elif entity_type == "road":
        features = ctx.geo.road_features
        filename = "roads.geojson"
    else:
        raise not_found("空间对象类型必须是 building 或 road")
    feature = next((f for f in features if f["properties"]["id"] == entity_id), None)
    if feature is None:
        raise not_found(f"{entity_type} {entity_id} 不存在")
    if body.geometry is not None:
        geometry_type = body.geometry.get("type")
        expected = "Polygon" if entity_type == "building" else "LineString"
        if geometry_type != expected:
            raise not_found(f"{entity_type} 几何类型必须是 {expected}")
        feature["geometry"] = body.geometry
    feature["properties"] = {**feature["properties"], **body.properties, "id": entity_id}
    _write_geojson(ctx, filename, features)
    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "geometry": feature.get("geometry") or {},
        "properties": feature.get("properties") or {},
    }


@router.get("/buildings", summary="建筑轮廓 GeoJSON（OpenStreetMap，含沉降风险等级）")
def buildings(ctx: AppContext = Depends(get_ctx)) -> Response:
    return Response(content=ctx.buildings_json(), media_type="application/json")


@router.get("/buildings/fine", summary="武汉精细建筑轮廓 GeoJSON（本地派生数据）")
def fine_buildings(district: str | None = Query(None), ctx: AppContext = Depends(get_ctx)) -> Response:
    try:
        payload = ctx.fine_buildings_json(district)
    except FileNotFoundError as exc:
        raise not_found("精细建筑图层不存在，请运行 data/scripts/build_wuhan_buildings.py") from exc
    return Response(content=payload, media_type="application/json")


@router.get("/buildings/fine/districts", summary="可加载的精细建筑行政区分区")
def fine_building_districts(ctx: AppContext = Depends(get_ctx)) -> dict:
    return ctx.fine_building_manifest()


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
