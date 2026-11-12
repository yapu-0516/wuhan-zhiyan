"""应急演练运行记录：复用情景会话、版本和运行结果，不另建孤立台账。"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import timeutil
from ..context import AppContext, not_found
from ..models import ReviewRecord, ScenarioRunRecord, ScenarioSession, ScenarioVersion
from ..schemas import DrillRunCreate, DrillRunPatch, ReviewCreate
from .events import next_id
from .workflow import create_review

PROVIDER = "local-crowd-simulator"
LIMITATIONS = [
    "人员、车辆与风险范围为轻量演示模拟，不代表专业疏散或灾害模型结果",
    "步行路线使用道路中心线近似，尚未接入真实人行道、障碍物和出口容量标定",
    "人员位置使用平面高程，未严格采样地形、桥面和建筑遮挡",
]


def drill_to_dict(row: ScenarioRunRecord) -> dict[str, Any]:
    payload = row.payload or {}
    return {
        "id": row.id,
        "scenario_session_id": row.session_id,
        "version_id": row.version_id,
        "drill_key": payload.get("drill_key", ""),
        "title": payload.get("title", row.id),
        "event_type": row.scenario_type,
        "source_event_id": payload.get("source_event_id"),
        "status": payload.get("drill_status", "running"),
        "provider": row.provider,
        "data_classification": row.data_classification,
        "parameters": payload.get("parameters", {}),
        "metrics": payload.get("metrics", {}),
        "timeline": payload.get("timeline", []),
        "frames": payload.get("frames", []),
        "summary": payload.get("summary", ""),
        "limitations": payload.get("limitations", LIMITATIONS),
        "created_at": timeutil.fmt(row.created_at),
        "updated_at": payload.get("updated_at") or timeutil.fmt(row.created_at),
    }


def create_drill_run(
    ctx: AppContext,
    session: Session,
    body: DrillRunCreate,
    now: datetime | None = None,
) -> ScenarioRunRecord:
    ts = now or timeutil.now()
    params = {
        **body.parameters,
        **({"source_event_id": body.source_event_id} if body.source_event_id else {}),
    }
    with ctx.id_lock:
        scenario_session = ScenarioSession(
            id=next_id(session, ScenarioSession.id, "SC"),
            title=body.title.strip(),
            scenario_type=body.event_type,
            state="completed" if body.status == "completed" else "running",
            parameters=params,
            messages=[],
            current_version_id=None,
            last_comparison=None,
            created_at=ts,
            updated_at=ts,
        )
        session.add(scenario_session)
        session.flush()
        version = ScenarioVersion(
            id=next_id(session, ScenarioVersion.id, "SV"),
            session_id=scenario_session.id,
            version_no=1,
            scenario_type=body.event_type,
            title=body.title.strip(),
            parameters=params,
            created_at=ts,
        )
        session.add(version)
        session.flush()
        scenario_session.current_version_id = version.id
        run = ScenarioRunRecord(
            id=next_id(session, ScenarioRunRecord.id, "DR"),
            session_id=scenario_session.id,
            version_id=version.id,
            scenario_type=body.event_type,
            provider=PROVIDER,
            data_classification="simulated",
            status="success",
            payload={
                "run_kind": "drill",
                "drill_key": body.drill_key,
                "title": body.title.strip(),
                "source_event_id": body.source_event_id,
                "parameters": body.parameters,
                "metrics": body.metrics,
                "timeline": body.timeline,
                "frames": [],
                "summary": body.summary.strip(),
                "drill_status": body.status,
                "operator": body.operator.strip() or "应急演练人员",
                "limitations": LIMITATIONS,
                "updated_at": timeutil.fmt(ts),
            },
            created_at=ts,
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        return run


def update_drill_run(
    session: Session,
    row: ScenarioRunRecord,
    body: DrillRunPatch,
    now: datetime | None = None,
) -> ScenarioRunRecord:
    if row.payload.get("run_kind") != "drill":
        raise not_found(f"演练运行 {row.id} 不存在")
    ts = now or timeutil.now()
    payload = dict(row.payload or {})
    updates = body.model_dump(exclude_unset=True)
    for key in ("parameters", "metrics", "timeline", "summary", "status"):
        if key in updates and updates[key] is not None:
            payload["parameters" if key == "parameters" else "drill_status" if key == "status" else key] = updates[key]
    if body.frame is not None:
        frames = list(payload.get("frames") or [])
        frames.append(body.frame)
        payload["frames"] = frames[-120:]
    payload["updated_at"] = timeutil.fmt(ts)
    row.payload = payload
    scenario_session = session.get(ScenarioSession, row.session_id)
    if scenario_session is not None:
        scenario_session.updated_at = ts
        scenario_session.state = (
            "completed" if payload.get("drill_status") == "completed" else "running"
        )
        if body.parameters is not None:
            scenario_session.parameters = body.parameters
    session.commit()
    session.refresh(row)
    return row


def create_drill_review(
    ctx: AppContext,
    session: Session,
    row: ScenarioRunRecord,
) -> ReviewRecord:
    existing = session.scalars(
        select(ReviewRecord).where(
            ReviewRecord.entity_type == "drill",
            ReviewRecord.entity_id == row.id,
        )
    ).first()
    if existing is not None:
        return existing
    payload = row.payload or {}
    metrics = dict(payload.get("metrics") or {})
    metrics.update(
        {
            "frame_count": len(payload.get("frames") or []),
            "timeline_count": len(payload.get("timeline") or []),
            "data_classification": row.data_classification,
        }
    )
    summary = payload.get("summary") or (
        f"演练「{payload.get('title', row.id)}」已形成模拟疏散与处置过程记录。"
    )
    findings = [
        "演练参数、版本、运行结果和过程时间线已关联保存",
        "演练结果仅用于辅助培训和流程检查，不代表专业模型结论",
    ]
    if metrics.get("peak_waiting"):
        findings.append(f"峰值排队 {metrics['peak_waiting']} 人，需检查出口组织")
    recommendations = [
        "将有效处置动作回写到同类任务模板和演练预案",
        "在有真实步行网络和出口容量数据后重新标定参数",
    ]
    return create_review(
        ctx,
        session,
        ReviewCreate(
            entity_type="drill",
            entity_id=row.id,
            status="draft",
            summary=summary,
            metrics=metrics,
            findings=findings,
            recommendations=recommendations,
        ),
    )
