"""业务闭环接口：监测任务、运行记录、研判、工单与复盘。"""
from __future__ import annotations

import math
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy import func, select

from .. import timeutil
from ..context import AppContext, bad_request, get_ctx, not_found
from ..models import (
    AssessmentRecord,
    EmergencyResource,
    Event,
    EventLog,
    MonitoringRun,
    MonitoringTask,
    MonitoringTaskTemplate,
    ReviewRecord,
    ScenarioRunRecord,
    Task,
    TaskTemplateRevision,
    WorkOrder,
)
from ..schemas import (
    AssessmentCreate,
    AssessmentContextOut,
    AssessmentOut,
    CandidateMergeCreate,
    CandidateMergeOut,
    MonitoringExecuteOut,
    MonitoringRunCreate,
    MonitoringRunOut,
    MonitoringTaskCreate,
    MonitoringTaskExecute,
    MonitoringTaskOut,
    MonitoringTaskPatch,
    MonitoringTaskStatus,
    MonitoringTaskTemplateCreate,
    MonitoringTaskTemplateOut,
    MonitoringTaskTemplatePatch,
    ReviewCreate,
    ReviewDraftOut,
    ReviewOut,
    ReviewUpdate,
    ScenarioDispatchIn,
    TaskTemplateApply,
    TaskTemplateRevisionOut,
    WorkOrderCreate,
    WorkOrderFeedbackAssessmentCreate,
    WorkOrderOut,
    WorkOrderPatch,
    WorkOrderResourceUseCreate,
)
from ..services.workflow import (
    add_work_order_feedback,
    assessment_to_dict,
    create_assessment,
    create_monitoring_run,
    create_monitoring_task,
    create_review,
    create_task_template,
    create_work_order,
    dispatch_scenario_actions,
    execute_monitoring_task,
    order_to_dict,
    review_to_dict,
    run_to_dict,
    task_to_dict,
    task_template_to_dict,
    update_monitoring_task,
    update_work_order,
    work_order_sla,
)
from ..services.tasks import task_to_dict as analysis_task_to_dict
from ..services.events import add_log, event_to_dict, transition
from ..services.uploads import (
    ATTACHMENT_SUFFIXES,
    attachment_metadata,
    remove,
    save_uploads,
)

router = APIRouter(tags=["业务闭环"])

MAX_WORK_ORDER_ATTACHMENTS = 10
MAX_WORK_ORDER_TOTAL_BYTES = 500 * (1 << 20)


def _optional_coordinate(raw: str | None, name: str, low: float, high: float) -> float | None:
    if raw is None or not str(raw).strip():
        return None
    try:
        value = float(raw)
    except ValueError as exc:
        raise bad_request(f"{name} 必须是数字") from exc
    if not low <= value <= high:
        raise bad_request(f"{name} 超出取值范围")
    return value


@router.get(
    "/task-templates",
    response_model=list[MonitoringTaskTemplateOut],
    summary="监测任务模板",
)
def list_task_templates(ctx: AppContext = Depends(get_ctx)) -> list[dict]:
    with ctx.session() as s:
        rows = s.scalars(
            select(MonitoringTaskTemplate).order_by(
                MonitoringTaskTemplate.event_type,
                MonitoringTaskTemplate.name,
            )
        ).all()
        return [task_template_to_dict(row) for row in rows]


@router.post(
    "/task-templates",
    response_model=MonitoringTaskTemplateOut,
    status_code=201,
    summary="保存监测任务模板",
)
def post_task_template(
    body: MonitoringTaskTemplateCreate, ctx: AppContext = Depends(get_ctx)
) -> dict:
    with ctx.session() as s:
        return task_template_to_dict(create_task_template(ctx, s, body))


def revision_to_dict(row: TaskTemplateRevision) -> dict:
    return {
        "id": row.id,
        "template_id": row.template_id,
        "version_no": row.version_no,
        "rule_config": row.rule_config or {},
        "source_review_id": row.source_review_id,
        "operator": row.operator,
        "created_at": timeutil.fmt(row.created_at),
    }


@router.get(
    "/task-templates/{template_id}/revisions",
    response_model=list[TaskTemplateRevisionOut],
    summary="任务模板修订历史",
)
def task_template_revisions(
    template_id: str, ctx: AppContext = Depends(get_ctx)
) -> list[dict]:
    with ctx.session() as s:
        if s.get(MonitoringTaskTemplate, template_id) is None:
            raise not_found(f"监测任务模板 {template_id} 不存在")
        rows = s.scalars(
            select(TaskTemplateRevision)
            .where(TaskTemplateRevision.template_id == template_id)
            .order_by(TaskTemplateRevision.version_no.desc())
        ).all()
        return [revision_to_dict(row) for row in rows]


