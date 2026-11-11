"""城市智能情景推演 API。"""

from __future__ import annotations

import sys
import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from .. import timeutil
from ..context import AppContext, get_ctx
from ..models import ScenarioTemplate, ScenarioTemplateRevision
from ..schemas import (
    ScenarioResourceSelection,
    ScenarioTemplateCreate,
    ScenarioTemplateOut,
    ScenarioTemplatePatch,
    ScenarioTemplateRevisionOut,
)
from ..services.scenario import ScenarioService
from ..services.events import next_id

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from llm_module.client import LLMError, Settings  # noqa: E402
from llm_module.scenario_agent import ScenarioAgentError  # noqa: E402
from scenario_engine.models import ScenarioParameters  # noqa: E402

router = APIRouter(prefix="/scenario", tags=["情景推演"])


class ScenarioMessageIn(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    auto_run: bool = False


class ScenarioSessionCreate(BaseModel):
    event_id: str | None = None
    template_id: str | None = None


class ScenarioCompareIn(BaseModel):
    left_run_id: str = Field(min_length=1)
    right_run_id: str = Field(min_length=1)


def _service(ctx: AppContext) -> ScenarioService:
    return ScenarioService(ctx)


@router.get("/status", summary="情景 Agent 可用性")
def scenario_status() -> dict:
    try:
        Settings.from_env()
    except LLMError as exc:
        return {"available": False, "reason": str(exc), "provider": "mock"}
    return {"available": True, "model": "deepseek-chat", "provider": "mock"}


@router.post("/sessions", summary="创建情景会话")
def create_session(
    body: ScenarioSessionCreate | None = None,
    ctx: AppContext = Depends(get_ctx),
) -> dict:
    return _service(ctx).create_session(
        body.event_id if body else None,
        body.template_id if body else None,
    )


def template_to_dict(row: ScenarioTemplate) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "description": row.description,
        "scenario_type": row.scenario_type,
        "parameters": row.parameters or {},
        "created_at": timeutil.fmt(row.created_at),
        "updated_at": timeutil.fmt(row.updated_at),
    }


@router.get("/templates", response_model=list[ScenarioTemplateOut], summary="情景模板")
def list_templates(ctx: AppContext = Depends(get_ctx)) -> list[dict]:
    with ctx.session() as s:
        rows = s.scalars(
            select(ScenarioTemplate).order_by(ScenarioTemplate.scenario_type, ScenarioTemplate.name)
        ).all()
        return [template_to_dict(row) for row in rows]


@router.post("/templates", response_model=ScenarioTemplateOut, status_code=201, summary="保存情景模板")
def create_template(body: ScenarioTemplateCreate, ctx: AppContext = Depends(get_ctx)) -> dict:
    parameters = ScenarioParameters.model_validate(body.parameters).model_dump(mode="json")
    now = timeutil.now()
    with ctx.session() as s:
        with ctx.id_lock:
            row = ScenarioTemplate(
                id=next_id(s, ScenarioTemplate.id, "ST"),
                name=body.name.strip(),
                description=body.description.strip(),
                scenario_type=body.scenario_type,
                parameters=parameters,
                created_at=now,
                updated_at=now,
            )
            s.add(row)
            s.flush()
            s.add(
                ScenarioTemplateRevision(
                    template_id=row.id,
                    version_no=1,
                    name=row.name,
                    description=row.description,
                    scenario_type=row.scenario_type,
                    parameters=row.parameters,
                    operator="情景模板编辑员",
                    created_at=now,
                )
            )
            s.commit()
        return template_to_dict(row)


def template_revision_to_dict(row: ScenarioTemplateRevision) -> dict:
    return {
        "id": row.id,
        "template_id": row.template_id,
        "version_no": row.version_no,
        "name": row.name,
        "description": row.description,
        "scenario_type": row.scenario_type,
        "parameters": row.parameters or {},
        "operator": row.operator,
        "created_at": timeutil.fmt(row.created_at),
    }


@router.get(
    "/templates/{template_id}/revisions",
    response_model=list[ScenarioTemplateRevisionOut],
    summary="情景模板修订历史",
)
def list_template_revisions(
    template_id: str, ctx: AppContext = Depends(get_ctx)
) -> list[dict]:
    with ctx.session() as s:
        if s.get(ScenarioTemplate, template_id) is None:
            raise HTTPException(status_code=404, detail=f"情景模板 {template_id} 不存在")
        rows = s.scalars(
            select(ScenarioTemplateRevision)
            .where(ScenarioTemplateRevision.template_id == template_id)
            .order_by(ScenarioTemplateRevision.version_no.desc())
        ).all()
        return [template_revision_to_dict(row) for row in rows]


