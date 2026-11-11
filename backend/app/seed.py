"""初始种子数据（首次启动或 POST /api/demo/reset 时生成）。

原则：
- 随机性固定（random.Random(42)），时间相对"当前时刻"生成，演示数据始终是"近 7 天"；
- 所有 AI / 传感器类事件都来自**真实执行的算法**：图片证据来自示例影像的分析结果，时序类事件由
  与实时模拟器同一模型生成的历史序列（车速 / 水位 / 沉降）经算法分析得出——未检出则不生成事件；
- 事件状态由处置时间线推演到当前时刻自然得出（越久远的事件越可能已办结），日志与状态一致；
- 示例影像、模拟序列均为合成演示数据，事件描述中注明。
"""
from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

import cityeye_algo as ca
import numpy as np
from cityeye_algo import AnalysisResult
from cityeye_algo.building import SettlementThresholds, assess_settlement
from cityeye_algo.flood import WaterLevelAnalyzer
from cityeye_algo.traffic import TrafficSeriesAnalyzer
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import timeutil
from .db import Base
from .geo import ODBL, is_generic_name
from .models import (
    AppMeta,
    AuditLog,
    AssessmentRecord,
    DataAsset,
    DataValidationRecord,
    EmergencyResource,
    Event,
    MonitoringRun,
    MonitoringTask,
    MonitoringTaskTemplate,
    NotificationRecord,
    OperatorAccount,
    ReviewRecord,
    ResponsibilityGrid,
    ScenarioTemplate,
    ScenarioTemplateRevision,
    SettlementSeries,
    Source,
    Task,
    WorkOrder,
)
from .services.events import TYPE_CN, add_log, create_event, default_assignee, event_from_result
from .services.tasks import create_task

if TYPE_CHECKING:
    from .context import AppContext

log = logging.getLogger("cityeye.seed")

SEED_VERSION = "5"
DUTY = ["值班员 王磊", "值班员 张敏", "调度员 李娜", "值班员 陈刚", "调度员 赵倩"]
SYNTH = "（合成演示数据）"
LANDMARKS = {
    "黄鹤楼": (114.30538, 30.54568),
    "武汉长江大桥": (114.283457, 30.551792),
}


# ====================================================================== 入口

def seed_database(ctx: "AppContext") -> dict[str, int]:
    """清空并重建全部业务数据，返回各表记录数。"""
    Base.metadata.drop_all(ctx.engine)
    Base.metadata.create_all(ctx.engine)
    ctx.clear_generated_files()
    now = timeutil.now()
    rng = random.Random(42)
    ctx.traffic.reset(now)
    with ctx.session() as s:
        _seed_sources(s, now)
        _seed_data_assets(ctx, s, now)
        monitored = _seed_settlement(ctx, s, now, rng)
        builder = _EventBuilder(ctx, s, now, rng)
        builder.run_seed_tasks()
        builder.plan_fire()
        builder.plan_traffic()
        builder.plan_building(monitored)
        builder.plan_flood()
        n_events = builder.commit_all()
        _seed_workflow(ctx, s, now)
        s.add(AppMeta(key="seed_version", value=SEED_VERSION))
        s.add(AppMeta(key="seeded_at", value=timeutil.fmt(now) or ""))
        s.commit()
        ctx.sources.load(s)
        counts = {"events": n_events, "tasks": s.scalar(select(func.count()).select_from(Task)) or 0, "buildings_monitored": len(monitored)}
    ensure_support_data(ctx)
    ctx.invalidate_buildings()
    log.info("种子数据已生成：%s", counts)
    return counts


def is_seeded(ctx: "AppContext") -> bool:
    with ctx.session() as s:
        try:
            return s.get(AppMeta, "seed_version") is not None
        except Exception:  # noqa: BLE001 - 表不存在
            return False


def load_runtime_state(ctx: "AppContext") -> None:
    """从数据库恢复内存态（建筑风险等级、数据源基线），用于非首次启动。"""
    with ctx.session() as s:
        ctx.geo.monitoring = {r.building_id: r.risk_level for r in s.scalars(select(SettlementSeries))}
        ctx.sources.load(s)
    ctx.invalidate_buildings()