@router.patch(
    "/task-templates/{template_id}",
    response_model=MonitoringTaskTemplateOut,
    summary="编辑监测任务模板并保留规则修订",
)
def patch_task_template(
    template_id: str,
    body: MonitoringTaskTemplatePatch,
    ctx: AppContext = Depends(get_ctx),
) -> dict:
    with ctx.session() as s:
        row = s.get(MonitoringTaskTemplate, template_id)
        if row is None:
            raise not_found(f"监测任务模板 {template_id} 不存在")
        updates = body.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(row, field, value)
        now = timeutil.now()
        row.updated_at = now
        if body.rule_config is not None:
            version_no = (s.scalar(
                select(func.count()).select_from(TaskTemplateRevision).where(
                    TaskTemplateRevision.template_id == row.id
                )
            ) or 0) + 1
            s.add(
                TaskTemplateRevision(
                    template_id=row.id,
                    version_no=version_no,
                    rule_config=body.rule_config,
                    source_review_id=None,
                    operator="模板编辑员",
                    created_at=now,
                )
            )
        s.commit()
        return task_template_to_dict(row)


@router.delete("/task-templates/{template_id}", summary="删除监测任务模板")
def delete_task_template(template_id: str, ctx: AppContext = Depends(get_ctx)) -> dict:
    with ctx.session() as s:
        row = s.get(MonitoringTaskTemplate, template_id)
        if row is None:
            raise not_found(f"监测任务模板 {template_id} 不存在")
        s.delete(row)
        s.commit()
        return {"ok": True}


@router.get("/monitoring-tasks", response_model=list[MonitoringTaskOut])
def list_monitoring_tasks(
    status: MonitoringTaskStatus | None = None,
    ctx: AppContext = Depends(get_ctx),
) -> list[dict]:
    stmt = select(MonitoringTask)
    if status:
        stmt = stmt.where(MonitoringTask.status == status)
    with ctx.session() as s:
        rows = s.scalars(stmt.order_by(MonitoringTask.created_at.desc(), MonitoringTask.id.desc()))
        return [task_to_dict(row) for row in rows]


@router.get("/monitoring-tasks/{task_id}", response_model=MonitoringTaskOut)
def get_monitoring_task(task_id: str, ctx: AppContext = Depends(get_ctx)) -> dict:
    with ctx.session() as s:
        row = s.get(MonitoringTask, task_id)
        if row is None:
            raise not_found(f"监测任务 {task_id} 不存在")
        return task_to_dict(row)


@router.post("/monitoring-tasks", response_model=MonitoringTaskOut, status_code=201)
def post_monitoring_task(body: MonitoringTaskCreate, ctx: AppContext = Depends(get_ctx)) -> dict:
    with ctx.session() as s:
        return task_to_dict(create_monitoring_task(ctx, s, body))


@router.patch("/monitoring-tasks/{task_id}", response_model=MonitoringTaskOut)
def patch_monitoring_task(
    task_id: str, body: MonitoringTaskPatch, ctx: AppContext = Depends(get_ctx)
) -> dict:
    with ctx.session() as s:
        row = s.get(MonitoringTask, task_id)
        if row is None:
            raise not_found(f"监测任务 {task_id} 不存在")
        return task_to_dict(update_monitoring_task(s, row, body))


@router.post("/monitoring-tasks/{task_id}/execute", response_model=MonitoringExecuteOut)
def run_monitoring_task(
    task_id: str, body: MonitoringTaskExecute, ctx: AppContext = Depends(get_ctx)
) -> dict:
    with ctx.session() as s:
        task = s.get(MonitoringTask, task_id)
        if task is None:
            raise not_found(f"监测任务 {task_id} 不存在")
        run, analysis = execute_monitoring_task(ctx, s, task, body)
        return {"monitoring_run": run_to_dict(run), "analysis_task": analysis_task_to_dict(analysis)}


@router.get("/monitoring-runs", response_model=list[MonitoringRunOut])
def list_monitoring_runs(
    task_id: str | None = None,
    ctx: AppContext = Depends(get_ctx),
) -> list[dict]:
    stmt = select(MonitoringRun)
    if task_id:
        stmt = stmt.where(MonitoringRun.monitoring_task_id == task_id)
    with ctx.session() as s:
        rows = s.scalars(stmt.order_by(MonitoringRun.created_at.desc(), MonitoringRun.id.desc()))
        return [run_to_dict(row) for row in rows]