@router.patch(
    "/templates/{template_id}",
    response_model=ScenarioTemplateOut,
    summary="编辑情景模板并记录修订",
)
def patch_template(
    template_id: str,
    body: ScenarioTemplatePatch,
    ctx: AppContext = Depends(get_ctx),
) -> dict:
    updates = body.model_dump(exclude_unset=True, exclude={"operator"})
    if "parameters" in updates:
        updates["parameters"] = ScenarioParameters.model_validate(
            updates["parameters"]
        ).model_dump(mode="json")
    now = timeutil.now()
    with ctx.session() as s:
        row = s.get(ScenarioTemplate, template_id)
        if row is None:
            raise HTTPException(status_code=404, detail=f"情景模板 {template_id} 不存在")
        for field, value in updates.items():
            setattr(row, field, value.strip() if isinstance(value, str) else value)
        row.updated_at = now
        version_no = (s.scalar(
            select(func.count()).select_from(ScenarioTemplateRevision).where(
                ScenarioTemplateRevision.template_id == row.id
            )
        ) or 0) + 1
        s.add(
            ScenarioTemplateRevision(
                template_id=row.id,
                version_no=version_no,
                name=row.name,
                description=row.description,
                scenario_type=row.scenario_type,
                parameters=row.parameters or {},
                operator=body.operator,
                created_at=now,
            )
        )
        s.commit()
        return template_to_dict(row)


@router.delete("/templates/{template_id}", summary="删除情景模板")
def delete_template(template_id: str, ctx: AppContext = Depends(get_ctx)) -> dict:
    with ctx.session() as s:
        row = s.get(ScenarioTemplate, template_id)
        if row is None:
            raise HTTPException(status_code=404, detail=f"情景模板 {template_id} 不存在")
        s.delete(row)
        s.commit()
        return {"ok": True}


@router.get("/sessions/{session_id}", summary="获取情景会话")
def get_session(session_id: str, ctx: AppContext = Depends(get_ctx)) -> dict:
    return _service(ctx).get_session(session_id)


@router.put("/sessions/{session_id}/resources", summary="设置并预留情景资源")
def set_resources(
    session_id: str,
    body: ScenarioResourceSelection,
    ctx: AppContext = Depends(get_ctx),
) -> dict:
    try:
        return _service(ctx).set_resources(session_id, body.resource_ids)
    except ScenarioAgentError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/sessions/{session_id}/messages", summary="发送自然语言情景指令")
def post_message(session_id: str, body: ScenarioMessageIn, ctx: AppContext = Depends(get_ctx)) -> dict:
    try:
        return _service(ctx).message(session_id, body.message, auto_run=body.auto_run)
    except LLMError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/sessions/{session_id}/runs", summary="运行当前情景版本")
def run_current(session_id: str, ctx: AppContext = Depends(get_ctx)) -> dict:
    try:
        return _service(ctx).run_current(session_id)
    except LLMError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/sessions/{session_id}/runs/variants", summary="重跑并返回三套可能结果")
def run_current_variants(session_id: str, ctx: AppContext = Depends(get_ctx)) -> dict:
    try:
        return _service(ctx).run_current_variants(session_id)
    except LLMError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/runs/{run_id}", summary="获取推演时间帧")
def get_run(run_id: str, ctx: AppContext = Depends(get_ctx)) -> dict:
    return _service(ctx).get_run(run_id)


@router.post("/sessions/{session_id}/compare", summary="比较两次推演")
def compare_runs(session_id: str, body: ScenarioCompareIn, ctx: AppContext = Depends(get_ctx)) -> dict:
    try:
        return _service(ctx).compare(session_id, body.left_run_id, body.right_run_id)
    except LLMError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/runs/{run_id}/report", summary="生成结构化推演报告")
def report(run_id: str, ctx: AppContext = Depends(get_ctx)) -> dict:
    try:
        return _service(ctx).report(run_id)
    except LLMError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/runs/{run_id}/export", summary="导出推演结果 JSON")
def export_run(run_id: str, ctx: AppContext = Depends(get_ctx)) -> Response:
    payload = _service(ctx).get_run(run_id)
    return Response(
        content=json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{run_id}.json"'},
    )
