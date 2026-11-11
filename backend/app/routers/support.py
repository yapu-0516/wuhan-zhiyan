"""公共支撑接口：角色、网格、站内通知、操作审计与 SLA 汇总。"""
from __future__ import annotations

import csv
import io
import json
from dataclasses import replace

import cityeye_algo as ca
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import func, select

from .. import timeutil
from ..context import AppContext, get_ctx, not_found
from ..models import (
    AuditLog,
    DataAsset,
    EmergencyResource,
    Event,
    MonitoringRun,
    NotificationRecord,
    OperatorAccount,
    ResponsibilityGrid,
    ReviewRecord,
    Task,
    WorkOrder,
)
from ..schemas import (
    AccountOut,
    AuditLogOut,
    EmergencyResourceOut,
    EmergencyResourcePatch,
    NotificationOut,
    ResponsibilityGridOut,
    ResponsibilityGridPatch,
    SlaSummaryOut,
    ServiceStatusOut,
    ReviewStatsOut,
    RuntimeConfigPatch,
    WorkOrderOut,
)
from ..services.support import (
    account_to_dict,
    audit_to_dict,
    grid_to_dict,
    notification_to_dict,
)
from ..services.workflow import order_to_dict, work_order_sla

router = APIRouter(prefix="/support", tags=["公共支撑"])


def _csv_response(rows: list[list[object]], filename: str) -> Response:
    buffer = io.StringIO()
    csv.writer(buffer).writerows(rows)
    return Response(
        content=("\ufeff" + buffer.getvalue()).encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/accounts", response_model=list[AccountOut], summary="演示角色与组织目录")
def list_accounts(ctx: AppContext = Depends(get_ctx)) -> list[dict]:
    with ctx.session() as s:
        rows = s.scalars(
            select(OperatorAccount).order_by(OperatorAccount.status, OperatorAccount.id)
        ).all()
        return [account_to_dict(row) for row in rows]


@router.get("/grids", response_model=list[ResponsibilityGridOut], summary="责任网格目录")
def list_grids(
    district: str | None = None,
    ctx: AppContext = Depends(get_ctx),
) -> list[dict]:
    stmt = select(ResponsibilityGrid)
    if district:
        stmt = stmt.where(ResponsibilityGrid.district == district)
    with ctx.session() as s:
        rows = s.scalars(stmt.order_by(ResponsibilityGrid.district, ResponsibilityGrid.id)).all()
        return [grid_to_dict(row) for row in rows]


@router.patch("/grids/{grid_id}", response_model=ResponsibilityGridOut, summary="维护责任网格")
def patch_grid(
    grid_id: str,
    body: ResponsibilityGridPatch,
    ctx: AppContext = Depends(get_ctx),
) -> dict:
    with ctx.session() as s:
        row = s.get(ResponsibilityGrid, grid_id)
        if row is None:
            raise not_found(f"责任网格 {grid_id} 不存在")
        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(row, field, value)
        s.commit()
        return grid_to_dict(row)


def resource_to_dict(row: EmergencyResource) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "kind": row.kind,
        "longitude": row.longitude,
        "latitude": row.latitude,
        "capability": row.capability,
        "capacity": row.capacity,
        "available": row.available,
        "status": row.status,
        "contact": row.contact,
        "notes": row.notes,
        "updated_at": row.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
    }


@router.get("/emergency-resources", response_model=list[EmergencyResourceOut], summary="应急资源可调度能力")
def list_emergency_resources(
    kind: str | None = None,
    status: str | None = None,
    q: str | None = None,
    limit: int = Query(default=500, ge=1, le=2000),
    ctx: AppContext = Depends(get_ctx),
) -> list[dict]:
    stmt = select(EmergencyResource)
    if kind:
        stmt = stmt.where(EmergencyResource.kind == kind)
    if status:
        stmt = stmt.where(EmergencyResource.status == status)
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            EmergencyResource.name.ilike(pattern)
            | EmergencyResource.capability.ilike(pattern)
        )
    with ctx.session() as s:
        rows = s.scalars(stmt.order_by(EmergencyResource.kind, EmergencyResource.name).limit(limit)).all()
        return [resource_to_dict(row) for row in rows]