@router.post("/monitoring-runs", response_model=MonitoringRunOut, status_code=201)
def post_monitoring_run(body: MonitoringRunCreate, ctx: AppContext = Depends(get_ctx)) -> dict:
    with ctx.session() as s:
        return run_to_dict(create_monitoring_run(ctx, s, body))


@router.get("/assessments", response_model=list[AssessmentOut])
def list_assessments(
    event_id: str | None = None,
    limit: int = Query(default=200, ge=1, le=2000),
    ctx: AppContext = Depends(get_ctx),
) -> list[dict]:
    stmt = select(AssessmentRecord)
    if event_id:
        stmt = stmt.where(AssessmentRecord.event_id == event_id)
    with ctx.session() as s:
        rows = s.scalars(stmt.order_by(AssessmentRecord.created_at.desc(), AssessmentRecord.id.desc()).limit(limit))
        return [assessment_to_dict(row) for row in rows]


@router.get(
    "/assessments/context",
    response_model=AssessmentContextOut,
    summary="事件周边建筑、道路与设施查询",
)
def assessment_context(
    event_id: str,
    radius_m: float = Query(default=300, ge=50, le=3000),
    ctx: AppContext = Depends(get_ctx),
) -> dict:
    with ctx.session() as s:
        event = s.get(Event, event_id)
        if event is None:
            raise not_found(f"事件 {event_id} 不存在")
    buildings = [
        {
            "id": building["id"],
            "name": ctx.geo.building_label(building),
            "category": building.get("category", "other"),
            "distance_m": round(distance, 1),
            "risk_level": ctx.geo.monitoring.get(building["id"], "normal"),
        }
        for building, distance in ctx.geo.nearby_buildings(
            event.longitude, event.latitude, radius_m, limit=12
        )
    ]
    roads = [
        {
            "id": road.id,
            "name": road.base_name,
            "highway": road.highway,
            "distance_m": round(distance, 1),
        }
        for road, distance in ctx.geo.nearest_roads(
            event.longitude, event.latitude, within_m=radius_m, k=8
        )
    ]
    pois = [
        {
            "id": poi["id"],
            "name": poi.get("name") or poi["id"],
            "kind": poi.get("kind", "other"),
            "distance_m": round(distance, 1),
        }
        for poi, distance in ctx.geo.nearby_pois(
            event.longitude, event.latitude, within_m=max(500, radius_m), limit=12
        )
    ]
    return {
        "event_id": event.id,
        "longitude": event.longitude,
        "latitude": event.latitude,
        "district": event.district,
        "grid": event.grid,
        "radius_m": radius_m,
        "buildings": buildings,
        "roads": roads,
        "pois": pois,
    }


@router.post(
    "/assessments/candidates/merge",
    response_model=CandidateMergeOut,
    summary="合并相近告警",
)
def merge_candidates(
    body: CandidateMergeCreate,
    ctx: AppContext = Depends(get_ctx),
) -> dict:
    if body.primary_event_id == body.related_event_id:
        raise bad_request("主事件与被合并事件不能相同")
    now = timeutil.now()
    with ctx.session() as s:
        primary = s.get(Event, body.primary_event_id)
        related = s.get(Event, body.related_event_id)
        if primary is None or related is None:
            raise not_found("主事件或被合并事件不存在")
        if primary.event_type != related.event_type:
            raise bad_request("只有同类型事件可以合并")
        if related.status == "resolved":
            raise bad_request("被合并事件已经办结")
        distance = math.hypot(
            (primary.longitude - related.longitude) * 111320 * math.cos(math.radians(primary.latitude)),
            (primary.latitude - related.latitude) * 110540,
        )
        if distance > 1000:
            raise bad_request("事件距离超过 1 km，不能作为相近告警合并")
        if abs(primary.timestamp - related.timestamp).total_seconds() > 2 * 60 * 60:
            raise bad_request("事件时间间隔超过 2 小时，不能作为相近告警合并")
        related_metrics = dict(related.metrics or {})
        related_metrics["merged_into"] = primary.id
        related.metrics = related_metrics
        primary_metrics = dict(primary.metrics or {})
        primary_metrics["merged_event_ids"] = list(
            dict.fromkeys([*(primary_metrics.get("merged_event_ids") or []), related.id])
        )
        primary.metrics = primary_metrics
        related.updated_at = now
        primary.updated_at = now
        add_log(
            s,
            primary.id,
            "comment",
            body.operator.strip() or "值班员",
            f"合并相近告警 {related.id}（{distance:.0f} m）"
            + (f"：{body.note.strip()}" if body.note.strip() else ""),
            now,
        )
        transition(
            s,
            related,
            "resolved",
            body.operator.strip() or "值班员",
            f"相近告警合并至 {primary.id}"
            + (f"：{body.note.strip()}" if body.note.strip() else ""),
            now,
        )
        s.commit()
        return {
            "primary": event_to_dict(primary),
            "merged": event_to_dict(related),
        }


