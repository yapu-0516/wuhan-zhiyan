"""业务闭环服务：监测任务、运行记录、研判、工单和复盘的编号、序列化与状态校验。"""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import timeutil
from ..models import (
    AssessmentRecord,
    DataAsset,
    Event,
    MonitoringRun,
    MonitoringTask,
    MonitoringTaskTemplate,
    ReviewRecord,
    ScenarioRunRecord,
    Source,
    Task,
    WorkOrder,
)
from ..schemas import (
    AssessmentCreate,
    MonitoringRunCreate,
    MonitoringTaskCreate,
    MonitoringTaskExecute,
    MonitoringTaskPatch,
    MonitoringTaskTemplateCreate,
    ReviewCreate,
    ScenarioActionIn,
    ScenarioDispatchIn,
    WorkOrderCreate,
    WorkOrderPatch,
)
from .events import default_assignee, next_id
from .support import create_notification, notify_work_order
from .tasks import create_task, submit

if TYPE_CHECKING:
    from ..context import AppContext

log = logging.getLogger("cityeye.workflow")

TASK_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "draft": ("scheduled", "running"),
    "scheduled": ("running", "failed"),
    "running": ("completed", "failed"),
    "failed": ("scheduled", "running"),
    "completed": ("scheduled", "running"),
}
ORDER_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "pending": ("accepted", "in_progress", "cancelled"),
    "accepted": ("in_progress", "rejected", "cancelled"),
    "in_progress": ("completed", "cancelled"),
    "completed": ("verified", "rejected"),
    "rejected": ("in_progress", "cancelled"),
    "verified": (),
    "cancelled": (),
}
ORDER_STATUS_CN = {
    "pending": "待接单",
    "accepted": "已接单",
    "in_progress": "执行中",
    "completed": "待复核",
    "verified": "已复核",
    "rejected": "复核退回",
    "cancelled": "已取消",
}

SCENARIO_ACTIONS: dict[str, tuple[tuple[str, str], ...]] = {
    "flood": (
        ("现场核查积水边界与雨水口状态", "核查低洼点水位、退水速度、雨箅子堵塞与车辆通行条件。"),
        ("实施抽排并落实道路通行管控", "根据现场条件布设泵车、清理排水口，并对受影响路段采取交通管控。"),
    ),
    "traffic": (
        ("核查拥堵原因与排队范围", "核实现场事故、占道和信号配时，确认拥堵尾部与受影响路口。"),
        ("落实分流引导与节点管控", "按选定方案在关键节点实施分流、信号调整和交通引导。"),
    ),
    "fire": (
        ("实施危险区警戒与人员疏散", "核实现场火势、烟气和人员位置，组织危险区警戒与疏散。"),
        ("核查消防通道与周边道路条件", "保障消防车辆通行，清理占用通道并跟踪周边敏感对象。"),
    ),
}

RISK_PRIORITY = {
    "critical": "critical",
    "high": "high",
    "medium": "medium",
    "low": "low",
    "unknown": "medium",
}

DUE_MINUTES = {"critical": 30, "high": 60, "medium": 120, "low": 180}


def _fmt(value: datetime | None) -> str | None:
    return timeutil.fmt(value) if value is not None else None


def task_to_dict(row: MonitoringTask) -> dict[str, Any]:
    return {
        "id": row.id,
        "name": row.name,
        "event_type": row.event_type,
        "schedule_type": row.schedule_type,
        "status": row.status,
        "area_name": row.area_name,
        "bbox": row.bbox or [],
        "data_source_ids": row.data_source_ids or [],
        "rule_config": row.rule_config or {},
        "owner": row.owner,
        "notify_targets": row.notify_targets or [],
        "template_key": row.template_key,
        "start_at": _fmt(row.start_at),
        "end_at": _fmt(row.end_at),
        "next_run_at": _fmt(row.next_run_at),
        "last_run_at": _fmt(row.last_run_at),
        "created_at": timeutil.fmt(row.created_at),
        "updated_at": timeutil.fmt(row.updated_at),
    }


