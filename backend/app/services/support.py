"""公共支撑服务：身份、网格、站内通知与跨模块审计。"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import inspect as sqlalchemy_inspect, select
from sqlalchemy.orm import Session

from .. import timeutil
from ..models import (
    AssessmentRecord,
    AuditLog,
    DataAsset,
    EmergencyResource,
    Event,
    MonitoringRun,
    MonitoringTask,
    NotificationRecord,
    OperatorAccount,
    ResponsibilityGrid,
    ReviewRecord,
    ScenarioRunRecord,
    ScenarioSession,
    ScenarioTemplate,
    Task,
    WorkOrder,
)

if TYPE_CHECKING:
    from ..context import AppContext

log = logging.getLogger("cityeye.support")

_ENTITY = re.compile(
    r"/(events|tasks|data|monitoring-tasks|monitoring-runs|assessments|work-orders|reviews|"
    r"scenario-runs|scenario/templates|scenario/sessions|scenario/runs|"
    r"support/grids|support/emergency-resources|support/notifications)/([A-Za-z0-9_-]+)"
)
_ENTITY_TYPES = {
    "events": "event",
    "tasks": "analysis_task",
    "data": "data_asset",
    "monitoring-tasks": "monitoring_task",
    "monitoring-runs": "monitoring_run",
    "assessments": "assessment",
    "work-orders": "work_order",
    "reviews": "review",
    "scenario-runs": "scenario_run",
    "scenario/templates": "scenario_template",
    "scenario/sessions": "scenario_session",
    "scenario/runs": "scenario_run",
    "support/grids": "responsibility_grid",
    "support/emergency-resources": "emergency_resource",
    "support/notifications": "notification",
}
_ENTITY_MODELS = {
    "event": Event,
    "analysis_task": Task,
    "data_asset": DataAsset,
    "monitoring_task": MonitoringTask,
    "monitoring_run": MonitoringRun,
    "assessment": AssessmentRecord,
    "work_order": WorkOrder,
    "review": ReviewRecord,
    "scenario_run": ScenarioRunRecord,
    "scenario_session": ScenarioSession,
    "scenario_template": ScenarioTemplate,
    "responsibility_grid": ResponsibilityGrid,
    "emergency_resource": EmergencyResource,
    "notification": NotificationRecord,
}


def account_to_dict(row: OperatorAccount) -> dict[str, Any]:
    return {
        "id": row.id,
        "name": row.name,
        "role": row.role,
        "organization": row.organization,
        "grid_ids": row.grid_ids or [],
        "status": row.status,
        "contact": row.contact,
        "created_at": timeutil.fmt(row.created_at),
        "updated_at": timeutil.fmt(row.updated_at),
    }


def grid_to_dict(row: ResponsibilityGrid) -> dict[str, Any]:
    return {
        "id": row.id,
        "district": row.district,
        "name": row.name,
        "organization": row.organization,
        "owner": row.owner,
        "contact": row.contact,
        "bbox": row.bbox or [],
        "risk_types": row.risk_types or [],
        "created_at": timeutil.fmt(row.created_at),
    }


def notification_to_dict(row: NotificationRecord) -> dict[str, Any]:
    return {
        "id": row.id,
        "target": row.target,
        "title": row.title,
        "body": row.body,
        "level": row.level,
        "entity_type": row.entity_type,
        "entity_id": row.entity_id,
        "is_read": row.is_read,
        "created_at": timeutil.fmt(row.created_at),
    }


def audit_to_dict(row: AuditLog) -> dict[str, Any]:
    return {
        "id": row.id,
        "method": row.method,
        "path": row.path,
        "action": row.action,
        "entity_type": row.entity_type,
        "entity_id": row.entity_id,
        "operator_id": row.operator_id,
        "operator_name": row.operator_name,
        "role": row.role,
        "status_code": row.status_code,
        "summary": row.summary,
        "before_data": row.before_data or {},
        "after_data": row.after_data or {},
        "created_at": timeutil.fmt(row.created_at),
    }


def create_notification(
    session: Session,
    *,
    title: str,
    body: str,
    target: str = "",
    level: str = "info",
    entity_type: str = "",
    entity_id: str = "",
    created_at: datetime | None = None,
) -> NotificationRecord:
    row = NotificationRecord(
        target=target,
        title=title.strip(),
        body=body.strip(),
        level=level,
        entity_type=entity_type,
        entity_id=entity_id,
        is_read=False,
        created_at=created_at or timeutil.now(),
    )
    session.add(row)
    return row


def notify_work_order(
    session: Session,
    *,
    title: str,
    body: str,
    target: str,
    level: str,
    order_id: str,
) -> NotificationRecord:
    return create_notification(
        session,
        title=title,
        body=body,
        target=target,
        level=level,
        entity_type="work_order",
        entity_id=order_id,
    )


def audit_entity(path: str) -> tuple[str, str]:
    match = _ENTITY.search(path)
    if match is None:
        return "", ""
    return _ENTITY_TYPES.get(match.group(1), match.group(1)), match.group(2)


def audit_action(method: str, path: str) -> str:
    if path.endswith("/feedback"):
        return "field_feedback"
    if path.endswith("/dispatch"):
        return "scenario_dispatch"
    if path.endswith("/execute"):
        return "task_execute"
    if path.endswith("/report"):
        return "scenario_report"
    if path.endswith("/read") or path.endswith("/read-all"):
        return "notification_read"
    if path.rstrip("/").endswith("/events"):
        return "create_event"
    if path.rstrip("/").endswith("/work-orders"):
        return "create_work_order"
    if path.rstrip("/").endswith("/assessments"):
        return "create_assessment"
    if path.rstrip("/").endswith("/reviews"):
        return "create_review"
    if path.rstrip("/").endswith("/scenario/templates"):
        return "create_scenario_template"
    if path.rstrip("/").endswith("/task-templates"):
        return "create_task_template"
    if path.rstrip("/").endswith("/monitoring-tasks"):
        return "create_monitoring_task"
    if path.rstrip("/").endswith("/demo/reset"):
        return "reset_demo"
    return f"{method.lower()}_api"


def _json_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return timeutil.fmt(value)
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    return value


def capture_audit_entity(ctx: "AppContext", path: str) -> dict[str, Any]:
    """按请求路径读取对象当前数据库快照，供审计展示修改前后值。"""
    entity_type, entity_id = audit_entity(path)
    model = _ENTITY_MODELS.get(entity_type)
    if model is None or not entity_id:
        return {}
    try:
        key: Any = int(entity_id) if entity_type == "notification" else entity_id
        with ctx.session() as s:
            row = s.get(model, key)
            if row is None:
                return {}
            return {
                column.key: _json_value(getattr(row, column.key))
                for column in sqlalchemy_inspect(row).mapper.column_attrs
            }
    except Exception:  # noqa: BLE001 - 审计快照失败不影响原业务
        log.exception("读取审计对象快照失败：%s", path)
        return {}


def record_http_audit(
    ctx: "AppContext",
    *,
    method: str,
    path: str,
    status_code: int,
    operator_id: str,
    before_data: dict[str, Any] | None = None,
    after_data: dict[str, Any] | None = None,
) -> None:
    """记录一次写请求；审计失败不能影响原业务响应。"""
    try:
        with ctx.session() as s:
            account = s.get(OperatorAccount, operator_id) if operator_id else None
            entity_type, entity_id = audit_entity(path)
            s.add(
                AuditLog(
                    method=method,
                    path=path,
                    action=audit_action(method, path),
                    entity_type=entity_type,
                    entity_id=entity_id,
                    operator_id=account.id if account else "",
                    operator_name=account.name if account else "系统/未指定身份",
                    role=account.role if account else "",
                    status_code=status_code,
                    summary=f"{method} {path}",
                    before_data=before_data or {},
                    after_data=after_data or {},
                    created_at=timeutil.now(),
                )
            )
            s.commit()
    except Exception:  # noqa: BLE001 - 审计故障不能反向阻断业务
        log.exception("写入操作审计失败：%s %s", method, path)


def resolve_account(session: Session, operator_id: str | None) -> OperatorAccount | None:
    if operator_id:
        return session.get(OperatorAccount, operator_id)
    return session.scalars(
        select(OperatorAccount).where(OperatorAccount.status == "active").order_by(OperatorAccount.id)
    ).first()