@router.post("/assessments", response_model=AssessmentOut, status_code=201)
def post_assessment(body: AssessmentCreate, ctx: AppContext = Depends(get_ctx)) -> dict:
    with ctx.session() as s:
        return assessment_to_dict(create_assessment(ctx, s, body))


@router.get("/work-orders", response_model=list[WorkOrderOut])
def list_work_orders(
    event_id: str | None = None,
    status: str | None = None,
    limit: int = Query(default=500, ge=1, le=2000),
    ctx: AppContext = Depends(get_ctx),
) -> list[dict]:
    stmt = select(WorkOrder)
    if event_id:
        stmt = stmt.where(WorkOrder.event_id == event_id)
    if status:
        stmt = stmt.where(WorkOrder.status == status)
    with ctx.session() as s:
        rows = s.scalars(stmt.order_by(WorkOrder.created_at.desc(), WorkOrder.id.desc()).limit(limit))
        return [order_to_dict(row) for row in rows]


@router.get("/work-orders/{order_id}", response_model=WorkOrderOut)
def get_work_order(order_id: str, ctx: AppContext = Depends(get_ctx)) -> dict:
    with ctx.session() as s:
        row = s.get(WorkOrder, order_id)
        if row is None:
            raise not_found(f"工单 {order_id} 不存在")
        return order_to_dict(row)


@router.post("/work-orders", response_model=WorkOrderOut, status_code=201)
def post_work_order(body: WorkOrderCreate, ctx: AppContext = Depends(get_ctx)) -> dict:
    with ctx.session() as s:
        return order_to_dict(create_work_order(ctx, s, body))


@router.post(
    "/work-orders/{order_id}/feedback",
    response_model=WorkOrderOut,
    summary="提交现场文字、定位、图片、视频、音频和文件",
)
def post_work_order_feedback(
    order_id: str,
    note: str = Form(default=""),
    longitude: str | None = Form(default=None),
    latitude: str | None = Form(default=None),
    operator: str = Form(default="现场处置人员"),
    files: list[UploadFile] | None = File(default=None),
    ctx: AppContext = Depends(get_ctx),
) -> dict:
    uploads = files or []
    if len(uploads) > MAX_WORK_ORDER_ATTACHMENTS:
        raise bad_request(f"单次最多提交 {MAX_WORK_ORDER_ATTACHMENTS} 个现场附件")
    invalid = [
        f.filename or "未命名文件"
        for f in uploads
        if Path(f.filename or "").suffix.lower() not in ATTACHMENT_SUFFIXES
    ]
    if invalid:
        raise bad_request(
            "现场附件包含不支持的文件类型："
            f"{', '.join(invalid)}；支持图片、视频、音频、PDF、Office、文本和常见压缩包"
        )
    lon = _optional_coordinate(longitude, "经度", -180, 180)
    lat = _optional_coordinate(latitude, "纬度", -90, 90)
    if (lon is None) != (lat is None):
        raise bad_request("经度与纬度需同时提供")
    with ctx.session() as s:
        row = s.get(WorkOrder, order_id)
        if row is None:
            raise not_found(f"工单 {order_id} 不存在")
        if row.status in ("verified", "cancelled"):
            raise bad_request("已复核或已取消的工单不能再追加现场反馈")
        saved = save_uploads(
            uploads,
            ctx.uploads_dir / "work-orders" / row.id,
            int(ctx.settings.work_order_max_attachment_mb * (1 << 20)),
            max_total_bytes=MAX_WORK_ORDER_TOTAL_BYTES,
        )
        paths = [path for _, path, _ in saved]
        attachments = []
        for name, path, size in saved:
            metadata = attachment_metadata(name)
            attachments.append(
                {
                    "name": name,
                    "url": ctx.url_for(path),
                    "size_bytes": size,
                    "kind": metadata["kind"],
                    "mime_type": metadata["mime_type"],
                }
            )
        try:
            updated = add_work_order_feedback(
                s,
                row,
                operator=operator,
                note=note,
                location={"longitude": lon, "latitude": lat} if lon is not None and lat is not None else None,
                attachments=attachments,
            )
        except Exception:
            remove(paths)
            raise
        return order_to_dict(updated)