def task_template_to_dict(row: MonitoringTaskTemplate) -> dict[str, Any]:
    return {
        "id": row.id,
        "name": row.name,
        "description": row.description,
        "event_type": row.event_type,
        "schedule_type": row.schedule_type,
        "area_name": row.area_name,
        "bbox": row.bbox or [],
        "data_source_ids": row.data_source_ids or [],
        "rule_config": row.rule_config or {},
        "owner": row.owner,
        "notify_targets": row.notify_targets or [],
        "created_at": timeutil.fmt(row.created_at),
        "updated_at": timeutil.fmt(row.updated_at),
    }


def create_task_template(
    ctx: "AppContext", session: Session, body: MonitoringTaskTemplateCreate
) -> MonitoringTaskTemplate:
    ts = timeutil.now()
    with ctx.id_lock:
        row = MonitoringTaskTemplate(
            id=next_id(session, MonitoringTaskTemplate.id, "TP"),
            name=body.name.strip(),
            description=body.description.strip(),
            event_type=body.event_type,
            schedule_type=body.schedule_type,
            area_name=body.area_name.strip() or "武汉中心城区",
            bbox=body.bbox,
            data_source_ids=body.data_source_ids,
            rule_config=body.rule_config,
            owner=body.owner.strip(),
            notify_targets=body.notify_targets,
            created_at=ts,
            updated_at=ts,
        )
        session.add(row)
        session.commit()
    return row


def run_to_dict(row: MonitoringRun) -> dict[str, Any]:
    return {
        "id": row.id,
        "monitoring_task_id": row.monitoring_task_id,
        "analysis_task_id": row.analysis_task_id,
        "event_ids": row.event_ids or [],
        "status": row.status,
        "coverage": row.coverage or {},
        "quality": row.quality or {},
        "failure_reason": row.failure_reason,
        "started_at": _fmt(row.started_at),
        "finished_at": _fmt(row.finished_at),
        "created_at": timeutil.fmt(row.created_at),
    }


def assessment_to_dict(row: AssessmentRecord) -> dict[str, Any]:
    return {
        "id": row.id,
        "event_id": row.event_id,
        "monitoring_run_id": row.monitoring_run_id,
        "decision": row.decision,
        "summary": row.summary,
        "evidence": row.evidence or [],
        "impact": row.impact or {},
        "missing_information": row.missing_information or [],
        "priority": row.priority,
        "operator": row.operator,
        "created_at": timeutil.fmt(row.created_at),
    }


def _feedback_time(row: WorkOrder, target: str) -> datetime | None:
    for item in row.feedback or []:
        if item.get("to") == target or item.get("action") == target:
            raw = item.get("at")
            if not raw:
                continue
            try:
                return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).replace(tzinfo=None)
            except ValueError:
                continue
    return None


