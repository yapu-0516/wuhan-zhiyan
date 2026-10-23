"""系统 / 数据源接口（docs/api.md §1 §7）。"""
from __future__ import annotations

import time

import cityeye_algo as ca
from fastapi import APIRouter, Depends

from .. import timeutil
from ..config import APP_NAME, APP_VERSION
from ..context import AppContext, get_ctx
from ..geo import ODBL
from ..schemas import HealthOut, SourceOut, SystemInfoOut

router = APIRouter(tags=["系统"])


@router.get("/health", response_model=HealthOut, summary="健康检查")
def health() -> dict:
    return {"status": "ok", "time": timeutil.fmt(timeutil.now())}


@router.get("/system/info", response_model=SystemInfoOut, summary="系统信息（区域、算法、模拟器）")
def system_info(ctx: AppContext = Depends(get_ctx)) -> dict:
    s, region = ctx.settings, ctx.geo.region
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "demo_mode": s.demo_mode,
        "simulator": {"enabled": s.simulator, "interval_sec": s.sim_interval},
        "database": s.database_kind,
        "uptime_sec": int(time.time() - ctx.started_at),
        "region": {"name": region["name"], "city": region["city"], "center": region["center"], "bbox": region["bbox"]},
        "algorithms": ca.algorithms(),
        "data_attribution": ODBL,
    }


@router.get("/sources", response_model=list[SourceOut], summary="监测数据源")
def sources(ctx: AppContext = Depends(get_ctx)) -> list[dict]:
    with ctx.session() as s:
        return ctx.sources.list(s)