@router.post(
    "/work-orders/{order_id}/feedback/{index}/assess",
    response_model=AssessmentOut,
    status_code=201,
    summary="将现场反馈转入风险研判",
)
def assess_work_order_feedback(
    order_id: str,
    index: int,
    body: WorkOrderFeedbackAssessmentCreate | None = None,
    ctx: AppContext = Depends(get_ctx),
) -> dict:
    with ctx.session() as s:
        order = s.get(WorkOrder, order_id)
        if order is None:
            raise not_found(f"工单 {order_id} 不存在")
        entries = order.feedback or []
        if index < 0 or index >= len(entries):
            raise bad_request("现场反馈序号不存在")
        entry = entries[index]
        summary = body.summary.strip() if body and body.summary.strip() else entry.get("note", "")
        row = create_assessment(
            ctx,
            s,
            AssessmentCreate(
                event_id=order.event_id,
                decision="needs_review",
                summary=summary or f"工单 {order.id} 现场反馈需要重新研判",
                evidence=[
                    {
                        "kind": "work_order_feedback",
                        "id": f"{order.id}:{index}",
                        "work_order_id": order.id,
                        "feedback": entry,
                    }
                ],
                impact={"source": "work_order_feedback", "work_order_id": order.id},
                missing_information=["结合最新现场信息和观测数据完成复核"],
                priority=order.priority,
                operator=(body.operator if body else entry.get("operator", "现场处置人员")),
            ),
        )
        return assessment_to_dict(row)


@router.post(
    "/work-orders/{order_id}/resources/use",
    response_model=WorkOrderOut,
    summary="从应急资源库存登记资源使用",
)
def use_work_order_resource(
    order_id: str,
    body: WorkOrderResourceUseCreate,
    ctx: AppContext = Depends(get_ctx),
) -> dict:
    with ctx.session() as s:
        order = s.get(WorkOrder, order_id)
        if order is None:
            raise not_found(f"工单 {order_id} 不存在")
        if order.status in ("verified", "cancelled"):
            raise bad_request("已复核或已取消的工单不能登记资源使用")
        resource = s.get(EmergencyResource, body.resource_id)
        if resource is None:
            raise not_found(f"应急资源 {body.resource_id} 不存在")
        if resource.status == "unavailable" or resource.available < body.quantity:
            raise bad_request(
                f"{resource.name} 当前可用数量不足（可用 {resource.available} {resource.contact}）"
            )
        resource.available -= body.quantity
        if resource.available == 0:
            resource.status = "limited"
        resource.updated_at = timeutil.now()
        updated = add_work_order_feedback(
            s,
            order,
            operator=body.operator,
            note=(
                f"资源使用：{resource.name} {body.quantity} 单位"
                f"{f'；{body.note.strip()}' if body.note.strip() else ''}"
            ),
            location=None,
            attachments=[],
        )
        updated.feedback = [
            *updated.feedback[:-1],
            {
                **updated.feedback[-1],
                "resource_usage": {
                    "resource_id": resource.id,
                    "resource_name": resource.name,
                    "quantity": body.quantity,
                    "remaining": resource.available,
                },
            },
        ]
        s.commit()
        return order_to_dict(updated)


@router.post(
    "/scenario-runs/{run_id}/dispatch",
    response_model=list[WorkOrderOut],
    status_code=201,
    summary="将选定推演方案转为协同处置工单",
)
def dispatch_scenario_run(
    run_id: str, body: ScenarioDispatchIn, ctx: AppContext = Depends(get_ctx)
) -> list[dict]:
    with ctx.session() as s:
        return [order_to_dict(row) for row in dispatch_scenario_actions(ctx, s, run_id, body)]


@router.patch("/work-orders/{order_id}", response_model=WorkOrderOut)
def patch_work_order(
    order_id: str, body: WorkOrderPatch, ctx: AppContext = Depends(get_ctx)
) -> dict:
    with ctx.session() as s:
        row = s.get(WorkOrder, order_id)
        if row is None:
            raise not_found(f"工单 {order_id} 不存在")
        return order_to_dict(update_work_order(s, row, body))