@router.patch("/emergency-resources/{resource_id}", response_model=EmergencyResourceOut, summary="更新资源可用状态")
def patch_emergency_resource(
    resource_id: str, body: EmergencyResourcePatch, ctx: AppContext = Depends(get_ctx)
) -> dict:
    with ctx.session() as s:
        row = s.get(EmergencyResource, resource_id)
        if row is None:
            raise not_found(f"应急资源 {resource_id} 不存在")
        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(row, field, value)
        if row.available > row.capacity:
            row.available = row.capacity
        row.updated_at = timeutil.now()
        s.commit()
        return resource_to_dict(row)


@router.get("/notifications", response_model=list[NotificationOut], summary="站内通知")
def list_notifications(
    target: str | None = None,
    unread_only: bool = False,
    limit: int = Query(default=100, ge=1, le=500),
    ctx: AppContext = Depends(get_ctx),
) -> list[dict]:
    stmt = select(NotificationRecord)
    if target:
        stmt = stmt.where(NotificationRecord.target == target)
    if unread_only:
        stmt = stmt.where(NotificationRecord.is_read.is_(False))
    with ctx.session() as s:
        rows = s.scalars(
            stmt.order_by(NotificationRecord.created_at.desc(), NotificationRecord.id.desc()).limit(limit)
        ).all()
        return [notification_to_dict(row) for row in rows]


@router.get("/notifications/unread-count", summary="未读通知数量")
def unread_notification_count(
    target: str | None = None,
    ctx: AppContext = Depends(get_ctx),
) -> dict:
    stmt = select(func.count()).select_from(NotificationRecord).where(NotificationRecord.is_read.is_(False))
    if target:
        stmt = stmt.where(NotificationRecord.target == target)
    with ctx.session() as s:
        return {"count": s.scalar(stmt) or 0}


@router.patch("/notifications/{notification_id}/read", response_model=NotificationOut, summary="标记通知已读")
def mark_notification_read(notification_id: int, ctx: AppContext = Depends(get_ctx)) -> dict:
    with ctx.session() as s:
        row = s.get(NotificationRecord, notification_id)
        if row is None:
            raise not_found(f"通知 {notification_id} 不存在")
        row.is_read = True
        s.commit()
        return notification_to_dict(row)


@router.patch("/notifications/read-all", summary="全部标记已读")
def mark_all_notifications_read(ctx: AppContext = Depends(get_ctx)) -> dict:
    with ctx.session() as s:
        rows = s.scalars(select(NotificationRecord).where(NotificationRecord.is_read.is_(False))).all()
        for row in rows:
            row.is_read = True
        s.commit()
        return {"updated": len(rows)}


@router.get("/audit", response_model=list[AuditLogOut], summary="跨模块操作审计")
def list_audit_logs(
    entity_type: str | None = None,
    entity_id: str | None = None,
    operator_id: str | None = None,
    limit: int = Query(default=200, ge=1, le=2000),
    ctx: AppContext = Depends(get_ctx),
) -> list[dict]:
    stmt = select(AuditLog)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if entity_id:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    if operator_id:
        stmt = stmt.where(AuditLog.operator_id == operator_id)
    with ctx.session() as s:
        rows = s.scalars(
            stmt.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(limit)
        ).all()
        return [audit_to_dict(row) for row in rows]