def _minutes_between(start: datetime | None, end: datetime | None) -> int | None:
    if start is None or end is None:
        return None
    return max(0, int((end - start).total_seconds() // 60))


def work_order_sla(row: WorkOrder, now: datetime | None = None) -> dict[str, Any]:
    ts = now or timeutil.now()
    accepted_at = _feedback_time(row, "accepted")
    started_at = _feedback_time(row, "in_progress")
    completed_at = _feedback_time(row, "completed")
    verified_at = _feedback_time(row, "verified")
    resolved_at = verified_at if row.status == "verified" else None
    elapsed_end = resolved_at or ts
    remaining_min = None
    if row.due_at is not None:
        remaining_min = int((row.due_at - ts).total_seconds() // 60)
    overdue = bool(
        row.due_at is not None
        and row.status not in ("verified", "cancelled")
        and ts > row.due_at
    )
    return {
        "accepted_at": _fmt(accepted_at),
        "started_at": _fmt(started_at),
        "completed_at": _fmt(completed_at),
        "verified_at": _fmt(verified_at),
        "response_min": _minutes_between(row.created_at, accepted_at),
        "execution_min": _minutes_between(started_at, completed_at),
        "review_min": _minutes_between(completed_at, verified_at),
        "elapsed_min": _minutes_between(row.created_at, elapsed_end) or 0,
        "remaining_min": remaining_min,
        "overdue": overdue,
    }


def order_to_dict(row: WorkOrder) -> dict[str, Any]:
    return {
        "id": row.id,
        "event_id": row.event_id,
        "assessment_id": row.assessment_id,
        "scenario_run_id": row.scenario_run_id,
        "title": row.title,
        "unit": row.unit,
        "assignee": row.assignee,
        "status": row.status,
        "priority": row.priority,
        "description": row.description,
        "due_at": _fmt(row.due_at),
        "feedback": row.feedback or [],
        "sla": work_order_sla(row),
        "created_at": timeutil.fmt(row.created_at),
        "updated_at": timeutil.fmt(row.updated_at),
    }


def review_to_dict(row: ReviewRecord) -> dict[str, Any]:
    return {
        "id": row.id,
        "entity_type": row.entity_type,
        "entity_id": row.entity_id,
        "status": row.status,
        "summary": row.summary,
        "metrics": row.metrics or {},
        "findings": row.findings or [],
        "recommendations": row.recommendations or [],
        "created_at": timeutil.fmt(row.created_at),
        "updated_at": timeutil.fmt(row.updated_at),
    }


def create_monitoring_task(
    ctx: "AppContext", session: Session, body: MonitoringTaskCreate, now: datetime | None = None
) -> MonitoringTask:
    ts = now or timeutil.now()
    asset_ids = [item for item in body.data_source_ids if item.startswith("D")]
    source_ids = [item for item in body.data_source_ids if item.startswith("S-")]
    for asset_id in asset_ids:
        asset = session.get(DataAsset, asset_id)
        if asset is None:
            raise HTTPException(404, f"数据资源 {asset_id} 不存在")
        if asset.analysis_status != "ready":
            raise HTTPException(409, f"数据资源 {asset_id} 尚未完成校验，不能绑定监测任务")
    for source_id in source_ids:
        if session.get(Source, source_id) is None:
            raise HTTPException(404, f"数据源 {source_id} 不存在")
    with ctx.id_lock:
        row = MonitoringTask(
            id=next_id(session, MonitoringTask.id, "MT"),
            name=body.name.strip(),
            event_type=body.event_type,
            schedule_type=body.schedule_type,
            status="scheduled" if body.schedule_type == "periodic" and body.next_run_at else "draft",
            area_name=body.area_name.strip() or "武汉中心城区",
            bbox=body.bbox,
            data_source_ids=body.data_source_ids,
            rule_config=body.rule_config,
            owner=body.owner.strip(),
            notify_targets=body.notify_targets,
            template_key=body.template_key,
            start_at=body.start_at,
            end_at=body.end_at,
            next_run_at=body.next_run_at,
            created_at=ts,
            updated_at=ts,
        )
        session.add(row)
        session.commit()
    return row


def update_monitoring_task(
    session: Session, row: MonitoringTask, body: MonitoringTaskPatch, now: datetime | None = None
) -> MonitoringTask:
    ts = now or timeutil.now()
    if body.status and body.status != row.status:
        if body.status not in TASK_TRANSITIONS[row.status]:
            allowed = "、".join(TASK_TRANSITIONS[row.status]) or "无"
            raise HTTPException(409, f"监测任务不能从 {row.status} 流转到 {body.status}；当前可流转：{allowed}")
        row.status = body.status
    if body.owner is not None:
        row.owner = body.owner.strip()
    if body.rule_config is not None:
        row.rule_config = body.rule_config
    if body.next_run_at is not None:
        row.next_run_at = body.next_run_at
    if body.status == "scheduled" and row.schedule_type == "periodic" and row.next_run_at is None:
        row.next_run_at = ts + timedelta(minutes=_task_interval_minutes(row))
    row.updated_at = ts
    session.commit()
    return row


def create_monitoring_run(
    ctx: "AppContext", session: Session, body: MonitoringRunCreate, now: datetime | None = None
) -> MonitoringRun:
    task = session.get(MonitoringTask, body.monitoring_task_id)
    if task is None:
        raise HTTPException(404, f"监测任务 {body.monitoring_task_id} 不存在")
    if body.analysis_task_id and session.get(Task, body.analysis_task_id) is None:
        raise HTTPException(404, f"AI 分析任务 {body.analysis_task_id} 不存在")
    missing_events = [eid for eid in body.event_ids if session.get(Event, eid) is None]
    if missing_events:
        raise HTTPException(404, f"事件不存在：{', '.join(missing_events)}")
    ts = now or timeutil.now()
    with ctx.id_lock:
        row = MonitoringRun(
            id=next_id(session, MonitoringRun.id, "MR"),
            monitoring_task_id=task.id,
            analysis_task_id=body.analysis_task_id,
            event_ids=body.event_ids,
            status=body.status,
            coverage=body.coverage,
            quality=body.quality,
            failure_reason=body.failure_reason,
            started_at=body.started_at,
            finished_at=body.finished_at,
            created_at=ts,
        )
        task.last_run_at = body.started_at or ts
        if body.status == "running":
            task.status = "running"
        elif body.status == "completed" and task.schedule_type == "instant":
            task.status = "completed"
        task.updated_at = ts
        session.add(row)
        session.commit()
    return row


def execute_monitoring_task(
    ctx: "AppContext", session: Session, task: MonitoringTask, body: MonitoringTaskExecute
) -> tuple[MonitoringRun, Task]:
    linked_assets = [item for item in task.data_source_ids if item.startswith("D")]
    for asset_id in linked_assets:
        asset = session.get(DataAsset, asset_id)
        if asset is None or asset.analysis_status != "ready":
            raise HTTPException(409, f"数据资源 {asset_id} 当前不可分析，请重新校验后再运行任务")
    pool = [item for item in ctx.samples.items if item["type"] == task.event_type and item.get("kind") != "csv"]
    if body.sample_id:
        sample = ctx.samples.by_id.get(body.sample_id)
        if sample is None or sample["type"] != task.event_type:
            raise HTTPException(404, f"{task.event_type} 类型的示例数据 {body.sample_id} 不存在")
    else:
        sample = next((item for item in pool if item.get("showcase")), pool[0] if pool else None)
    if sample is None:
        raise HTTPException(404, f"没有可用于{task.event_type}任务的示例数据")
    paths = ctx.samples.paths(sample)
    if len(task.bbox) == 4:
        longitude = (float(task.bbox[0]) + float(task.bbox[2])) / 2
        latitude = (float(task.bbox[1]) + float(task.bbox[3])) / 2
    else:
        longitude, latitude = sample.get("longitude"), sample.get("latitude")
    analysis = create_task(
        ctx,
        session,
        event_type=task.event_type,
        paths=paths,
        inputs=[{"name": path.name, "url": ctx.url_for(path)} for path in paths],
        longitude=longitude,
        latitude=latitude,
        create_event=True,
        sample_id=sample["id"],
        origin="business_task",
    )
    run = create_monitoring_run(
        ctx,
        session,
        MonitoringRunCreate(
            monitoring_task_id=task.id,
            analysis_task_id=analysis.id,
            status="pending",
            coverage={
                "bbox": task.bbox,
                "sample_id": sample["id"],
                "data_asset_ids": linked_assets,
            },
        ),
    )
    submit(ctx, analysis, paths)
    return run, analysis


def _task_interval_minutes(task: MonitoringTask) -> int:
    raw = (task.rule_config or {}).get("interval_minutes", 60)
    try:
        return max(1, min(10_080, int(raw)))
    except (TypeError, ValueError):
        return 60


def run_due_monitoring_tasks(
    ctx: "AppContext", now: datetime | None = None
) -> list[MonitoringRun]:
    """执行已排程且到期的周期任务；一次最多启动 5 个算法作业。"""
    ts = now or timeutil.now()
    with ctx.session() as s:
        candidates = list(
            s.scalars(
                select(MonitoringTask)
                .where(
                    MonitoringTask.schedule_type == "periodic",
                    MonitoringTask.status == "scheduled",
                    MonitoringTask.next_run_at.is_not(None),
                    MonitoringTask.next_run_at <= ts,
                )
                .order_by(MonitoringTask.next_run_at, MonitoringTask.id)
                .limit(20)
            )
        )
        due_ids = [
            task.id
            for task in candidates
            if task.end_at is None or task.end_at > ts
        ][:5]

    submitted: list[MonitoringRun] = []
    for task_id in due_ids:
        with ctx.session() as s:
            task = s.get(MonitoringTask, task_id)
            if (
                task is None
                or task.status != "scheduled"
                or task.next_run_at is None
                or task.next_run_at > ts
                or (task.end_at is not None and task.end_at <= ts)
            ):
                continue
            task.next_run_at = ts + timedelta(minutes=_task_interval_minutes(task))
            task.updated_at = ts
            s.commit()
            try:
                run, _ = execute_monitoring_task(ctx, s, task, MonitoringTaskExecute())
                submitted.append(run)
                log.info("周期任务 %s 已启动运行 %s，下次运行 %s", task.id, run.id, task.next_run_at)
            except HTTPException as exc:
                task.status = "failed"
                task.updated_at = ts
                s.commit()
                log.warning("周期任务 %s 启动失败：%s", task.id, exc.detail)
    return submitted


def create_assessment(
    ctx: "AppContext", session: Session, body: AssessmentCreate, now: datetime | None = None
) -> AssessmentRecord:
    if session.get(Event, body.event_id) is None:
        raise HTTPException(404, f"事件 {body.event_id} 不存在")
    if body.monitoring_run_id and session.get(MonitoringRun, body.monitoring_run_id) is None:
        raise HTTPException(404, f"监测运行记录 {body.monitoring_run_id} 不存在")
    with ctx.id_lock:
        row = AssessmentRecord(
            id=next_id(session, AssessmentRecord.id, "AS"),
            event_id=body.event_id,
            monitoring_run_id=body.monitoring_run_id,
            decision=body.decision,
            summary=body.summary.strip(),
            evidence=body.evidence,
            impact=body.impact,
            missing_information=body.missing_information,
            priority=body.priority,
            operator=body.operator.strip() or "值班员",
            created_at=now or timeutil.now(),
        )
        session.add(row)
        session.commit()
    return row


def create_work_order(
    ctx: "AppContext", session: Session, body: WorkOrderCreate, now: datetime | None = None
) -> WorkOrder:
    if session.get(Event, body.event_id) is None:
        raise HTTPException(404, f"事件 {body.event_id} 不存在")
    if body.assessment_id:
        assessment = session.get(AssessmentRecord, body.assessment_id)
        if assessment is None:
            raise HTTPException(404, f"研判记录 {body.assessment_id} 不存在")
        if assessment.event_id != body.event_id:
            raise HTTPException(409, "研判记录与工单事件不一致")
    if body.scenario_run_id and session.get(ScenarioRunRecord, body.scenario_run_id) is None:
        raise HTTPException(404, f"情景推演结果 {body.scenario_run_id} 不存在")
    ts = now or timeutil.now()
    with ctx.id_lock:
        row = WorkOrder(
            id=next_id(session, WorkOrder.id, "WO"),
            event_id=body.event_id,
            assessment_id=body.assessment_id,
            scenario_run_id=body.scenario_run_id,
            title=body.title.strip(),
            unit=body.unit.strip(),
            assignee=body.assignee.strip(),
            status="pending",
            priority=body.priority,
            description=body.description.strip(),
            due_at=body.due_at,
            feedback=[],
            created_at=ts,
            updated_at=ts,
        )
        session.add(row)
        notify_work_order(
            session,
            title=f"新工单 {row.id}",
            body=f"{row.title}，责任单位：{row.unit or '待指派'}。",
            target=row.unit or row.assignee or "待指派单位",
            level="warning" if body.priority in ("high", "critical") else "info",
            order_id=row.id,
        )
        session.commit()
    return row


def dispatch_scenario_actions(
    ctx: "AppContext", session: Session, run_id: str, body: ScenarioDispatchIn
) -> list[WorkOrder]:
    """把用户确认的推演方案转换成可追踪的协同处置工单。"""
    run = session.get(ScenarioRunRecord, run_id)
    if run is None:
        raise HTTPException(404, f"情景推演结果 {run_id} 不存在")
    if run.status not in ("success", "preview"):
        raise HTTPException(409, "失败或未完成的推演结果不能转为处置工单")
    event = session.get(Event, body.event_id)
    if event is None:
        raise HTTPException(404, f"事件 {body.event_id} 不存在")
    if body.assessment_id:
        assessment = session.get(AssessmentRecord, body.assessment_id)
        if assessment is None:
            raise HTTPException(404, f"研判记录 {body.assessment_id} 不存在")
        if assessment.event_id != event.id:
            raise HTTPException(409, "研判记录与处置事件不一致")
    existing = session.scalars(
        select(WorkOrder).where(
            WorkOrder.scenario_run_id == run_id,
            WorkOrder.event_id == event.id,
        )
    ).first()
    if existing is not None:
        raise HTTPException(409, f"该推演方案已转为工单，首张工单为 {existing.id}")

    payload = run.payload or {}
    frames = payload.get("frames") or []
    last_frame = frames[-1] if frames else {}
    risk = str(last_frame.get("risk_level") or "unknown")
    priority = RISK_PRIORITY.get(risk, "medium")
    variant = str(payload.get("variant_label") or "选定方案")
    unit = default_assignee(event.event_type, event.district)
    actions = body.actions or [
        ScenarioActionIn(title=title, unit=unit, assignee=unit, priority=priority, description=description)
        for title, description in SCENARIO_ACTIONS.get(run.scenario_type, ())
    ]
    if not actions:
        raise HTTPException(409, "该场景没有可转换的处置动作模板")

    metrics = last_frame.get("metrics") or {}
    metrics_text = "，".join(f"{key}={value}" for key, value in list(metrics.items())[:4])
    due_at = timeutil.now() + timedelta(minutes=DUE_MINUTES.get(priority, 120))
    created: list[WorkOrder] = []
    for action in actions:
        description = action.description.strip()
        basis = f"依据情景 {run_id}「{variant}」方案"
        if metrics_text:
            basis += f"（末帧指标：{metrics_text}）"
        created.append(
            create_work_order(
                ctx,
                session,
                WorkOrderCreate(
                    event_id=event.id,
                    assessment_id=body.assessment_id,
                    scenario_run_id=run_id,
                    title=action.title,
                    unit=action.unit.strip() or unit,
                    assignee=action.assignee.strip(),
                    priority=action.priority,
                    description=f"{basis}。{description}".strip(),
                    due_at=due_at,
                ),
            )
        )
    return created


def update_work_order(
    session: Session, row: WorkOrder, body: WorkOrderPatch, now: datetime | None = None
) -> WorkOrder:
    ts = now or timeutil.now()
    changed = False
    note = body.note.strip()
    if body.status and body.status != row.status:
        if body.status not in ORDER_TRANSITIONS[row.status]:
            raise HTTPException(
                409,
                f"工单不能从{ORDER_STATUS_CN[row.status]}流转到{ORDER_STATUS_CN[body.status]}",
            )
        previous = row.status
        row.status = body.status
        row.feedback = [
            *(row.feedback or []),
            {
                "at": timeutil.fmt(ts),
                "operator": body.operator.strip() or "值班员",
                "action": "status_changed",
                "from": previous,
                "to": body.status,
                "note": note or f"状态变更为{ORDER_STATUS_CN[body.status]}",
            },
        ]
        changed = True
    if body.assignee is not None and body.assignee.strip() != row.assignee:
        row.assignee = body.assignee.strip()
        changed = True
    if body.feedback is not None:
        row.feedback = [
            *(row.feedback or []),
            {"at": timeutil.fmt(ts), "operator": body.operator.strip() or "值班员", **body.feedback},
        ]
        changed = True
    elif note and not (body.status and body.status != row.status):
        row.feedback = [
            *(row.feedback or []),
            {"at": timeutil.fmt(ts), "operator": body.operator.strip() or "值班员", "action": "comment", "note": note},
        ]
        changed = True
    if changed:
        row.updated_at = ts
        if body.status and body.status != "pending":
            level = "success" if body.status == "verified" else "warning" if body.status in ("rejected", "cancelled") else "info"
            notify_work_order(
                session,
                title=f"工单 {row.id} 已更新",
                body=f"{row.title}：{ORDER_STATUS_CN.get(row.status, row.status)}",
                target=row.unit or row.assignee or "责任单位",
                level=level,
                order_id=row.id,
            )
    session.commit()
    return row


def add_work_order_feedback(
    session: Session,
    row: WorkOrder,
    *,
    operator: str,
    note: str,
    location: dict[str, float] | None,
    attachments: list[dict[str, Any]],
    now: datetime | None = None,
) -> WorkOrder:
    if row.status in ("verified", "cancelled"):
        raise HTTPException(409, "已复核或已取消的工单不能再追加现场反馈")
    ts = now or timeutil.now()
    if not note.strip() and not attachments and location is None:
        raise HTTPException(400, "现场反馈至少需要文字、位置或附件之一")
    entry: dict[str, Any] = {
        "at": timeutil.fmt(ts),
        "operator": operator.strip() or row.assignee or "现场处置人员",
        "action": "field_feedback",
        "note": note.strip() or "提交现场反馈",
    }
    if location is not None:
        entry["location"] = location
    if attachments:
        entry["attachments"] = attachments
    row.feedback = [*(row.feedback or []), entry]
    row.updated_at = ts
    notify_work_order(
        session,
        title="收到现场反馈",
        body=f"{row.id} {row.title}：{entry['note']}",
        target=row.unit or row.assignee or "调度席",
        level="info",
        order_id=row.id,
    )
    session.commit()
    return row


def create_review(
    ctx: "AppContext", session: Session, body: ReviewCreate, now: datetime | None = None
) -> ReviewRecord:
    if body.entity_type == "event" and session.get(Event, body.entity_id) is None:
        raise HTTPException(404, f"事件 {body.entity_id} 不存在")
    if body.entity_type == "monitoring_task" and session.get(MonitoringTask, body.entity_id) is None:
        raise HTTPException(404, f"监测任务 {body.entity_id} 不存在")
    if body.entity_type == "drill":
        drill = session.get(ScenarioRunRecord, body.entity_id)
        if drill is None or drill.payload.get("run_kind") != "drill":
            raise HTTPException(404, f"演练运行 {body.entity_id} 不存在")
    ts = now or timeutil.now()
    with ctx.id_lock:
        row = ReviewRecord(
            id=next_id(session, ReviewRecord.id, "RV"),
            entity_type=body.entity_type,
            entity_id=body.entity_id,
            status=body.status,
            summary=body.summary.strip(),
            metrics=body.metrics,
            findings=body.findings,
            recommendations=body.recommendations,
            created_at=ts,
            updated_at=ts,
        )
        session.add(row)
        if body.status == "confirmed":
            create_notification(
                session,
                title="复盘建议已确认",
                body=f"{row.id} 已确认，可纳入下一轮任务规则与预案评审。",
                target="任务责任组",
                level="success",
                entity_type="review",
                entity_id=row.id,
            )
        session.commit()
    return row