def ensure_support_data(ctx: "AppContext") -> None:
    """为已有演示库补建角色、责任网格和初始站内提醒。"""
    now = timeutil.now()
    with ctx.session() as s:
        if (s.scalar(select(func.count()).select_from(OperatorAccount)) or 0) == 0:
            s.add_all(
                [
                    OperatorAccount(
                        id="A0001", name="王磊", role="duty", organization="市城市运行管理中心",
                        grid_ids=["G-JH-01", "G-JA-01"], status="active", contact="值班席 01",
                        created_at=now, updated_at=now,
                    ),
                    OperatorAccount(
                        id="A0002", name="张敏", role="analyst", organization="市城市运行管理中心",
                        grid_ids=["G-JH-01", "G-WC-01"], status="active", contact="分析席 02",
                        created_at=now, updated_at=now,
                    ),
                    OperatorAccount(
                        id="A0003", name="李娜", role="dispatcher", organization="市城市运行管理中心",
                        grid_ids=["G-JH-01", "G-HY-01", "G-QK-01"], status="active", contact="调度席 03",
                        created_at=now, updated_at=now,
                    ),
                    OperatorAccount(
                        id="A0004", name="陈刚", role="field", organization="水务 / 属地联动处置组",
                        grid_ids=["G-WC-01", "G-HS-01"], status="active", contact="现场席位 04",
                        created_at=now, updated_at=now,
                    ),
                    OperatorAccount(
                        id="A0005", name="周宁", role="data_admin", organization="城市数据资源中心",
                        grid_ids=["G-JH-01"], status="active", contact="数据维护席",
                        created_at=now, updated_at=now,
                    ),
                    OperatorAccount(
                        id="A0006", name="刘洋", role="admin", organization="系统运行保障组",
                        grid_ids=[], status="active", contact="系统保障席",
                        created_at=now, updated_at=now,
                    ),
                ]
            )
        if (s.scalar(select(func.count()).select_from(ResponsibilityGrid)) or 0) == 0:
            districts = list(ctx.geo.region.get("event_districts") or ctx.geo.region.get("districts") or [])
            for district in districts:
                prefix = {
                    "江岸区": "JA", "江汉区": "JH", "硚口区": "QK", "汉阳区": "HY",
                    "武昌区": "WC", "洪山区": "HS", "青山区": "QS",
                }.get(district, "WH")
                points = [
                    (p["longitude"], p["latitude"])
                    for p in ctx.geo.buildings.values()
                    if p.get("district") == district
                ]
                if points:
                    bbox = [
                        min(x for x, _ in points), min(y for _, y in points),
                        max(x for x, _ in points), max(y for _, y in points),
                    ]
                else:
                    bbox = list(ctx.geo.region["bbox"])
                s.add(
                    ResponsibilityGrid(
                        id=f"G-{prefix}-01", district=district, name=f"{district}综合责任网格",
                        organization=f"{district}城市运行管理中心", owner="值班调度员",
                        contact="12345", bbox=bbox, risk_types=["fire", "traffic", "building", "flood"],
                        created_at=now,
                    )
                )
        if (s.scalar(select(func.count()).select_from(MonitoringTaskTemplate)) or 0) == 0:
            s.add_all(
                [
                    MonitoringTaskTemplate(
                        id="TP0001", name="火灾重点区域即时核查", description="影像或视频发现火情线索后立即核查。",
                        event_type="fire", schedule_type="instant", area_name="武汉中心城区",
                        bbox=list(ctx.geo.region["bbox"]), data_source_ids=["S-DRONE", "S-VIDEO"],
                        rule_config={"priority": "high"}, owner="消防救援联动组",
                        notify_targets=["消防救援指挥中心", "属地街道"], created_at=now, updated_at=now,
                    ),
                    MonitoringTaskTemplate(
                        id="TP0002", name="交通高峰拥堵周期监测", description="早晚高峰按周期分析车速和持续拥堵。",
                        event_type="traffic", schedule_type="periodic", area_name="武汉中心城区",
                        bbox=list(ctx.geo.region["bbox"]), data_source_ids=["S-TRAFFIC", "S-VIDEO"],
                        rule_config={"interval_minutes": 30, "tpi_threshold": 6.0}, owner="交通运行值班组",
                        notify_targets=["交管指挥中心"], created_at=now, updated_at=now,
                    ),
                    MonitoringTaskTemplate(
                        id="TP0003", name="建筑沉降日监测", description="对已接入沉降监测的建筑执行日尺度分析。",
                        event_type="building", schedule_type="periodic", area_name="武汉中心城区",
                        bbox=list(ctx.geo.region["bbox"]), data_source_ids=["S-IOT-SETTLE"],
                        rule_config={"interval_minutes": 1440}, owner="结构安全监测组",
                        notify_targets=["房安中心", "属地街道"], created_at=now, updated_at=now,
                    ),
                    MonitoringTaskTemplate(
                        id="TP0004", name="强降雨道路积水专项监测", description="降雨期间监测水位、雨量并核查道路积水。",
                        event_type="flood", schedule_type="periodic", area_name="武汉中心城区",
                        bbox=list(ctx.geo.region["bbox"]), data_source_ids=["S-RADAR", "S-IOT-WATER"],
                        rule_config={"interval_minutes": 15, "rainfall_mm_h": 50, "water_level_threshold_cm": 15},
                        owner="防汛值班组", notify_targets=["水务排水中心", "属地街道"],
                        created_at=now, updated_at=now,
                    ),
                ]
            )
        if (s.scalar(select(func.count()).select_from(EmergencyResource)) or 0) == 0:
            capability = {
                "hospital": ("急救床位与医疗救援", 120),
                "fire_station": ("消防车辆与救援班组", 8),
                "police": ("现场秩序与交通管控", 30),
                "school": ("临时避难与人员安置", 500),
            }
            for poi in ctx.geo.pois:
                label, capacity = capability.get(poi.get("kind", "other"), ("应急资源", 20))
                s.add(
                    EmergencyResource(
                        id=poi["id"], name=poi.get("name") or poi["id"], kind=poi.get("kind", "other"),
                        longitude=float(poi["longitude"]), latitude=float(poi["latitude"]),
                        capability=label, capacity=capacity, available=capacity,
                        status="available", contact="通过属地调度席联系",
                        notes="演示资源能力档案，实际可调度状态以现场确认为准。", updated_at=now,
                    )
                )
        s.commit()

        if (s.scalar(select(func.count()).select_from(NotificationRecord)) or 0) == 0:
            active = s.scalars(
                select(WorkOrder)
                .where(WorkOrder.status.in_(("pending", "accepted", "in_progress", "completed")))
                .order_by(WorkOrder.due_at.is_(None), WorkOrder.due_at, WorkOrder.updated_at.desc())
            ).first()
            if active is not None:
                s.add(
                    NotificationRecord(
                        target=active.unit or active.assignee or "属地责任单位",
                        title=f"待处置工单 {active.id}",
                        body=f"{active.title} 需要现场核查并及时反馈。",
                        level="warning",
                        entity_type="work_order",
                        entity_id=active.id,
                        is_read=False,
                        created_at=now,
                    )
                )
            review = s.scalars(select(ReviewRecord).order_by(ReviewRecord.created_at.desc())).first()
            if review is not None:
                s.add(
                    NotificationRecord(
                        target="防汛值班组",
                        title="复盘建议待审核",
                        body=f"{review.id} 已形成改进建议，请纳入下一次任务配置评审。",
                        level="info",
                        entity_type="review",
                        entity_id=review.id,
                        is_read=False,
                        created_at=now - timedelta(minutes=12),
                    )
                )
            s.commit()

        if (s.scalar(select(func.count()).select_from(AuditLog)) or 0) == 0:
            audit_rows = [
                AuditLog(
                    method="POST", path="/api/monitoring-tasks/MT0001/execute", action="task_execute",
                    entity_type="monitoring_task", entity_id="MT0001", operator_id="A0001",
                    operator_name="王磊", role="duty", status_code=200,
                    summary="周期监测任务启动算法运行", created_at=now - timedelta(hours=2),
                ),
                AuditLog(
                    method="PATCH", path="/api/work-orders/WO0003", action="update_api",
                    entity_type="work_order", entity_id="WO0003", operator_id="A0003",
                    operator_name="李娜", role="dispatcher", status_code=200,
                    summary="工单进入现场执行状态",
                    before_data={"status": "accepted"},
                    after_data={"status": "in_progress"},
                    created_at=now - timedelta(minutes=40),
                ),
                AuditLog(
                    method="POST", path="/api/reviews", action="create_review",
                    entity_type="review", entity_id="RV0001", operator_id="A0002",
                    operator_name="张敏", role="analyst", status_code=201,
                    summary="确认复盘结论与改进建议", created_at=now - timedelta(minutes=18),
                ),
            ]
            s.add_all(audit_rows)
            s.commit()

        if (s.scalar(select(func.count()).select_from(DataValidationRecord)) or 0) == 0:
            ready_assets = s.scalars(
                select(DataAsset).where(DataAsset.analysis_status == "ready").order_by(DataAsset.id)
            ).all()
            for index, asset in enumerate(ready_assets, 1):
                s.add(
                    DataValidationRecord(
                        id=f"DV{index:04d}",
                        asset_id=asset.id,
                        decision="pass",
                        checks={"coordinate": True, "time": True, "fields": True},
                        quality_score=asset.quality_score,
                        notes=["演示数据已完成坐标、时相与字段校验"],
                        operator="数据管理员 周宁",
                        created_at=now - timedelta(days=1),
                    )
                )
            s.commit()

        if (s.scalar(select(func.count()).select_from(ScenarioTemplate)) or 0) == 0:
            s.add_all(
                [
                    ScenarioTemplate(
                        id="ST0001", name="中心城区暴雨内涝", description="50 mm/h 降雨，持续 60 分钟，评估道路积水与人员疏散。",
                        scenario_type="flood",
                        parameters={
                            "location_name": "江汉区", "start_time": now.strftime("%Y-%m-%d %H:%M"),
                            "duration_min": 60, "rainfall_mm_h": 50, "people_count": 300,
                            "response_delay_min": 3, "available_resource_count": 4,
                        },
                        created_at=now, updated_at=now,
                    ),
                    ScenarioTemplate(
                        id="ST0002", name="主干道严重拥堵", description="严重拥堵持续 60 分钟，评估分流和恢复时间。",
                        scenario_type="traffic",
                        parameters={
                            "location_name": "中山大道", "start_time": now.strftime("%Y-%m-%d %H:%M"),
                            "duration_min": 60, "congestion_level": "severe", "traffic_cause": "交通事故",
                            "people_count": 120, "response_delay_min": 5, "available_resource_count": 3,
                        },
                        created_at=now, updated_at=now,
                    ),
                    ScenarioTemplate(
                        id="ST0003", name="重点区域中型火灾", description="危险半径 240 米，评估警戒、疏散与周边道路影响。",
                        scenario_type="fire",
                        parameters={
                            "location_name": "武昌区", "start_time": now.strftime("%Y-%m-%d %H:%M"),
                            "duration_min": 30, "fire_severity": "medium", "danger_radius_m": 240,
                            "people_count": 240, "response_delay_min": 3, "available_resource_count": 5,
                        },
                        created_at=now, updated_at=now,
                    ),
                    ScenarioTemplate(
                        id="ST0004", name="建筑沉降异常复核", description="沉降速率 4.5 mm/月，评估建筑周边警戒和人员核查。",
                        scenario_type="building",
                        parameters={
                            "location_name": "江汉区", "start_time": now.strftime("%Y-%m-%d %H:%M"),
                            "duration_min": 60, "settlement_rate_mm_month": 4.5,
                            "people_count": 120, "response_delay_min": 5, "available_resource_count": 4,
                        },
                        created_at=now, updated_at=now,
                    ),
                ]
            )
            s.commit()

        if s.get(ScenarioTemplate, "ST0004") is None:
            s.add(
                ScenarioTemplate(
                    id="ST0004",
                    name="建筑沉降异常复核",
                    description="沉降速率 4.5 mm/月，评估建筑周边警戒和人员核查。",
                    scenario_type="building",
                    parameters={
                        "location_name": "江汉区",
                        "start_time": now.strftime("%Y-%m-%d %H:%M"),
                        "duration_min": 60,
                        "settlement_rate_mm_month": 4.5,
                        "people_count": 120,
                        "response_delay_min": 5,
                        "available_resource_count": 4,
                    },
                    created_at=now,
                    updated_at=now,
                )
            )
            s.commit()

        templates_without_revision = [
            row for row in s.scalars(select(ScenarioTemplate)).all()
            if s.scalar(
                select(func.count()).select_from(ScenarioTemplateRevision).where(
                    ScenarioTemplateRevision.template_id == row.id
                )
            ) == 0
        ]
        for row in templates_without_revision:
            s.add(
                ScenarioTemplateRevision(
                    template_id=row.id,
                    version_no=1,
                    name=row.name,
                    description=row.description,
                    scenario_type=row.scenario_type,
                    parameters=row.parameters or {},
                    operator="初始模板",
                    created_at=row.created_at,
                )
            )
        s.commit()


