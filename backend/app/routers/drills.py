"""应急演练运行、回放记录与复盘入口。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ..context import AppContext, get_ctx, not_found
from ..models import ScenarioRunRecord
from ..schemas import DrillRunCreate, DrillRunOut, DrillRunPatch, ReviewOut
from ..services.drills import create_drill_review, create_drill_run, drill_to_dict, update_drill_run
from ..services.workflow import review_to_dict
from sqlalchemy import select

router = APIRouter(prefix="/drills", tags=["应急演练"])


@router.get("/runs", response_model=list[DrillRunOut], summary="演练运行记录")
def list_drill_runs(
    limit: int = Query(default=50, ge=1, le=200),
    ctx: AppContext = Depends(get_ctx),
) -> list[dict]:
    with ctx.session() as s:
        rows = s.scalars(
            select(ScenarioRunRecord)
            .where(ScenarioRunRecord.provider == "local-crowd-simulator")
            .order_by(ScenarioRunRecord.created_at.desc())
            .limit(limit)
        ).all()
        return [drill_to_dict(row) for row in rows]


@router.get("/runs/{run_id}", response_model=DrillRunOut, summary="演练运行详情与回放帧")
def get_drill_run(run_id: str, ctx: AppContext = Depends(get_ctx)) -> dict:
    with ctx.session() as s:
        row = s.get(ScenarioRunRecord, run_id)
        if row is None or row.payload.get("run_kind") != "drill":
            raise not_found(f"演练运行 {run_id} 不存在")
        return drill_to_dict(row)


@router.post("/runs", response_model=DrillRunOut, status_code=201, summary="创建演练运行")
def post_drill_run(body: DrillRunCreate, ctx: AppContext = Depends(get_ctx)) -> dict:
    with ctx.session() as s:
        return drill_to_dict(create_drill_run(ctx, s, body))


@router.patch("/runs/{run_id}", response_model=DrillRunOut, summary="更新演练过程与回放帧")
def patch_drill_run(
    run_id: str,
    body: DrillRunPatch,
    ctx: AppContext = Depends(get_ctx),
) -> dict:
    with ctx.session() as s:
        row = s.get(ScenarioRunRecord, run_id)
        if row is None or row.payload.get("run_kind") != "drill":
            raise not_found(f"演练运行 {run_id} 不存在")
        return drill_to_dict(update_drill_run(s, row, body))


@router.post("/runs/{run_id}/review", response_model=ReviewOut, summary="生成或获取演练复盘草稿")
def post_drill_review(run_id: str, ctx: AppContext = Depends(get_ctx)) -> dict:
    with ctx.session() as s:
        row = s.get(ScenarioRunRecord, run_id)
        if row is None or row.payload.get("run_kind") != "drill":
            raise not_found(f"演练运行 {run_id} 不存在")
        return review_to_dict(create_drill_review(ctx, s, row))
