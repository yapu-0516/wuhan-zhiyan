"""统一业务关系图与完整链路导出。"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from ..context import AppContext, get_ctx
from ..services.traceability import build_traceability_graph

router = APIRouter(prefix="/traceability", tags=["业务链路"])


@router.get("/graph", summary="统一业务关系图")
def graph(
    entity_type: str | None = None,
    entity_id: str | None = None,
    limit: int = Query(default=240, ge=20, le=5000),
    ctx: AppContext = Depends(get_ctx),
) -> dict:
    return build_traceability_graph(
        ctx,
        entity_type=entity_type,
        entity_id=entity_id,
        limit=limit,
    )


@router.get("/export", summary="导出完整业务链路 JSON")
def export_graph(ctx: AppContext = Depends(get_ctx)) -> Response:
    payload = build_traceability_graph(ctx, limit=5000)
    return Response(
        content=json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="cityeye-traceability.json"'},
    )