def _seed_workflow(ctx: "AppContext", s: Session, now: datetime) -> None:
    """为最近一次已办结内涝事件建立任务、研判、工单和复盘的示例闭环。"""
    event = s.scalars(
        select(Event)
        .where(Event.event_type == "flood", Event.status == "resolved")
        .order_by(Event.timestamp.desc())
        .limit(1)
    ).first()
    if event is None:
        return
    started = event.timestamp - timedelta(minutes=35)
    task = MonitoringTask(
        id="MT0001",
        name="强降雨道路积水专项监测",
        event_type="flood",
        schedule_type="periodic",
        status="completed",
        area_name="武汉中心城区",
        bbox=ctx.geo.region["bbox"],
        data_source_ids=["S-SAT", "S-IOT-WATER"],
        rule_config={"rainfall_mm_h": 50, "water_level_threshold_cm": 15},
        owner="防汛值班组",
        notify_targets=["水务排水中心", "属地街道"],
        template_key="flood-road",
        start_at=started,
        end_at=event.updated_at,
        last_run_at=event.updated_at,
        created_at=started,
        updated_at=event.updated_at,
    )
    run = MonitoringRun(
        id="MR0001",
        monitoring_task_id=task.id,
        analysis_task_id=event.task_id,
        event_ids=[event.id],
        status="completed",
        coverage={"bbox": ctx.geo.region["bbox"], "window_minutes": 120},
        quality={"data_completeness": 0.92, "event_count": 1},
        started_at=started,
        finished_at=event.updated_at,
        created_at=started,
    )
    assessment = AssessmentRecord(
        id="AS0001",
        event_id=event.id,
        monitoring_run_id=run.id,
        decision="confirmed",
        summary=f"结合积水时序与空间位置，确认「{event.name}」为有效积水事件。",
        evidence=[{"kind": "event", "id": event.id, "url": event.evidence_url}],
        impact={"district": event.district, "road_id": event.road_id, "risk_level": event.severity},
        missing_information=[],
        priority=event.severity,
        operator="值班员 王磊",
        created_at=event.timestamp + timedelta(minutes=8),
    )
    unit = default_assignee(event.event_type, event.district)
    first_verified = event.updated_at
    first_completed = first_verified - timedelta(minutes=5)
    second_verified = event.updated_at
    second_completed = second_verified - timedelta(minutes=8)
    orders = [
        WorkOrder(
            id="WO0001",
            event_id=event.id,
            assessment_id=assessment.id,
            title="核验积水范围与道路通行条件",
            unit=unit,
            assignee=unit,
            status="verified",
            priority=event.severity,
            description="现场复核积水边界、雨箅子状态和车辆通行条件。",
            feedback=[
                {
                    "at": timeutil.fmt(assessment.created_at + timedelta(minutes=2)),
                    "operator": unit,
                    "action": "status_changed",
                    "from": "pending",
                    "to": "accepted",
                    "note": "责任单位已接单",
                },
                {
                    "at": timeutil.fmt(assessment.created_at + timedelta(minutes=4)),
                    "operator": unit,
                    "action": "status_changed",
                    "from": "accepted",
                    "to": "in_progress",
                    "note": "核查人员出发",
                },
                {
                    "at": timeutil.fmt(first_completed),
                    "operator": unit,
                    "action": "status_changed",
                    "from": "in_progress",
                    "to": "completed",
                    "note": "现场范围核查完成",
                },
                {
                    "at": timeutil.fmt(first_verified),
                    "operator": "值班复核员",
                    "action": "status_changed",
                    "from": "completed",
                    "to": "verified",
                    "note": "证据与反馈复核通过",
                },
            ],
            due_at=assessment.created_at + timedelta(minutes=120),
            created_at=assessment.created_at,
            updated_at=event.updated_at,
        ),
        WorkOrder(
            id="WO0002",
            event_id=event.id,
            assessment_id=assessment.id,
            title="积水抽排与雨箅子清理",
            unit=unit,
            assignee=unit,
            status="verified",
            priority=event.severity,
            description="清理堵塞雨水口并安排移动泵车抽排。",
            feedback=[
                {
                    "at": timeutil.fmt(assessment.created_at + timedelta(minutes=3)),
                    "operator": unit,
                    "action": "status_changed",
                    "from": "pending",
                    "to": "accepted",
                    "note": "抽排班组已接单",
                },
                {
                    "at": timeutil.fmt(assessment.created_at + timedelta(minutes=6)),
                    "operator": unit,
                    "action": "status_changed",
                    "from": "accepted",
                    "to": "in_progress",
                    "note": "移动泵车到场",
                },
                {
                    "at": timeutil.fmt(second_completed),
                    "operator": unit,
                    "action": "status_changed",
                    "from": "in_progress",
                    "to": "completed",
                    "note": "积水抽排完成",
                },
                {
                    "at": timeutil.fmt(second_verified),
                    "operator": "值班复核员",
                    "action": "status_changed",
                    "from": "completed",
                    "to": "verified",
                    "note": "水位消退，道路恢复通行",
                },
            ],
            due_at=assessment.created_at + timedelta(minutes=120),
            created_at=assessment.created_at,
            updated_at=event.updated_at,
        ),
    ]
    review = ReviewRecord(
        id="RV0001",
        entity_type="event",
        entity_id=event.id,
        status="confirmed",
        summary="发现、核查、抽排和复核流程完整；数据覆盖满足演示要求。",
        metrics={"response_min": 8, "resolve_min": max(1, int((event.updated_at - event.timestamp).total_seconds() / 60))},
        findings=["现场反馈与水位序列方向一致", "雨箅子堵塞是主要局部积水原因"],
        recommendations=["降雨前增加重点路段雨水口巡检"],
        created_at=now,
        updated_at=now,
    )
    s.add(task)
    s.flush()
    s.add(run)
    s.flush()
    s.add(assessment)
    s.flush()
    s.add_all(orders)
    s.add(review)
    s.commit()

    active_event = s.scalars(
        select(Event)
        .where(Event.status.in_(("pending", "monitoring", "processing")))
        .order_by(Event.timestamp.desc())
        .limit(1)
    ).first()
    if active_event is None:
        return
    active_started = active_event.timestamp - timedelta(minutes=12)
    active_task = MonitoringTask(
        id="MT0002",
        name=f"{TYPE_CN[active_event.event_type]}即时核查",
        event_type=active_event.event_type,
        schedule_type="instant",
        status="completed",
        area_name=active_event.district,
        bbox=ctx.geo.region["bbox"],
        data_source_ids=["S-VIDEO", "S-IOT-WATER"] if active_event.event_type == "flood" else ["S-VIDEO"],
        rule_config={"priority": active_event.severity},
        owner="联合值班组",
        notify_targets=[default_assignee(active_event.event_type, active_event.district)],
        template_key=f"{active_event.event_type}-quick-check",
        start_at=active_started,
        end_at=active_event.timestamp,
        last_run_at=active_event.timestamp,
        created_at=active_started,
        updated_at=active_event.timestamp,
    )
    active_run = MonitoringRun(
        id="MR0002",
        monitoring_task_id=active_task.id,
        analysis_task_id=active_event.task_id,
        event_ids=[active_event.id],
        status="completed",
        coverage={"district": active_event.district, "window_minutes": 20},
        quality={"data_completeness": 0.86, "event_count": 1},
        started_at=active_started,
        finished_at=active_event.timestamp,
        created_at=active_started,
    )
    active_assessment = AssessmentRecord(
        id="AS0002",
        event_id=active_event.id,
        monitoring_run_id=active_run.id,
        decision="confirmed",
        summary=f"初步研判确认「{active_event.name}」需要现场核查。",
        evidence=[{"kind": "event", "id": active_event.id, "url": active_event.evidence_url}],
        impact={"district": active_event.district, "risk_level": active_event.severity},
        missing_information=["等待现场边界与受影响对象反馈"],
        priority=active_event.severity,
        operator="调度员 赵倩",
        created_at=active_event.timestamp + timedelta(minutes=3),
    )
    active_order = WorkOrder(
        id="WO0003",
        event_id=active_event.id,
        assessment_id=active_assessment.id,
        title="现场核查与影响范围确认",
        unit=default_assignee(active_event.event_type, active_event.district),
        assignee=default_assignee(active_event.event_type, active_event.district),
        status="in_progress",
        priority=active_event.severity,
        description="核查现场状态、受影响对象、道路通行条件和所需增援资源。",
        due_at=active_assessment.created_at + timedelta(minutes=90),
        feedback=[
            {
                "at": timeutil.fmt(active_assessment.created_at + timedelta(minutes=2)),
                "operator": default_assignee(active_event.event_type, active_event.district),
                "action": "status_changed",
                "from": "pending",
                "to": "accepted",
                "note": "责任单位已接单",
            },
            {
                "at": timeutil.fmt(active_assessment.created_at + timedelta(minutes=6)),
                "operator": default_assignee(active_event.event_type, active_event.district),
                "action": "status_changed",
                "from": "accepted",
                "to": "in_progress",
                "note": "处置力量已出发，现场信息待回传",
            }
        ],
        created_at=active_assessment.created_at,
        updated_at=timeutil.now(),
    )
    s.add(active_task)
    s.flush()
    s.add(active_run)
    s.flush()
    s.add(active_assessment)
    s.flush()
    s.add(active_order)
    s.commit()


