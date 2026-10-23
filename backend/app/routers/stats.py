"""统计接口（docs/api.md §4）。"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ..context import AppContext, get_ctx
from ..schemas import OverviewOut
from ..services.stats import overview

router = APIRouter(prefix="/stats", tags=["统计"])


@router.get("/overview", response_model=OverviewOut, summary="城市运行总览")
def stats_overview(ctx: AppContext = Depends(get_ctx)) -> dict:
    with ctx.session() as s:
        return overview(ctx, s)
