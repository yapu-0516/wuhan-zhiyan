"""AI 分析任务与示例数据接口（docs/api.md §6）。"""
from __future__ import annotations

import cityeye_algo as ca
from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import select

from ..context import AppContext, bad_request, get_ctx, not_found
from ..models import Task
from ..schemas import AnalysisTaskOut, SampleOut, TaskCreate
from ..services.tasks import create_task, submit, task_to_dict
from ..services.uploads import remove, save_uploads

router = APIRouter(tags=["AI 分析"])


def _check_type(event_type: str) -> None:
    if event_type not in ca.EVENT_TYPES:
        raise bad_request(f"不支持的分析类型：{event_type}（可选 fire / traffic / building / flood）")


def _parse_float(name: str, raw: str | None, lo: float, hi: float) -> float | None:
    if raw is None or str(raw).strip() == "":
        return None
    try:
        v = float(raw)
    except ValueError as e:
        raise bad_request(f"{name} 必须是数字") from e
    if not lo <= v <= hi:
        raise bad_request(f"{name} 超出取值范围 [{lo}, {hi}]")
    return v


@router.get("/tasks", response_model=list[AnalysisTaskOut], summary="任务列表（按创建时间倒序）")
def list_tasks(ctx: AppContext = Depends(get_ctx)) -> list[dict]:
    with ctx.session() as s:
        return [task_to_dict(t) for t in s.scalars(select(Task).order_by(Task.created_at.desc(), Task.id.desc()))]


@router.get("/tasks/{task_id}", response_model=AnalysisTaskOut, summary="任务详情")
def get_task(task_id: str, ctx: AppContext = Depends(get_ctx)) -> dict:
    with ctx.session() as s:
        t = s.get(Task, task_id)
        if t is None:
            raise not_found(f"任务 {task_id} 不存在")
        return task_to_dict(t)


@router.post("/tasks", response_model=AnalysisTaskOut, summary="在示例数据上创建分析任务（异步执行）")
def post_task(body: TaskCreate, ctx: AppContext = Depends(get_ctx)) -> dict:
    _check_type(body.type)
    if not body.sample_id:
        raise bad_request("未指定示例数据 sample_id，也没有上传文件；上传文件请使用 POST /api/tasks/upload")
    smp = ctx.samples.by_id.get(body.sample_id)
    if smp is None:
        raise not_found(f"示例数据 {body.sample_id} 不存在")
    if smp["type"] != body.type:
        raise bad_request(f"示例数据 {body.sample_id} 属于 {smp['type']} 类型，与任务类型 {body.type} 不一致")
    paths = ctx.samples.paths(smp)
    lon = body.longitude if body.longitude is not None else smp.get("longitude")
    lat = body.latitude if body.latitude is not None else smp.get("latitude")
    with ctx.session() as s:
        try:
            t = create_task(
                ctx, s, event_type=body.type, paths=paths, inputs=[{"name": p.name, "url": ctx.url_for(p)} for p in paths],
                longitude=lon, latitude=lat, create_event=body.create_event, sample_id=smp["id"], origin="user",
            )
        except ca.InputError as e:
            raise bad_request(str(e)) from e
        submit(ctx, t, paths)
        return task_to_dict(t)


@router.post("/tasks/upload", response_model=AnalysisTaskOut, summary="上传文件创建分析任务（异步执行）")
def upload_task(
    type: str = Form(..., description="fire / traffic / building / flood"),
    files: list[UploadFile] = File(..., description="1~N 个文件"),
    longitude: str | None = Form(default=None),
    latitude: str | None = Form(default=None),
    create_event: str = Form(default="true"),
    ctx: AppContext = Depends(get_ctx),
) -> dict:
    _check_type(type)
    lon = _parse_float("longitude", longitude, -180, 180)
    lat = _parse_float("latitude", latitude, -90, 90)
    if (lon is None) != (lat is None):
        raise bad_request("longitude 与 latitude 需同时提供")
    try:  # 先按文件名做类型 / 数量校验，避免无效文件落盘
        ca.select(type, [f.filename or "" for f in files])
    except ca.InputError as e:
        raise bad_request(str(e)) from e
    saved = save_uploads(files, ctx.uploads_dir / "tasks", int(ctx.settings.max_upload_mb * (1 << 20)))
    paths = [p for _, p, _ in saved]
    with ctx.session() as s:
        try:
            t = create_task(
                ctx, s, event_type=type, paths=paths, inputs=[{"name": n, "url": ctx.url_for(p)} for n, p, _ in saved],
                longitude=lon, latitude=lat, create_event=create_event.strip().lower() not in ("false", "0", "no", "off"),
                sample_id=None, origin="upload",
            )
        except ca.InputError as e:
            remove(paths)
            raise bad_request(str(e)) from e
        submit(ctx, t, paths)
        return task_to_dict(t)


@router.get("/samples", response_model=list[SampleOut], summary="示例数据（合成演示数据）")
def samples(type: str | None = None, ctx: AppContext = Depends(get_ctx)) -> list[dict]:
    return ctx.samples.list(type)
