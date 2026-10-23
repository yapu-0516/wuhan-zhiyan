"""演示控制接口（docs/api.md §8，仅 demo_mode=true 时可用）。"""
from __future__ import annotations

import random
import threading

from fastapi import APIRouter, Depends, HTTPException

from .. import seed
from ..context import AppContext, get_ctx
from ..schemas import OkOut, ScenarioOut, ScenarioRequest
from ..services.simulator import random_site
from ..services.tasks import create_task, run_task

router = APIRouter(prefix="/demo", tags=["演示控制"])
_reset_lock = threading.Lock()
_rng = random.Random()


def _require_demo(ctx: AppContext) -> None:
    if not ctx.settings.demo_mode:
        raise HTTPException(status_code=403, detail="当前未开启演示模式（CITYEYE_DEMO_MODE=false）")


@router.post("/scenario", response_model=ScenarioOut, summary="立即在示例数据上运行一次算法流水线")
def scenario(body: ScenarioRequest, ctx: AppContext = Depends(get_ctx)) -> dict:
    _require_demo(ctx)
    kind = body.scenario if body.scenario != "random" else _rng.choice(("fire", "traffic", "building", "flood"))
    pool = [smp for smp in ctx.samples.items if smp["type"] == kind and smp.get("showcase")] or [
        smp for smp in ctx.samples.items if smp["type"] == kind
    ]
    if not pool:
        raise HTTPException(status_code=404, detail=f"没有 {kind} 类型的示例数据，请先运行 data/scripts/generate_samples.py")
    smp = _rng.choice(pool)
    paths = ctx.samples.paths(smp)
    lon, lat = random_site(ctx.geo, _rng, kind)
    with ctx.session() as s:
        t = create_task(
            ctx, s, event_type=kind, paths=paths, inputs=[{"name": p.name, "url": ctx.url_for(p)} for p in paths],
            longitude=lon, latitude=lat, create_event=True, sample_id=smp["id"], origin="demo",
        )
    done = run_task(ctx, t.id, paths, pace=0)
    event_ids = (done.result or {}).get("event_ids", []) if done else []
    return {"task_id": t.id, "event_id": event_ids[0] if event_ids else None}


@router.post("/reset", response_model=OkOut, summary="重置数据库为初始种子数据")
def reset(ctx: AppContext = Depends(get_ctx)) -> dict:
    _require_demo(ctx)
    if not _reset_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="正在重置中，请稍后")
    try:
        seed.seed_database(ctx)
    finally:
        _reset_lock.release()
    return {"ok": True}