# ====================================================================== 数据源 / 数据资产

def _seed_sources(s: Session, now: datetime) -> None:
    rows = [
        ("S-DRONE", "无人机巡检", "drone", "🚁", "8 架多旋翼巡检无人机按航线巡航，回传可见光 / 热红外影像", "采集中", 6, 8, 124, "帧/分钟", "七城区重点航段"),
        ("S-SAT", "卫星遥感", "satellite", "🛰️", "高分二号 / 资源三号 / Sentinel-2 过境影像，用于变化检测", "在线", 3, 3, 2, "景/天", "武汉中心城区"),
        ("S-VIDEO", "视频监控", "video", "📹", "公安天网与交通卡口高清视频，AI 抽帧分析", "在线", 1124, 1180, 1124, "路", "主干道与重点区域"),
        ("S-IOT-WATER", "积水监测", "sensor", "🌊", "下穿通道与低洼路段超声波液位计 + 雨量计，5 分钟上报", "在线", 46, 48, 552, "条/小时", "易涝点 48 处"),
        ("S-IOT-SETTLE", "结构安全监测", "sensor", "🏗️", "高层建筑静力水准仪 / GNSS 沉降监测，日解算", "在线", 152, 160, 152, "条/小时", "重点建筑 40 栋"),
        ("S-TRAFFIC", "交通流检测", "sensor", "🚦", "地磁 / 微波车检器，车速与流量 2 分钟聚合", "在线", 84, 88, 2140, "车次/分钟", "主干路网 93.6 km"),
        ("S-CITIZEN", "市民上报", "other", "🙋", "12345 热线、武汉城市留言板与随手拍工单接入", "在线", 1, 1, 3, "件/小时", "全市"),
        ("S-RADAR", "气象雷达 QPE", "other", "🌧️", "天气雷达定量降水估测，接入后用于内涝提前预警", "待接入", 0, 1, 0, "幅/6分钟", "武汉市"),
    ]
    for i, (sid, name, typ, icon, desc, status, online, total, thr, unit, cov) in enumerate(rows):
        s.add(Source(id=sid, name=name, type=typ, icon=icon, desc=desc, status=status, devices_online=online, devices_total=total,
                     throughput=thr, unit=unit, coverage=cov, last_active=now - timedelta(seconds=30 * i), sort_order=i))
    s.commit()