@router.get("/sla-summary", response_model=SlaSummaryOut, summary="工单 SLA 汇总报表")
def sla_summary(ctx: AppContext = Depends(get_ctx)) -> dict:
    with ctx.session() as s:
        rows = s.scalars(select(WorkOrder).order_by(WorkOrder.updated_at.desc())).all()
        events = {event.id: event.event_type for event in s.scalars(select(Event)).all()}
    sla_items = [(row, work_order_sla(row)) for row in rows]
    active = [item for item in sla_items if item[0].status not in ("verified", "cancelled")]
    overdue = [item for item in active if item[1]["overdue"]]
    verified = [item for item in sla_items if item[0].status == "verified"]

    def average(key: str, items: list[tuple[WorkOrder, dict]]) -> float | None:
        values = [float(item[1][key]) for item in items if item[1][key] is not None]
        return round(sum(values) / len(values), 1) if values else None

    def grouped(items: list[tuple[WorkOrder, dict]], key_fn: Any) -> list[dict]:
        values: dict[str, dict[str, int]] = {}
        for order, sla in items:
            key = str(key_fn(order) or "未指定")
            bucket = values.setdefault(key, {"count": 0, "overdue": 0})
            bucket["count"] += 1
            bucket["overdue"] += int(bool(sla["overdue"]))
        return [
            {"name": name, **counts}
            for name, counts in sorted(values.items(), key=lambda item: (-item[1]["count"], item[0]))
        ]

    candidates = [
        item for item in sla_items
        if item[0].status not in ("verified", "cancelled") or item[1]["overdue"]
    ][:50]
    if len(candidates) < 10:
        candidates.extend(item for item in sla_items if item not in candidates)
    trend_groups: dict[str, list[tuple[WorkOrder, dict]]] = {}
    for item in sla_items:
        trend_groups.setdefault(item[0].created_at.strftime("%Y-%m-%d"), []).append(item)
    trend = [
        {
            "date": day,
            "total": len(items),
            "verified": sum(order.status == "verified" for order, _ in items),
            "overdue": sum(bool(sla["overdue"]) for _, sla in items),
            "avg_response_min": average("response_min", items),
            "avg_execution_min": average("execution_min", items),
        }
        for day, items in sorted(trend_groups.items())[-14:]
    ]
    return {
        "total_orders": len(rows),
        "active_orders": len(active),
        "overdue_orders": len(overdue),
        "verified_orders": len(verified),
        "avg_response_min": average("response_min", sla_items),
        "avg_execution_min": average("execution_min", sla_items),
        "avg_review_min": average("review_min", sla_items),
        "by_unit": grouped(sla_items, lambda order: order.unit),
        "by_priority": grouped(sla_items, lambda order: order.priority),
        "by_scenario": grouped(sla_items, lambda order: events.get(order.event_id)),
        "trend": trend,
        "orders": [order_to_dict(row) for row, _ in candidates[:50]],
    }


@router.get("/service-status", response_model=ServiceStatusOut, summary="系统配置与服务状态")
def service_status(ctx: AppContext = Depends(get_ctx)) -> dict:
    with ctx.session() as s:
        task_rows = s.execute(
            select(Task.status, func.count()).group_by(Task.status)
        ).all()
        run_rows = s.execute(
            select(MonitoringRun.status, func.count()).group_by(MonitoringRun.status)
        ).all()
        data_rows = s.execute(
            select(DataAsset.analysis_status, func.count()).group_by(DataAsset.analysis_status)
        ).all()
        orders = s.scalars(select(WorkOrder)).all()
        unread = s.scalar(
            select(func.count()).select_from(NotificationRecord).where(NotificationRecord.is_read.is_(False))
        ) or 0
    return {
        "database": ctx.settings.database_kind,
        "simulator_enabled": ctx.settings.simulator,
        "workflow_interval_sec": ctx.settings.workflow_interval,
        "task_pacing_sec": ctx.settings.task_pacing,
        "max_upload_mb": ctx.settings.max_upload_mb,
        "task_counts": {str(status): int(count) for status, count in task_rows},
        "run_counts": {str(status): int(count) for status, count in run_rows},
        "overdue_orders": sum(work_order_sla(order)["overdue"] for order in orders),
        "unread_notifications": int(unread),
        "data_counts": {str(status or "unknown"): int(count) for status, count in data_rows},
        "algorithms": ca.algorithms(),
    }