@router.get("/reviews/draft", response_model=ReviewDraftOut, summary="自动汇总复盘时间线与指标")
def review_draft(
    entity_type: str,
    entity_id: str,
    ctx: AppContext = Depends(get_ctx),
) -> dict:
    if entity_type not in ("event", "monitoring_task", "drill"):
        raise bad_request("复盘对象类型必须是 event / monitoring_task / drill")
    event_ids: list[str] = []
    entity_label = entity_id
    analysis_task_ids: list[str] = []
    drill_run: ScenarioRunRecord | None = None
    with ctx.session() as s:
        if entity_type == "event":
            event = s.get(Event, entity_id)
            if event is None:
                raise not_found(f"事件 {entity_id} 不存在")
            event_ids = [event.id]
            entity_label = event.name
            if event.task_id:
                analysis_task_ids.append(event.task_id)
            runs = []
        elif entity_type == "monitoring_task":
            task = s.get(MonitoringTask, entity_id)
            if task is None:
                raise not_found(f"监测任务 {entity_id} 不存在")
            entity_label = task.name
            runs = s.scalars(
                select(MonitoringRun)
                .where(MonitoringRun.monitoring_task_id == task.id)
                .order_by(MonitoringRun.created_at)
            ).all()
            event_ids = list(dict.fromkeys(eid for run in runs for eid in (run.event_ids or [])))
            analysis_task_ids = [run.analysis_task_id for run in runs if run.analysis_task_id]
        elif entity_type == "drill":
            drill_run = s.get(ScenarioRunRecord, entity_id)
            if drill_run is None or drill_run.payload.get("run_kind") != "drill":
                raise not_found(f"演练运行 {entity_id} 不存在")
            entity_label = drill_run.payload.get("title", entity_id)
            runs = []
        else:
            runs = []
        assessments = s.scalars(
            select(AssessmentRecord)
            .where(AssessmentRecord.event_id.in_(event_ids))
            .order_by(AssessmentRecord.created_at)
        ).all() if event_ids else []
        orders = s.scalars(
            select(WorkOrder)
            .where(WorkOrder.event_id.in_(event_ids))
            .order_by(WorkOrder.created_at)
        ).all() if event_ids else []
        logs = s.scalars(
            select(EventLog)
            .where(EventLog.event_id.in_(event_ids))
            .order_by(EventLog.timestamp)
        ).all() if event_ids else []
        scenario_ids = [order.scenario_run_id for order in orders if order.scenario_run_id]
        scenarios = s.scalars(
            select(ScenarioRunRecord).where(ScenarioRunRecord.id.in_(scenario_ids))
        ).all() if scenario_ids else []
        tasks = s.scalars(
            select(Task).where(Task.id.in_(analysis_task_ids))
        ).all() if analysis_task_ids else []

    if drill_run is not None:
        payload = drill_run.payload or {}
        metrics = dict(payload.get("metrics") or {})
        metrics.update(
            {
                "frame_count": len(payload.get("frames") or []),
                "timeline_count": len(payload.get("timeline") or []),
                "data_classification": drill_run.data_classification,
            }
        )
        timeline = [
            {
                "at": drill_run.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "kind": "演练",
                "operator": payload.get("operator", "应急演练人员"),
                "text": item.get("text", ""),
                "ref": f"{drill_run.id}:{index}",
            }
            for index, item in enumerate(payload.get("timeline") or [], 1)
        ]
        findings = [
            "演练参数、版本、运行结果和过程时间线已关联保存",
            "演练结果为模拟数据，不代表专业疏散或灾害模型结论",
        ]
        if metrics.get("peak_waiting"):
            findings.append(f"峰值排队 {metrics['peak_waiting']} 人，需要检查出口组织")
        return {
            "entity_type": "drill",
            "entity_id": entity_id,
            "summary": payload.get("summary")
            or f"演练「{entity_label}」共记录 {len(timeline)} 个过程节点。",
            "metrics": metrics,
            "findings": findings,
            "recommendations": [
                "将有效处置动作回写到同类任务模板和演练预案",
                "接入真实步行网络和出口容量数据后重新标定演练参数",
            ],
            "timeline": timeline,
        }

    sla = [(order, work_order_sla(order)) for order in orders]
    verified = [item for item in sla if item[0].status == "verified"]
    overdue = [item for item in sla if item[1]["overdue"]]

    def avg(key: str) -> float | None:
        values = [float(item[1][key]) for item in sla if item[1][key] is not None]
        return round(sum(values) / len(values), 1) if values else None

    timeline: list[dict] = []
    for log in logs:
        timeline.append(
            {
                "at": log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "kind": "事件",
                "operator": log.operator,
                "text": log.note,
                "ref": f"{log.event_id}:{log.action}",
            }
        )
    for assessment in assessments:
        timeline.append(
            {
                "at": assessment.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "kind": "研判",
                "operator": assessment.operator,
                "text": assessment.summary,
                "ref": assessment.id,
            }
        )
    for order in orders:
        timeline.append(
            {
                "at": order.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "kind": "工单",
                "operator": order.assignee or order.unit,
                "text": f"{order.id} {order.title} 已派发",
                "ref": order.id,
            }
        )
        for item in order.feedback or []:
            if not item.get("at"):
                continue
            timeline.append(
                {
                    "at": item["at"],
                    "kind": "现场反馈",
                    "operator": item.get("operator", ""),
                    "text": item.get("note", item.get("action", "")),
                    "ref": order.id,
                }
            )
    for scenario in scenarios:
        timeline.append(
            {
                "at": scenario.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "kind": "情景推演",
                "operator": scenario.provider,
                "text": scenario.payload.get("variant_label", scenario.id),
                "ref": scenario.id,
            }
        )
    timeline.sort(key=lambda item: item["at"])

    findings: list[str] = []
    if not assessments:
        findings.append("缺少研判记录，无法形成完整证据链")
    for assessment in assessments:
        for missing in assessment.missing_information or []:
            findings.append(f"研判缺失信息：{missing}")
    if not orders:
        findings.append("尚无处置工单，处置过程无法复盘")
    if overdue:
        findings.append(f"{len(overdue)} 张工单超过办理时限")
    rejected = [order for order in orders if order.status == "rejected"]
    if rejected:
        findings.append(f"{len(rejected)} 张工单复核退回，需要分析原因")
    false_alarms = [item for item in assessments if item.decision == "false_alarm"]
    if false_alarms:
        findings.append(f"{len(false_alarms)} 次研判结论为误报，应检查线索阈值")
    if not findings:
        findings.append("时间线、研判和工单记录均已形成，未发现明显流程断点")

    recommendations: list[str] = []
    if not assessments:
        recommendations.append("补充证据核查和研判记录后再确认复盘结论")
    if overdue:
        recommendations.append("复核责任单位时限设置和调度升级规则")
    if rejected:
        recommendations.append("将复核退回原因回写到处置动作模板")
    if false_alarms:
        recommendations.append("使用已核验样本重新评估识别阈值，避免直接据已报告事件计算漏报率")
    if not recommendations:
        recommendations.append("将本次有效处置动作保留为同类事件的任务和情景模板")

    metrics = {
        "event_count": len(event_ids),
        "run_count": len(runs),
        "assessment_count": len(assessments),
        "work_order_count": len(orders),
        "verified_orders": len(verified),
        "overdue_orders": len(overdue),
        "avg_response_min": avg("response_min"),
        "avg_execution_min": avg("execution_min"),
        "avg_review_min": avg("review_min"),
        "analysis_task_count": len(tasks),
        "scenario_count": len(scenarios),
        "timeline_count": len(timeline),
    }
    summary = (
        f"复盘对象：{entity_label}。共关联 {len(event_ids)} 个事件、{len(assessments)} 条研判、"
        f"{len(orders)} 张工单和 {len(scenarios)} 个情景结果；当前完成复核 {len(verified)} 张工单，"
        f"超时 {len(overdue)} 张。"
    )
    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "summary": summary,
        "metrics": metrics,
        "findings": findings,
        "recommendations": recommendations,
        "timeline": timeline,
    }