def _seed_data_assets(ctx: "AppContext", s: Session, now: datetime) -> None:
    geo_dir, samples = ctx.settings.geo_dir, ctx.settings.samples_dir

    def size_of(*paths: Path) -> int:
        return sum(p.stat().st_size for p in paths if p.exists())

    def sample_files(prefix: str, suffixes: tuple[str, ...]) -> list[Path]:
        d = samples / prefix
        return sorted(p for p in d.glob("*") if p.suffix in suffixes and "preview" not in p.name) if d.exists() else []

    imgs = sample_files("fire", (".jpg",)) + sample_files("flood", (".jpg",)) + sample_files("traffic", (".jpg",))
    pairs = sample_files("building", (".jpg",))
    tcsv, fcsv, bcsv = sample_files("traffic", (".csv",)), sample_files("flood", (".csv",)), sample_files("building", (".csv",))
    n_b, n_r, n_p = len(ctx.geo.buildings), len(ctx.geo.roads), len(ctx.geo.pois)
    catalog = "演示目录条目，未附带原始数据文件"
    rows = [
        ("武汉中心城区建筑概览", "矢量数据", now - timedelta(days=1, hours=3), "已入库", "OpenStreetMap / 武汉建筑楼层数据", "GeoJSON",
         size_of(geo_dir / "buildings.geojson"), n_b, f"{n_b} 栋真实建筑轮廓，含高度 / 层数 / 类别；{ODBL}", "/api/buildings"),
        ("中心城区主次干路网（OpenStreetMap）", "矢量数据", now - timedelta(days=1, hours=3), "已入库", "OpenStreetMap", "GeoJSON",
         size_of(geo_dir / "roads.geojson"), n_r, f"{n_r} 条主次干路，含等级与限速；{ODBL}", "/api/roads"),
        ("应急资源点位（医院 / 派出所 / 学校）", "矢量数据", now - timedelta(days=1, hours=2), "已入库", "OpenStreetMap", "JSON",
         size_of(geo_dir / "pois.json"), n_p, f"{n_p} 个应急资源点；{ODBL}", "/api/pois"),
        ("中心城区建筑白模 LOD1", "三维模型", now - timedelta(days=1), "已入库", "OSM 轮廓按高度拉伸", "GeoJSON / Cesium",
         size_of(geo_dir / "buildings.geojson"), n_b, "中心城区概览与按区精细图层，前端 Cesium 按需构建", "/api/buildings"),
        ("高分二号 0.8 m 融合影像", "遥感影像", now - timedelta(days=2, hours=5), "待接入", "高分二号卫星", "GeoTIFF",
         2_576_980_378, 1, f"0.8 m 全色 + 3.2 m 多光谱融合；{catalog}", None),
        ("Sentinel-2 L2A 多光谱影像", "遥感影像", now - timedelta(days=4, hours=2), "待接入", "Sentinel-2", "SAFE",
         1_181_116_006, 1, f"10 m 多光谱，用于水体 / 植被指数；{catalog}", None),
        ("无人机巡检影像（示例）", "无人机影像", now - timedelta(hours=6), "已入库", "无人机巡检", "JPEG",
         size_of(*imgs), len(imgs), "火情 / 积水 / 路况俯拍示例影像" + SYNTH, ctx.url_for(imgs[0]) if imgs else None),
        ("前后时相变化检测影像对（示例）", "遥感影像", now - timedelta(days=1, hours=8), "已入库", "卫星 / 无人机", "JPEG",
         size_of(*pairs), len(pairs), "建筑坍塌 / 新增临建 / 无变化对照" + SYNTH, ctx.url_for(pairs[0]) if pairs else None),
        ("交通检测器车速时序（示例）", "传感器数据", now - timedelta(hours=9), "已入库", "交通流检测", "CSV",
         size_of(*tcsv), len(tcsv), "解放大道全天 5 分钟车速、沿江大道事故时段车速" + SYNTH, ctx.url_for(tcsv[0]) if tcsv else None),
        ("积水液位与雨量时序（示例）", "传感器数据", now - timedelta(days=3), "已入库", "积水监测", "CSV",
         size_of(*fcsv), len(fcsv), "暴雨 / 小雨过程 5 分钟水位与雨量" + SYNTH, ctx.url_for(fcsv[0]) if fcsv else None),
        ("建筑沉降监测时序（示例）", "传感器数据", now - timedelta(hours=20), "已入库", "结构安全监测", "CSV",
         size_of(*bcsv), len(bcsv), "稳定 / 持续沉降 / 加速沉降三类 180 天位移序列" + SYNTH, ctx.url_for(bcsv[0]) if bcsv else None),
        ("江汉路商圈视频流", "视频流", now - timedelta(minutes=12), "采集中", "视频监控", "RTSP / H.265",
         0, 24, f"24 路商圈高清视频，AI 抽帧分析；{catalog}", None),
    ]
    rows.sort(key=lambda r: r[2])
    for i, (name, typ, t, status, src, fmt, size, rec, desc, url) in enumerate(rows, 1):
        if status == "已入库":
            analysis_status = "ready"
            quality_score = 94.0 if typ in ("矢量数据", "三维模型") else 88.0
            quality_notes = ["空间与时相口径已登记", "字段清单可用于演示分析"]
        elif status == "采集中":
            analysis_status = "pending"
            quality_score = 72.0
            quality_notes = ["实时流可用，尚未完成稳定性抽检"]
        else:
            analysis_status = "unavailable"
            quality_score = 0.0
            quality_notes = ["原始文件未接入，当前仅保留目录信息"]
        time_start = now - (
            timedelta(days=365) if typ in ("矢量数据", "三维模型")
            else timedelta(days=1) if typ == "传感器数据"
            else timedelta(hours=6) if typ == "无人机影像"
            else timedelta(hours=24)
        )
        s.add(DataAsset(id=f"D{i:04d}", name=name, type=typ, time=t, status=status, source=src, format=fmt, size_bytes=int(size),
                        records=int(rec), description=desc, url=url,
                        spatial_extent={"label": "武汉中心城区", "bbox": list(ctx.geo.region["bbox"])},
                        time_start=time_start, time_end=None if typ == "视频流" else t,
                        crs="EPSG:4326", quality_score=quality_score, quality_notes=quality_notes,
                        version=f"{t:%Y.%m.%d}", analysis_status=analysis_status, created_at=t))
    s.commit()


# ====================================================================== 沉降监测

def _seed_settlement(ctx: "AppContext", s: Session, now: datetime, rng: random.Random) -> list[str]:
    """从主要城区选取最高 40 栋建筑接入沉降监测，生成 180 天位移序列并用 SettleWatch 评估风险。

    预设剖面（加速 / 持续 / 稳定）只决定合成序列的形态；风险等级完全由算法计算。
    风险剖面优先放在无名建筑上，避免对具名建筑作出安全暗示。
    """
    event_districts = set(ctx.geo.region.get("event_districts") or ctx.geo.region.get("districts") or [])
    cands = [p for p in ctx.geo.buildings.values() if p.get("district") in event_districts and p.get("height", 0) >= 20]
    cands.sort(key=lambda p: (-p["height"], p["id"]))
    chosen = []
    for district in sorted(event_districts):
        chosen.extend([p for p in cands if p.get("district") == district][:5])
    seen = {p["id"] for p in chosen}
    chosen.extend(p for p in cands if p["id"] not in seen)
    chosen = chosen[:40]
    generic = [p["id"] for p in chosen if is_generic_name(p.get("name", ""))]
    accel = set(generic[:2])
    steady = set(generic[2:7])
    days = [(now - timedelta(days=179 - i)).date() for i in range(180)]
    t = np.arange(180.0)
    th = SettlementThresholds()
    for p in chosen:
        bid = p["id"]
        nrng = np.random.default_rng(int(bid[3:] if bid.startswith("WHB") else bid[1:]) + 7)
        if bid in accel:
            y = -rng.uniform(0.8, 1.2) / 30.44 * t - rng.uniform(0.0007, 0.0009) * np.clip(t - 100, 0, None) ** 2
        elif bid in steady:
            y = -rng.uniform(2.3, 3.4) / 30.44 * t
        else:
            y = -rng.uniform(0.05, 0.9) / 30.44 * t + rng.uniform(0.2, 0.6) * np.sin(2 * np.pi * (t + rng.uniform(0, 365)) / 365)
        y = y + nrng.normal(0, rng.uniform(0.15, 0.3), 180)
        if rng.random() < 0.15:
            y[int(nrng.integers(20, 170))] -= rng.uniform(2.5, 4.0)  # 偶发测量粗差
        rep = assess_settlement(days, y, th)
        s.add(SettlementSeries(
            building_id=bid,
            series=[{"date": d.isoformat(), "displacement_mm": round(float(v), 2)} for d, v in zip(days, y)],
            rate_mm_per_month=rep.rate_mm_per_month, acceleration=rep.acceleration, cumulative_mm=rep.cumulative_mm,
            risk_level=rep.risk_level, analysis=rep.analysis, updated_at=now,
        ))
    s.commit()
    ctx.geo.monitoring = {r.building_id: r.risk_level for r in s.scalars(select(SettlementSeries))}
    return [p["id"] for p in chosen]