@router.patch("/config", response_model=ServiceStatusOut, summary="更新本地运行配置")
def patch_runtime_config(
    body: RuntimeConfigPatch,
    ctx: AppContext = Depends(get_ctx),
) -> dict:
    replacements = {}
    if body.task_pacing_sec is not None:
        replacements["task_pacing"] = body.task_pacing_sec
    if body.workflow_interval_sec is not None:
        replacements["workflow_interval"] = body.workflow_interval_sec
    if body.max_upload_mb is not None:
        replacements["max_upload_mb"] = body.max_upload_mb
    if replacements:
        ctx.settings = replace(ctx.settings, **replacements)
    return service_status(ctx)


@router.get("/review-stats", response_model=ReviewStatsOut, summary="真实处置与演练复盘统计")
def review_stats(ctx: AppContext = Depends(get_ctx)) -> dict:
    with ctx.session() as s:
        rows = s.scalars(select(ReviewRecord)).all()
    confirmed = sum(row.status == "confirmed" for row in rows)
    draft = sum(row.status == "draft" for row in rows)
    grouped: dict[str, dict[str, int]] = {}
    for row in rows:
        bucket = grouped.setdefault(row.entity_type, {"count": 0, "confirmed": 0, "draft": 0})
        bucket["count"] += 1
        bucket["confirmed" if row.status == "confirmed" else "draft"] += 1
    return {
        "confirmed": confirmed,
        "draft": draft,
        "by_entity_type": [
            {"name": name, **counts}
            for name, counts in sorted(grouped.items())
        ],
    }


@router.get("/audit/export", summary="导出操作审计 CSV")
def export_audit(ctx: AppContext = Depends(get_ctx)) -> Response:
    with ctx.session() as s:
        rows = s.scalars(
            select(AuditLog).order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        ).all()
    data: list[list[object]] = [
        [
            "时间", "请求方法", "请求路径", "动作", "对象类型", "对象编号",
            "操作人", "角色", "响应状态", "摘要", "修改前", "修改后",
        ]
    ]
    data.extend(
        [
            [
                row.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                row.method,
                row.path,
                row.action,
                row.entity_type,
                row.entity_id,
                row.operator_name,
                row.role,
                row.status_code,
                row.summary,
                json.dumps(row.before_data or {}, ensure_ascii=False),
                json.dumps(row.after_data or {}, ensure_ascii=False),
            ]
            for row in rows
        ]
    )
    return _csv_response(data, "cityeye-audit.csv")


@router.get("/sla-summary/export", summary="导出工单 SLA CSV")
def export_sla_summary(ctx: AppContext = Depends(get_ctx)) -> Response:
    with ctx.session() as s:
        rows = s.scalars(select(WorkOrder).order_by(WorkOrder.created_at.desc())).all()
    data: list[list[object]] = [
        [
            "工单编号", "标题", "关联事件", "责任单位", "状态", "优先级", "办理时限",
            "响应分钟", "执行分钟", "复核分钟", "已用分钟", "剩余分钟", "是否超时",
        ]
    ]
    for row in rows:
        item = work_order_sla(row)
        data.append(
            [
                row.id,
                row.title,
                row.event_id,
                row.unit,
                row.status,
                row.priority,
                row.due_at.strftime("%Y-%m-%d %H:%M:%S") if row.due_at else "",
                item["response_min"] if item["response_min"] is not None else "",
                item["execution_min"] if item["execution_min"] is not None else "",
                item["review_min"] if item["review_min"] is not None else "",
                item["elapsed_min"],
                item["remaining_min"] if item["remaining_min"] is not None else "",
                "是" if item["overdue"] else "否",
            ]
        )
    return _csv_response(data, "cityeye-sla-summary.csv")
