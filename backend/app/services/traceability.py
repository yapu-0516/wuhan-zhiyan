"""跨业务对象关系图：把数据、任务、运行、事件、研判、情景、工单与复盘串成可追溯链路。"""
from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from .. import timeutil
from ..models import (
    AssessmentRecord,
    DataAsset,
    Event,
    MonitoringRun,
    MonitoringTask,
    ReviewRecord,
    ScenarioRunRecord,
    ScenarioSession,
    Task,
    WorkOrder,
)

if TYPE_CHECKING:
    from ..context import AppContext

NODE_META = {
    "data_asset": {"label": "数据资源", "stage": "数据", "color": "#5eead4"},
    "monitoring_task": {"label": "监测任务", "stage": "任务", "color": "#67c6df"},
    "monitoring_run": {"label": "运行记录", "stage": "运行", "color": "#4fa3d1"},
    "analysis_task": {"label": "分析作业", "stage": "运行", "color": "#7b9cff"},
    "event": {"label": "风险事件", "stage": "事件", "color": "#f0c050"},
    "assessment": {"label": "风险研判", "stage": "研判", "color": "#e9a45c"},
    "scenario_session": {"label": "情景会话", "stage": "推演", "color": "#9b8fff"},
    "scenario_run": {"label": "推演结果", "stage": "推演", "color": "#c084fc"},
    "work_order": {"label": "处置工单", "stage": "处置", "color": "#72c39a"},
    "review": {"label": "复盘记录", "stage": "复盘", "color": "#94a3b8"},
    "drill": {"label": "演练记录", "stage": "复盘", "color": "#94a3b8"},
}


def _node_id(entity_type: str, entity_id: str) -> str:
    return f"{entity_type}:{entity_id}"


def _add_node(
    nodes: dict[str, dict[str, Any]],
    entity_type: str,
    entity_id: str | None,
    label: str,
    status: str = "",
    timestamp: Any = None,
    summary: str = "",
    details: dict[str, Any] | None = None,
) -> str | None:
    if not entity_id:
        return None
    key = _node_id(entity_type, str(entity_id))
    if key not in nodes:
        meta = NODE_META.get(entity_type, {"label": entity_type, "stage": "其他", "color": "#92969a"})
        nodes[key] = {
            "id": key,
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "label": label,
            "display_name": meta["label"],
            "stage": meta["stage"],
            "color": meta["color"],
            "status": status,
            "timestamp": timeutil.fmt(timestamp) if hasattr(timestamp, "strftime") else (timestamp or ""),
            "summary": summary,
            "details": details or {},
        }
    return key


def _add_edge(
    edges: dict[str, dict[str, str]],
    source: str | None,
    target: str | None,
    relation: str,
) -> None:
    if not source or not target or source == target:
        return
    key = f"{source}|{target}|{relation}"
    edges.setdefault(
        key,
        {"id": key, "source": source, "target": target, "relation": relation},
    )