@router.get("/reviews/cases", response_model=list[ReviewOut], summary="已确认复盘案例库")
def list_review_cases(
    q: str | None = None,
    limit: int = Query(default=200, ge=1, le=2000),
    ctx: AppContext = Depends(get_ctx),
) -> list[dict]:
    stmt = select(ReviewRecord).where(ReviewRecord.status == "confirmed")
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            ReviewRecord.summary.ilike(pattern)
            | ReviewRecord.entity_id.ilike(pattern)
        )
    with ctx.session() as s:
        rows = s.scalars(
            stmt.order_by(ReviewRecord.updated_at.desc(), ReviewRecord.id.desc()).limit(limit)
        ).all()
        return [review_to_dict(row) for row in rows]


@router.patch("/reviews/{review_id}", response_model=ReviewOut, summary="审核或编辑复盘")
def patch_review(
    review_id: str,
    body: ReviewUpdate,
    ctx: AppContext = Depends(get_ctx),
) -> dict:
    with ctx.session() as s:
        row = s.get(ReviewRecord, review_id)
        if row is None:
            raise not_found(f"复盘记录 {review_id} 不存在")
        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(row, field, value)
        row.updated_at = timeutil.now()
        s.commit()
        return review_to_dict(row)


@router.post(
    "/reviews/{review_id}/apply-template",
    response_model=TaskTemplateRevisionOut,
    status_code=201,
    summary="将已审核复盘规则应用到任务模板",
)
def apply_review_to_template(
    review_id: str,
    body: TaskTemplateApply,
    ctx: AppContext = Depends(get_ctx),
) -> dict:
    with ctx.session() as s:
        review = s.get(ReviewRecord, review_id)
        if review is None:
            raise not_found(f"复盘记录 {review_id} 不存在")
        if review.status != "confirmed":
            raise bad_request("复盘记录确认后才能应用到任务模板")
        template = s.get(MonitoringTaskTemplate, body.template_id)
        if template is None:
            raise not_found(f"任务模板 {body.template_id} 不存在")
        version_no = (s.scalar(
            select(func.count()).select_from(TaskTemplateRevision).where(
                TaskTemplateRevision.template_id == template.id
            )
        ) or 0) + 1
        now = timeutil.now()
        revision = TaskTemplateRevision(
            template_id=template.id,
            version_no=version_no,
            rule_config=body.rule_config,
            source_review_id=review.id,
            operator=body.operator.strip() or "系统管理员",
            created_at=now,
        )
        s.add(revision)
        template.rule_config = {**(template.rule_config or {}), **body.rule_config}
        template.updated_at = now
        s.commit()
        s.refresh(revision)
        return {
            "id": revision.id,
            "template_id": revision.template_id,
            "version_no": revision.version_no,
            "rule_config": revision.rule_config,
            "source_review_id": revision.source_review_id,
            "operator": revision.operator,
            "created_at": timeutil.fmt(revision.created_at),
        }