# ====================================================================== 事件

@dataclass
class _Spec:
    ts: datetime
    event_type: str
    source: str
    lon: float
    lat: float
    result: AnalysisResult | None = None
    algorithm: str = ""
    input_kind: str = "image"
    input_label: str = ""
    evidence_src: Path | None = None
    evidence_url: str | None = None
    task_id: str | None = None
    building_id: str | None = None
    road_id: str | None = None
    name: str = ""
    severity: str = "medium"
    description: str = ""
    confidence: float = 1.0
    hold: str | None = None  # 状态推演到此为止（如沉降预警长期处于监测 / 处置中）
    false_alarm: str | None = None
    feedback: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


class _EventBuilder:
    def __init__(self, ctx: "AppContext", s: Session, now: datetime, rng: random.Random) -> None:
        self.ctx, self.s, self.now, self.rng = ctx, s, now, rng
        self.specs: list[_Spec] = []
        self.sample_runs: dict[str, tuple[Any, AnalysisResult]] = {}
        self.task_results: dict[str, tuple[Task, AnalysisResult]] = {}
        self.geo = ctx.geo
        self.event_districts = set(ctx.geo.region.get("event_districts") or ctx.geo.region.get("districts") or [])
        self.arterials = [
            road for road in ctx.geo.roads if road.highway in ("motorway", "trunk", "primary", "secondary")
        ]

    # ------------------------------------------------------------------ 工具
    def at(self, days_ago: int, hour: float, jitter_min: float = 0) -> datetime:
        base = timeutil.start_of_day(self.now) - timedelta(days=days_ago) + timedelta(hours=hour)
        return (base + timedelta(minutes=self.rng.uniform(-jitter_min, jitter_min))).replace(microsecond=0)

    def past(self, ts: datetime) -> bool:
        return ts <= self.now - timedelta(minutes=2)

    def sample_run(self, sample_id: str) -> tuple[Any, AnalysisResult] | None:
        """示例数据只分析一次，标注图作为多个历史事件的共享证据（evidence/S-<id>_*.jpg）。"""
        if sample_id not in self.sample_runs:
            smp = self.ctx.samples.by_id.get(sample_id)
            if smp is None:
                return None
            self.sample_runs[sample_id] = ca.run(smp["type"], self.ctx.samples.paths(smp), self.ctx.evidence_dir, f"S-{sample_id}")
        return self.sample_runs[sample_id]

    def pick_building(self, categories: tuple[str, ...], min_area: float = 300) -> dict[str, Any]:
        cands = [p for p in self.geo.buildings.values() if p.get("category") in categories and p.get("area_m2", 0) >= min_area
                 and p.get("district") in self.event_districts]
        cands = cands or list(self.geo.buildings.values())
        return self.rng.choice(sorted(cands, key=lambda p: p["id"]))

    def road_point(self, names: tuple[str, ...]) -> tuple[Any, float, float] | None:
        roads = sorted(self.geo.roads_named(*names), key=lambda r: r.id) if names else []
        roads = roads or self.arterials or list(self.geo.roads)
        if not roads:
            return None
        road = self.rng.choice(roads)
        lon, lat = self.geo.random_point_on_road(self.rng, road)
        return road, lon, lat

    def add_from_sample(self, sample_id: str, ts: datetime, source: str, lon: float, lat: float, **kw: Any) -> None:
        run = self.sample_run(sample_id)
        if run is None or not self.past(ts):
            return
        analyzer, result = run
        if not result.detected:  # 诚实原则：算法未检出则不生成事件
            return
        art = result.primary_artifact
        self.specs.append(_Spec(ts, analyzer.meta.type, source, lon, lat, result=result, algorithm=analyzer.meta.name,
                                input_kind=analyzer.meta.input_kind, evidence_url=self.ctx.url_for(art.path) if art else None,
                                input_label=f"输入：{self.ctx.samples.by_id[sample_id]['name']}{SYNTH}", **kw))

    # ------------------------------------------------------------------ 种子任务
    def run_seed_tasks(self) -> None:
        """在示例数据上真实运行算法，生成若干已完成的 AI 分析任务（含 1 个反例）。"""
        plan = [
            ("flood-02", 3, 15.6, True), ("flood-01", 2, 10.2, False), ("building-01", 1, 9.5, True),
            ("traffic-01", 0, -5.0, False), ("building-05", 0, -3.2, False), ("fire-05", 0, -1.6, False),
            ("fire-01", 0, -1.1, True), ("traffic-03", 0, -0.5, True),
        ]
        specs = []
        for sid, days_ago, hour, make_event in plan:
            ts = self.at(days_ago, hour) if hour >= 0 else (self.now + timedelta(hours=hour)).replace(microsecond=0)
            specs.append((ts, sid, make_event))
        for ts, sid, make_event in sorted(specs):
            smp = self.ctx.samples.by_id.get(sid)
            if smp is None:
                continue
            paths = self.ctx.samples.paths(smp)
            lon, lat = smp["longitude"], smp["latitude"]
            t = create_task(self.ctx, self.s, event_type=smp["type"], paths=paths,
                            inputs=[{"name": p.name, "url": self.ctx.url_for(p)} for p in paths],
                            longitude=lon, latitude=lat, create_event=make_event, sample_id=sid, origin="seed", created_at=ts)
            analyzer, result = ca.run(t.type, paths, self.ctx.results_dir, t.id)
            res = result.to_dict(self.ctx.url_for)
            res["event_ids"] = []
            t.result, t.status, t.progress, t.stage = res, "done", 100, "完成"
            t.started_at = ts
            t.finished_at = ts + timedelta(seconds=max(1, round(float(result.metrics.get("elapsed_ms", 200)) / 1000 + 2)))
            self.s.commit()
            self.task_results[t.id] = (t, result)
            if make_event and result.detected:
                art = result.primary_artifact
                self.specs.append(_Spec(t.finished_at, t.type, "ai_task", lon, lat, result=result, algorithm=analyzer.meta.name,
                                        input_kind=analyzer.meta.input_kind, evidence_src=art.path if art else None, task_id=t.id,
                                        input_label=f"输入：示例数据「{smp['name']}」{SYNTH}，任务 {t.id}"))

    # ------------------------------------------------------------------ 火灾
    def plan_fire(self) -> None:
        r = self.rng
        for sid, days_ago, hour, src in (("fire-02", 6, 15.3, "drone"), ("fire-01", 4, 11.2, "video"), ("fire-02", 2, 19.6, "drone"),
                                         ("fire-03", 1, 23.4, "drone"), ("fire-01", 0, -0.6, "drone")):
            b = self.pick_building(("commercial", "residential", "office", "other"))
            ts = self.at(days_ago, hour, 20) if hour >= 0 else (self.now + timedelta(hours=hour)).replace(microsecond=0)
            self.add_from_sample(sid, ts, src, b["longitude"], b["latitude"], building_id=b["id"],
                                 feedback=r.choice(["明火已扑灭，过火面积约 30 m²，无人员伤亡", "屋顶杂物起火，已扑灭并清理现场", "电气线路短路引燃，已断电扑灭"]))
        b = self.pick_building(("commercial",))
        ts = self.at(1, 12.4, 30)
        self.specs.append(_Spec(ts, "fire", "citizen", b["longitude"], b["latitude"], building_id=b["id"], name=f"{self.geo.building_label(b)}附近冒烟",
                                severity="medium", confidence=1.0, description="市民通过 12345 热线反映楼顶有浓烟冒出。",
                                false_alarm="现场核查为餐饮店排烟管道油烟，非火情，已告知商户整改"))
        b = self.pick_building(("residential",))
        ts = self.at(4, 21.1, 30)
        self.specs.append(_Spec(ts, "fire", "citizen", b["longitude"], b["latitude"], building_id=b["id"], name=f"{self.geo.building_label(b)}电动车充电起火",
                                severity="high", confidence=1.0, description="市民随手拍上报：楼道内电动车充电时起火，有烟雾。",
                                feedback="楼道电动车电池起火，已扑灭，疏散居民 23 人，无人员伤亡"))

    # ------------------------------------------------------------------ 交通
    def plan_traffic(self) -> None:
        if not self.geo.roads:
            return  # 无路网数据时跳过交通事件
        tr = self.ctx.traffic
        ranked = sorted(
            self.arterials or self.geo.roads,
            key=lambda rd: (tr.roads[rd.id].sensitivity, rd.length_m),
            reverse=True,
        )
        arterials = []
        for district in sorted(self.event_districts):
            arterials.extend([road for road in ranked if self.geo.road_district.get(road.id) == district][:4])
        seen = {road.id for road in arterials}
        arterials.extend(road for road in ranked if road.id not in seen)
        arterials = arterials[:32] or self.geo.roads[:8]
        analyzer = TrafficSeriesAnalyzer()
        r = self.rng
        for d in range(6, -1, -1):
            weekend = (self.now - timedelta(days=d)).weekday() >= 5
            peaks = [(10.2 if weekend else 8.35, 1), (17.95, 1 if weekend else 2)]
            for hour, n in peaks:
                for road in r.sample(arterials, k=min(n, len(arterials))):
                    ts = self.at(d, hour, 18)
                    if self.past(ts):
                        self._traffic_spec(analyzer, road, ts, None, video=r.random() < 0.25)
        incidents = [(self.at(5, 14.4, 30), "追尾事故"), (self.at(3, 11.0, 30), "施工占道"), (self.at(1, 15.2, 30), "车辆故障抛锚"),
                     ((self.now - timedelta(minutes=6)).replace(microsecond=0), "两车剐蹭")]  # 最后一起刚发生，处于待核查
        for ts, cause in incidents:
            road = r.choice(arterials)
            if self.past(ts):
                self._traffic_spec(analyzer, road, ts, (ts - timedelta(minutes=28), ts + timedelta(minutes=20), 0.32), cause=cause)

    def _traffic_spec(self, analyzer: TrafficSeriesAnalyzer, road: Any, ts: datetime, incident: Any, video: bool = False, cause: str = "") -> None:
        st = self.ctx.traffic.roads[road.id]
        times, speeds = self.ctx.traffic.synth_series(road.id, ts, minutes=120, step_min=2, incident=incident, seed=int(ts.timestamp()) % 100000)
        lon, lat = self.geo.random_point_on_road(self.rng, road)
        if video:
            run = self.sample_run("traffic-03")
            if run and run[1].detected:
                self.add_from_sample("traffic-03", ts, "video", lon, lat, road_id=road.id, feedback="交警到场疏导，车流已恢复")
            return
        chart = self.ctx.evidence_dir / f"seed-traffic-{road.id}-{ts:%m%d%H%M}.png"
        res = analyzer.analyze_series(times, speeds, chart, free_flow_kmh=st.free_flow, road_name=road.base_name)
        if not res.detected:
            return
        fb = f"现场为{cause}，已清障疏导" if cause else self.rng.choice(["高峰车流集中，已加派警力疏导", "路口信号配时已临时优化", "已引导车辆绕行"])
        self.specs.append(_Spec(ts, "traffic", "sensor", lon, lat, result=res, algorithm=analyzer.meta.name, input_kind="csv",
                                evidence_src=chart, road_id=road.id, feedback=fb,
                                input_label=f"输入：{road.base_name}交通流检测器 2 分钟车速序列（近 2 小时，模拟数据）"))

    # ------------------------------------------------------------------ 建筑
    def plan_building(self, monitored: list[str]) -> None:
        r = self.rng
        sw = ca.BY_KEY["building.series"]
        rows = {x.building_id: x for x in self.s.scalars(select(SettlementSeries).where(SettlementSeries.building_id.in_(monitored)))}
        for bid in sorted(monitored):
            row = rows.get(bid)
            if row is None or row.risk_level == "normal":
                continue
            ts = self.at(r.randint(1, 4), 6.0, 10)  # 每日 06:00 沉降日报解算
            pts = [p for p in row.series if p["date"] <= ts.date().isoformat()]
            csv = self.ctx.results_dir / f"seed-settle-{bid}.csv"
            csv.write_text("date,displacement_mm\n" + "\n".join(f"{p['date']},{p['displacement_mm']}" for p in pts), encoding="utf-8")
            res = sw.analyze([csv], self.ctx.evidence_dir, f"seed-settle-{bid}")
            csv.unlink()
            if not res.detected:
                continue
            b = self.geo.buildings[bid]
            self.specs.append(_Spec(ts, "building", "sensor", b["longitude"], b["latitude"], result=res, algorithm=sw.meta.name, input_kind="csv",
                                    evidence_src=res.primary_artifact.path if res.primary_artifact else None, building_id=bid,
                                    hold="processing" if res.level == "warning" else "monitoring",
                                    input_label=f"输入：该建筑 {len(pts)} 天沉降监测序列（模拟数据）"))
        b = self.pick_building(("residential", "other"))
        self.add_from_sample("building-01", self.at(5, 10.5, 30), "satellite", b["longitude"], b["latitude"], building_id=b["id"],
                             feedback="核查为违规搭建彩钢瓦临建及旧房拆除，已移交城管执法")
        for days_ago, hour, title, desc, sev, hold in (
            (2, 9.8, "外墙瓷砖脱落", "市民反映外墙瓷砖成片脱落，坠落至人行道，存在安全隐患。", "medium", None),
            (0, 7.5, "老旧住宅墙体开裂", "居民反映承重墙出现斜向裂缝并持续扩展，宽度约 3 mm。", "high", "monitoring"),
        ):
            b = self.pick_building(("residential",))
            ts = self.at(days_ago, hour, 30)
            if self.past(ts):
                self.specs.append(_Spec(ts, "building", "citizen", b["longitude"], b["latitude"], building_id=b["id"],
                                        name=f"{self.geo.building_label(b)}{title}", severity=sev, description=desc, hold=hold,
                                        feedback="已拉设警戒线并清理坠落物，督促物业维修" if hold is None else ""))
        ts = (self.now - timedelta(minutes=11)).replace(microsecond=0)
        lon, lat = LANDMARKS["武汉长江大桥"]
        self.specs.append(_Spec(
            ts, "building", "citizen", lon, lat, name="武汉长江大桥桥面伸缩缝异常",
            severity="medium", description="巡查人员上报：桥面伸缩缝附近出现轻微异响，已进入持续监测。",
            hold="monitoring",
        ))

    # ------------------------------------------------------------------ 内涝
    def plan_flood(self) -> None:
        r = self.rng
        storm_day = 3
        start = self.at(storm_day, 13.0)
        k = np.arange(72)
        rain = 7.0 / (1 + 0.09 * np.where(k < 22, (22 - k) / 0.4, (k - 22) / 0.6)) ** 1.6
        rain = np.where((k < 4) | (k > 50), 0.0, rain)
        aq = WaterLevelAnalyzer()
        for i in range(7):
            pt = self.road_point(())
            if pt is None:
                break
            road, lon, lat = pt
            coef, lag = r.uniform(0.75, 1.35), r.randint(3, 7)
            nrng = np.random.default_rng(100 + i)
            level = np.zeros(len(k))
            for j in range(1, len(k)):
                drain = min(0.07 * level[j - 1] + 0.35, 1.6) if level[j - 1] > 0 else 0.0
                level[j] = max(0.0, level[j - 1] + coef * (rain[j - lag] if j >= lag else 0.0) * (1 + nrng.normal(0, 0.06)) - drain)
            over = np.nonzero(level >= 15.0)[0]
            if len(over) == 0:
                continue  # 该点未超阈值：不生成事件
            cut = min(len(k) - 1, int(over[0]) + 1)
            times = [start + timedelta(minutes=5 * j) for j in range(cut + 1)]
            ts = times[-1]
            if not self.past(ts):
                continue
            chart = self.ctx.evidence_dir / f"seed-flood-{i}.png"
            res = aq.analyze_series(times, level[: cut + 1], chart, rain=rain[: cut + 1], site_name=f"{road.base_name}积水点")
            if res.detected:
                self.specs.append(_Spec(ts, "flood", "sensor", lon, lat, result=res, algorithm=aq.meta.name, input_kind="csv",
                                        evidence_src=chart, road_id=road.id, feedback="泵车抽排 2 小时，积水已退",
                                        input_label=f"输入：{road.base_name}积水点液位计与雨量计 5 分钟序列（模拟数据）"))
        for hour, text in ((14.6, "路口积水没过脚踝，车辆涉水缓行"), (15.1, "雨水箅子堵塞，路面大面积积水")):
            pt = self.road_point(())
            ts = self.at(storm_day, hour, 10)
            if pt and self.past(ts):
                road, lon, lat = pt
                self.specs.append(_Spec(ts, "flood", "citizen", lon, lat, road_id=road.id, name=f"{road.base_name}路面积水",
                                        severity="medium", description=f"市民上报：{text}。", feedback="已清掏雨水箅子，积水消退"))
        pt = self.road_point(())
        if pt:
            road, lon, lat = pt
            self.add_from_sample("flood-02", self.at(storm_day, 15.4, 5), "drone", lon, lat, road_id=road.id, feedback="交警封闭车道，泵车抽排后恢复通行")
        pt = self.road_point(())
        ts = (self.now - timedelta(minutes=4)).replace(microsecond=0)
        if pt:
            road, lon, lat = pt
            self.specs.append(_Spec(ts, "flood", "citizen", lon, lat, road_id=road.id, name=f"{road.base_name}管网冒溢",
                                    severity="low", description="市民上报：检查井冒水，路面局部积水约 5 cm。"))

    # ------------------------------------------------------------------ 生命周期推演
    def _steps(self, sp: _Spec, unit: str) -> list[tuple[datetime, str, str | None, str, str]]:
        """返回 [(时间, 动作, 目标状态, 操作人, 备注)]，之后按当前时刻截断。"""
        r = self.rng
        duty = r.choice(DUTY)
        m = lambda lo, hi: timedelta(minutes=r.uniform(lo, hi))  # noqa: E731
        t = sp.ts
        if sp.false_alarm:
            return [(t + m(6, 18), "status", "resolved", duty, sp.false_alarm)]
        steps: list[tuple[datetime, str, str | None, str, str]] = []
        if sp.event_type in ("fire", "traffic"):
            t1 = t + m(2, 9)
            op = "系统自动派单" if sp.source in ("sensor", "video", "drone") and r.random() < 0.4 else duty
            verb = "联动 119 指挥中心" if sp.event_type == "fire" else "安排警力疏导"
            steps += [(t1, "status", "processing", op, f"已派单至{unit}，{verb}"), (t1, "assign", None, op, unit)]
            dur = (45, 150) if sp.event_type == "fire" else (20, 75)
            t2 = t1 + m(*dur)
            if sp.feedback:
                steps.append((t1 + (t2 - t1) * 0.7, "comment", None, unit, f"现场反馈：{sp.feedback}"))
            steps.append((t2, "status", "resolved", duty, "处置完毕，现场恢复正常，已办结"))
        elif sp.event_type == "flood":
            t1 = t + m(3, 12)
            steps.append((t1, "status", "monitoring", duty, "已调取周边视频复核，持续监测水位"))
            t2 = t1 + m(8, 30)
            steps += [(t2, "status", "processing", duty, f"已通知{unit}出动泵车抽排"), (t2, "assign", None, duty, unit)]
            t3 = t2 + m(60, 220)
            if sp.feedback:
                steps.append((t2 + (t3 - t2) * 0.6, "comment", None, unit, f"现场反馈：{sp.feedback}"))
            steps.append((t3, "status", "resolved", duty, "积水已退至 5 cm 以下，道路恢复通行"))
        else:
            t1 = t + m(5, 40)
            steps.append((t1, "status", "monitoring", duty, "纳入重点监测，观测频次加密至每日 2 次"))
            t2 = t1 + m(60 * 6, 60 * 30)
            steps += [(t2, "status", "processing", duty, f"已通知{unit}组织现场安全鉴定"), (t2, "assign", None, duty, unit)]
            t3 = t2 + m(60 * 20, 60 * 60)
            if sp.feedback:
                steps.append((t2 + (t3 - t2) * 0.5, "comment", None, unit, f"现场反馈：{sp.feedback}"))
            steps.append((t3, "status", "resolved", duty, "鉴定 / 整改完成，已办结"))
        if sp.hold:  # 长期监测类事件：只推演到 hold 状态，不含现场反馈
            order = ("pending", "monitoring", "processing", "resolved")
            steps = [x for x in steps if x[1] == "assign" or (x[2] is not None and order.index(x[2]) <= order.index(sp.hold))]
        return steps

    def commit_all(self) -> int:
        """按发现时间顺序入库（编号随时间递增），并推演处置流程至当前时刻。"""
        n = 0
        for sp in sorted(self.specs, key=lambda x: x.ts):
            if sp.result is not None:
                e = event_from_result(
                    self.ctx, self.s, event_type=sp.event_type, algorithm_name=sp.algorithm, result=sp.result,
                    longitude=sp.lon, latitude=sp.lat, source=sp.source, input_kind=sp.input_kind, input_label=sp.input_label,
                    task_id=sp.task_id, timestamp=sp.ts, evidence_src=sp.evidence_src, evidence_url=sp.evidence_url,
                    building_id=sp.building_id, road_id=sp.road_id,
                    creator=f"AI 分析任务 {sp.task_id}" if sp.task_id else "系统",
                )
            else:
                e = create_event(
                    self.ctx, self.s, event_type=sp.event_type, name=sp.name, longitude=sp.lon, latitude=sp.lat,
                    severity=sp.severity, source=sp.source, confidence=sp.confidence, description=sp.description,
                    timestamp=sp.ts, building_id=sp.building_id, road_id=sp.road_id, creator="市民上报（12345 热线）",
                    metrics={"reporter": "市民", "channel": "12345 热线"},
                )
            if sp.task_id and sp.task_id in self.task_results:
                t, _ = self.task_results[sp.task_id]
                t.result = {**(t.result or {}), "event_ids": [*(t.result or {}).get("event_ids", []), e.id]}
            unit = default_assignee(e.event_type, e.district)
            for when, action, to, op, note in self._steps(sp, unit):
                if when > self.now - timedelta(minutes=1):
                    break
                when = when.replace(microsecond=0)
                if action == "status":
                    add_log(self.s, e.id, "status_changed", op, note, when, e.status, to)
                    e.status = to  # type: ignore[assignment]
                elif action == "assign":
                    e.assignee = note
                    add_log(self.s, e.id, "assigned", op, f"指派至 {note}", when)
                else:
                    add_log(self.s, e.id, "comment", op, note, when)
                e.updated_at = when
            self.s.commit()
            n += 1
        return n