def build_traceability_graph(
    ctx: "AppContext",
    *,
    entity_type: str | None = None,
    entity_id: str | None = None,
    limit: int = 240,
) -> dict[str, Any]:
    """构建业务对象图；可按任一对象做双向邻接子图。"""
    with ctx.session() as s:
        assets = s.scalars(select(DataAsset).order_by(DataAsset.created_at.desc()).limit(500)).all()
        tasks = s.scalars(select(MonitoringTask).order_by(MonitoringTask.updated_at.desc()).limit(500)).all()
        runs = s.scalars(select(MonitoringRun).order_by(MonitoringRun.created_at.desc()).limit(1000)).all()
        analyses = s.scalars(select(Task).order_by(Task.created_at.desc()).limit(1000)).all()
        events = s.scalars(select(Event).order_by(Event.timestamp.desc()).limit(2000)).all()
        assessments = s.scalars(
            select(AssessmentRecord).order_by(AssessmentRecord.created_at.desc()).limit(1000)
        ).all()
        sessions = s.scalars(
            select(ScenarioSession).order_by(ScenarioSession.updated_at.desc()).limit(500)
        ).all()
        scenario_runs = s.scalars(
            select(ScenarioRunRecord).order_by(ScenarioRunRecord.created_at.desc()).limit(500)
        ).all()
        orders = s.scalars(select(WorkOrder).order_by(WorkOrder.updated_at.desc()).limit(1000)).all()
        reviews = s.scalars(select(ReviewRecord).order_by(ReviewRecord.updated_at.desc()).limit(500)).all()

    nodes: dict[str, dict[str, Any]] = {}
    edges: dict[str, dict[str, str]] = {}

    for row in assets:
        _add_node(
            nodes, "data_asset", row.id, row.name, row.analysis_status, row.created_at,
            row.description, {"type": row.type, "quality_score": row.quality_score, "version": row.version},
        )
    for row in tasks:
        _add_node(
            nodes, "monitoring_task", row.id, row.name, row.status, row.updated_at,
            f"{row.area_name} · {row.event_type}", {"event_type": row.event_type, "owner": row.owner},
        )
        for asset_id in row.data_source_ids or []:
            if asset_id.startswith("D"):
                _add_edge(edges, _node_id("data_asset", asset_id), _node_id("monitoring_task", row.id), "绑定数据")
    for row in runs:
        _add_node(
            nodes, "monitoring_run", row.id, row.id, row.status, row.created_at,
            f"覆盖 {len(row.event_ids or [])} 个事件",
            {"coverage": row.coverage or {}, "quality": row.quality or {}},
        )
        _add_edge(edges, _node_id("monitoring_task", row.monitoring_task_id), _node_id("monitoring_run", row.id), "执行")
        _add_edge(edges, _node_id("monitoring_run", row.id), _node_id("analysis_task", row.analysis_task_id or ""), "调用算法")
        for event_id in row.event_ids or []:
            _add_edge(edges, _node_id("monitoring_run", row.id), _node_id("event", event_id), "产出事件")
    for row in analyses:
        _add_node(
            nodes, "analysis_task", row.id, f"{row.type} 分析 {row.id}", row.status, row.created_at,
            row.stage, {"origin": row.origin, "progress": row.progress},
        )
    for row in events:
        _add_node(
            nodes, "event", row.id, row.name, row.status, row.timestamp,
            row.description or row.address, {"event_type": row.event_type, "severity": row.severity},
        )
        _add_edge(edges, _node_id("analysis_task", row.task_id or ""), _node_id("event", row.id), "检出事发现")
    for row in assessments:
        _add_node(
            nodes, "assessment", row.id, f"{row.decision} · {row.id}", row.decision, row.created_at,
            row.summary, {"priority": row.priority, "operator": row.operator},
        )
        _add_edge(edges, _node_id("event", row.event_id), _node_id("assessment", row.id), "形成研判")
        _add_edge(
            edges,
            _node_id("monitoring_run", row.monitoring_run_id or ""),
            _node_id("assessment", row.id),
            "提供证据",
        )
    for row in sessions:
        _add_node(
            nodes, "scenario_session", row.id, row.title, row.state, row.updated_at,
            f"{row.scenario_type or '未定类型'} · {len(row.messages or [])} 条对话",
            {"parameters": row.parameters or {}},
        )
        source_event_id = (row.parameters or {}).get("source_event_id")
        _add_edge(edges, _node_id("event", str(source_event_id or "")), _node_id("scenario_session", row.id), "创建推演")
    for row in scenario_runs:
        _add_node(
            nodes, "scenario_run", row.id, row.payload.get("variant_label") or f"{row.scenario_type} 推演",
            row.status, row.created_at, row.payload.get("summary", ""),
            {"data_classification": row.data_classification, "provider": row.provider},
        )
        _add_edge(edges, _node_id("scenario_session", row.session_id), _node_id("scenario_run", row.id), "运行")
    for row in orders:
        _add_node(
            nodes, "work_order", row.id, row.title, row.status, row.updated_at,
            row.description, {"unit": row.unit, "priority": row.priority, "assignee": row.assignee},
        )
        _add_edge(edges, _node_id("event", row.event_id), _node_id("work_order", row.id), "生成工单")
        _add_edge(edges, _node_id("assessment", row.assessment_id or ""), _node_id("work_order", row.id), "依据研判")
        _add_edge(edges, _node_id("scenario_run", row.scenario_run_id or ""), _node_id("work_order", row.id), "采纳方案")
    for row in reviews:
        _add_node(
            nodes, "review", row.id, f"复盘 {row.entity_id}", row.status, row.updated_at,
            row.summary, {"metrics": row.metrics or {}, "entity_type": row.entity_type},
        )
        source_type = {
            "event": "event",
            "monitoring_task": "monitoring_task",
            "drill": "drill",
        }.get(row.entity_type, row.entity_type)
        if source_type == "drill":
            _add_node(
                nodes, "drill", row.entity_id, f"演练 {row.entity_id}", row.status, row.updated_at,
                "演练记录", {"entity_type": row.entity_type},
            )
        _add_edge(edges, _node_id(source_type, row.entity_id), _node_id("review", row.id), "形成复盘")

    selected_ids: set[str] | None = None
    root_id = ""
    if entity_type and entity_id:
        root_id = _node_id(entity_type, entity_id)
        if root_id not in nodes:
            return {
                "generated_at": timeutil.fmt(timeutil.now()),
                "root": {"entity_type": entity_type, "entity_id": entity_id},
                "nodes": [],
                "edges": [],
                "stats": {"nodes": 0, "edges": 0, "truncated": False},
            }
        adjacency: dict[str, list[str]] = {}
        for edge in edges.values():
            adjacency.setdefault(edge["source"], []).append(edge["target"])
            adjacency.setdefault(edge["target"], []).append(edge["source"])
        selected_ids = {root_id}
        queue = deque([root_id])
        while queue and len(selected_ids) < limit:
            current = queue.popleft()
            for neighbor in adjacency.get(current, []):
                if neighbor not in selected_ids:
                    selected_ids.add(neighbor)
                    queue.append(neighbor)
                    if len(selected_ids) >= limit:
                        break
    elif len(nodes) > limit:
        selected_ids = {
            item["id"]
            for item in sorted(
                nodes.values(),
                key=lambda value: (value.get("timestamp") or "", value["id"]),
                reverse=True,
            )[:limit]
        }

    if selected_ids is not None:
        visible_nodes = [node for key, node in nodes.items() if key in selected_ids]
        visible_edges = [
            edge for edge in edges.values()
            if edge["source"] in selected_ids and edge["target"] in selected_ids
        ]
    else:
        visible_nodes = list(nodes.values())
        visible_edges = list(edges.values())
    visible_nodes.sort(
        key=lambda item: (
            list(NODE_META).index(item["entity_type"]) if item["entity_type"] in NODE_META else 99,
            item.get("timestamp") or "",
        )
    )
    return {
        "generated_at": timeutil.fmt(timeutil.now()),
        "root": {"entity_type": entity_type or "", "entity_id": entity_id or ""},
        "nodes": visible_nodes,
        "edges": visible_edges,
        "stats": {
            "nodes": len(visible_nodes),
            "edges": len(visible_edges),
            "available_nodes": len(nodes),
            "available_edges": len(edges),
            "truncated": len(visible_nodes) < len(nodes),
        },
    }