@router.get("/reviews/{review_id}/export", summary="导出复盘 Markdown 报告")
def export_review(review_id: str, ctx: AppContext = Depends(get_ctx)) -> Response:
    with ctx.session() as s:
        row = s.get(ReviewRecord, review_id)
        if row is None:
            raise not_found(f"复盘记录 {review_id} 不存在")
        finding_lines = "\n".join(f"- {item}" for item in row.findings or []) or "- 无"
        recommendation_lines = "\n".join(f"- {item}" for item in row.recommendations or []) or "- 无"
        metric_lines = "\n".join(f"- {key}: {value}" for key, value in (row.metrics or {}).items()) or "- 无"
        text = (
            f"# 城市智眼复盘报告 {row.id}\n\n"
            f"- 对象：{row.entity_type} / {row.entity_id}\n"
            f"- 状态：{row.status}\n\n"
            f"## 摘要\n\n{row.summary}\n\n"
            f"## 评价指标\n\n{metric_lines}\n\n"
            f"## 发现\n\n{finding_lines}\n\n"
            f"## 改进建议\n\n{recommendation_lines}\n"
        )
    return Response(
        content=text.encode("utf-8"),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{review_id}.md"'},
    )


@router.get("/reviews", response_model=list[ReviewOut])
def list_reviews(
    entity_type: str | None = None,
    entity_id: str | None = None,
    ctx: AppContext = Depends(get_ctx),
) -> list[dict]:
    stmt = select(ReviewRecord)
    if entity_type:
        stmt = stmt.where(ReviewRecord.entity_type == entity_type)
    if entity_id:
        stmt = stmt.where(ReviewRecord.entity_id == entity_id)
    with ctx.session() as s:
        rows = s.scalars(stmt.order_by(ReviewRecord.created_at.desc(), ReviewRecord.id.desc()))
        return [review_to_dict(row) for row in rows]


@router.post("/reviews", response_model=ReviewOut, status_code=201)
def post_review(body: ReviewCreate, ctx: AppContext = Depends(get_ctx)) -> dict:
    with ctx.session() as s:
        return review_to_dict(create_review(ctx, s, body))
