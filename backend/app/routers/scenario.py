"""城市智能情景推演 API。"""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..context import AppContext, get_ctx
from ..services.scenario import ScenarioService

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from llm_module.client import LLMError, Settings  # noqa: E402

router = APIRouter(prefix="/scenario", tags=["情景推演"])


class ScenarioMessageIn(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    auto_run: bool = False


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
def create_session(ctx: AppContext = Depends(get_ctx)) -> dict:
    return _service(ctx).create_session()


@router.get("/sessions/{session_id}", summary="获取情景会话")
def get_session(session_id: str, ctx: AppContext = Depends(get_ctx)) -> dict:
    return _service(ctx).get_session(session_id)


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
