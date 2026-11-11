"""ORM 模型（与 database/schema.sql 保持一致）。

时间字段均为东八区本地时间（naive datetime）。道路实时路况保存在内存（services/traffic.py），不落库。
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Event(Base):
    """城市事件（火灾 / 交通拥堵 / 建筑异常 / 内涝积水）。"""

    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)  # E0001
    event_type: Mapped[str] = mapped_column(String(16), index=True)
    name: Mapped[str] = mapped_column(String(128))
    longitude: Mapped[float] = mapped_column(Float)
    latitude: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    status: Mapped[str] = mapped_column(String(16), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)  # 发现时间
    severity: Mapped[str] = mapped_column(String(16), index=True)
    source: Mapped[str] = mapped_column(String(16))
    district: Mapped[str] = mapped_column(String(32), default="")
    address: Mapped[str] = mapped_column(String(128), default="")
    grid: Mapped[str] = mapped_column(String(16), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    building_id: Mapped[str | None] = mapped_column(String(16), index=True, nullable=True)
    road_id: Mapped[str | None] = mapped_column(String(16), index=True, nullable=True)
    task_id: Mapped[str | None] = mapped_column(String(16), nullable=True)
    evidence_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    assignee: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)  # 入库时间
    updated_at: Mapped[datetime] = mapped_column(DateTime)

    logs: Mapped[list["EventLog"]] = relationship(
        back_populates="event", cascade="all, delete-orphan", order_by="EventLog.timestamp"
    )


class EventLog(Base):
    """事件处置日志：created / status_changed / assigned / comment / ai_detected。"""

    __tablename__ = "event_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), index=True)
    action: Mapped[str] = mapped_column(String(16))
    from_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    to_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    operator: Mapped[str] = mapped_column(String(64), default="系统")
    note: Mapped[str] = mapped_column(Text, default="")
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)

    event: Mapped[Event] = relationship(back_populates="logs")


class DataAsset(Base):
    """数据资产目录（遥感 / 无人机 / 视频 / 三维 / 传感器 / 矢量）。"""

    __tablename__ = "data_assets"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)  # D0001
    name: Mapped[str] = mapped_column(String(128))
    type: Mapped[str] = mapped_column(String(16), index=True)
    time: Mapped[datetime] = mapped_column(DateTime, index=True)  # 获取时间
    status: Mapped[str] = mapped_column(String(16))
    source: Mapped[str] = mapped_column(String(64), default="")
    format: Mapped[str] = mapped_column(String(32), default="")
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    records: Mapped[int] = mapped_column(Integer, default=1)
    description: Mapped[str] = mapped_column(Text, default="")
    url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    spatial_extent: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    time_start: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    time_end: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    crs: Mapped[str] = mapped_column(String(32), default="EPSG:4326")
    quality_score: Mapped[float] = mapped_column(Float, default=0.0)
    quality_notes: Mapped[list[str]] = mapped_column(JSON, default=list)
    version: Mapped[str] = mapped_column(String(32), default="")
    analysis_status: Mapped[str] = mapped_column(String(16), default="unknown", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)


class DataValidationRecord(Base):
    """数据资源的坐标、时相和字段校验历史。"""

    __tablename__ = "data_validations"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)  # DV0001
    asset_id: Mapped[str] = mapped_column(
        ForeignKey("data_assets.id", ondelete="CASCADE"), index=True
    )
    decision: Mapped[str] = mapped_column(String(16), index=True)
    checks: Mapped[dict[str, bool]] = mapped_column(JSON, default=dict)
    quality_score: Mapped[float] = mapped_column(Float, default=0.0)
    notes: Mapped[list[str]] = mapped_column(JSON, default=list)
    operator: Mapped[str] = mapped_column(String(64), default="数据管理员")
    created_at: Mapped[datetime] = mapped_column(DateTime)


class Task(Base):
    """AI 分析任务。inputs / algorithm / result 以 JSON 保存，结构见 docs/api.md §6。"""

    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)  # T0001
    type: Mapped[str] = mapped_column(String(16), index=True)
    status: Mapped[str] = mapped_column(String(16), index=True)  # pending | running | done | failed
    origin: Mapped[str] = mapped_column(String(16), default="user")  # user | upload | demo | seed
    created_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    stage: Mapped[str] = mapped_column(String(32), default="排队中")
    file_count: Mapped[int] = mapped_column(Integer, default=0)
    inputs: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    algorithm: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    sample_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    create_event: Mapped[bool] = mapped_column(Boolean, default=True)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class MonitoringTask(Base):
    """业务监测任务；一次任务可产生多次算法运行和多个事件。"""

    __tablename__ = "monitoring_tasks"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)  # MT0001
    name: Mapped[str] = mapped_column(String(128))
    event_type: Mapped[str] = mapped_column(String(16), index=True)
    schedule_type: Mapped[str] = mapped_column(String(16), default="instant")
    status: Mapped[str] = mapped_column(String(16), index=True)
    area_name: Mapped[str] = mapped_column(String(64), default="武汉中心城区")
    bbox: Mapped[list[float]] = mapped_column(JSON, default=list)
    data_source_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    rule_config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    owner: Mapped[str] = mapped_column(String(64), default="")
    notify_targets: Mapped[list[str]] = mapped_column(JSON, default=list)
    template_key: Mapped[str | None] = mapped_column(String(32), nullable=True)
    start_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    end_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)


class MonitoringTaskTemplate(Base):
    """可复用的监测任务模板。"""

    __tablename__ = "monitoring_task_templates"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)  # TP0001
    name: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text, default="")
    event_type: Mapped[str] = mapped_column(String(16), index=True)
    schedule_type: Mapped[str] = mapped_column(String(16), default="instant")
    area_name: Mapped[str] = mapped_column(String(64), default="武汉中心城区")
    bbox: Mapped[list[float]] = mapped_column(JSON, default=list)
    data_source_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    rule_config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    owner: Mapped[str] = mapped_column(String(64), default="")
    notify_targets: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)


class TaskTemplateRevision(Base):
    """任务模板的审核后修订版本。"""

    __tablename__ = "task_template_revisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    template_id: Mapped[str] = mapped_column(
        ForeignKey("monitoring_task_templates.id", ondelete="CASCADE"), index=True
    )
    version_no: Mapped[int] = mapped_column(Integer)
    rule_config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    source_review_id: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    operator: Mapped[str] = mapped_column(String(64), default="系统管理员")
    created_at: Mapped[datetime] = mapped_column(DateTime)


class MonitoringRun(Base):
    """业务任务的一次执行，可关联一次 AI 分析作业和多个事件。"""

    __tablename__ = "monitoring_runs"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)  # MR0001
    monitoring_task_id: Mapped[str] = mapped_column(
        ForeignKey("monitoring_tasks.id", ondelete="CASCADE"), index=True
    )
    analysis_task_id: Mapped[str | None] = mapped_column(String(16), index=True, nullable=True)
    event_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(16), index=True)
    coverage: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    quality: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)


class AssessmentRecord(Base):
    """针对一个事件的研判结论与证据快照。"""

    __tablename__ = "assessments"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)  # AS0001
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), index=True)
    monitoring_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("monitoring_runs.id", ondelete="SET NULL"), index=True, nullable=True
    )
    decision: Mapped[str] = mapped_column(String(20), index=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    evidence: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    impact: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    missing_information: Mapped[list[str]] = mapped_column(JSON, default=list)
    priority: Mapped[str] = mapped_column(String(16), default="medium")
    operator: Mapped[str] = mapped_column(String(64), default="值班员")
    created_at: Mapped[datetime] = mapped_column(DateTime)


class WorkOrder(Base):
    """围绕事件或研判结论执行的具体工作，与事件状态相互独立。"""

    __tablename__ = "work_orders"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)  # WO0001
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), index=True)
    assessment_id: Mapped[str | None] = mapped_column(
        ForeignKey("assessments.id", ondelete="SET NULL"), index=True, nullable=True
    )
    scenario_run_id: Mapped[str | None] = mapped_column(String(24), nullable=True)
    title: Mapped[str] = mapped_column(String(128))
    unit: Mapped[str] = mapped_column(String(64), default="")
    assignee: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(16), index=True)
    priority: Mapped[str] = mapped_column(String(16), default="medium")
    description: Mapped[str] = mapped_column(Text, default="")
    due_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    feedback: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)


class ReviewRecord(Base):
    """任务、事件或演练的复盘记录。"""

    __tablename__ = "reviews"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)  # RV0001
    entity_type: Mapped[str] = mapped_column(String(20), index=True)
    entity_id: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(16), index=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    findings: Mapped[list[str]] = mapped_column(JSON, default=list)
    recommendations: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)


class SettlementSeries(Base):
    """接入沉降监测的建筑：位移时序 + 由 SettleWatch 算法计算的评估结果。"""

    __tablename__ = "settlement_series"

    building_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    series: Mapped[list[dict[str, Any]]] = mapped_column(JSON)  # [{date, displacement_mm}]
    rate_mm_per_month: Mapped[float] = mapped_column(Float)
    acceleration: Mapped[float] = mapped_column(Float)
    cumulative_mm: Mapped[float] = mapped_column(Float)
    risk_level: Mapped[str] = mapped_column(String(16), index=True)
    analysis: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime)


class Source(Base):
    """监测数据源（基线配置；实时吞吐由模拟器在内存中刷新）。"""

    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # S-DRONE
    name: Mapped[str] = mapped_column(String(64))
    type: Mapped[str] = mapped_column(String(16))
    icon: Mapped[str] = mapped_column(String(8))
    desc: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(8))
    devices_online: Mapped[int] = mapped_column(Integer)
    devices_total: Mapped[int] = mapped_column(Integer)
    throughput: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(16))
    coverage: Mapped[str] = mapped_column(String(64))
    last_active: Mapped[datetime] = mapped_column(DateTime)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class AppMeta(Base):
    """键值元数据（种子版本、种子时间等）。"""

    __tablename__ = "app_meta"

    key: Mapped[str] = mapped_column(String(32), primary_key=True)
    value: Mapped[str] = mapped_column(Text)


class OperatorAccount(Base):
    """演示用操作身份目录；当前版本用于署名与角色提示，不替代正式认证。"""

    __tablename__ = "operator_accounts"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)  # A0001
    name: Mapped[str] = mapped_column(String(64))
    role: Mapped[str] = mapped_column(String(24), index=True)
    organization: Mapped[str] = mapped_column(String(96))
    grid_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(16), default="active")
    contact: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)


class ResponsibilityGrid(Base):
    """责任网格与属地责任单位。"""

    __tablename__ = "responsibility_grids"

    id: Mapped[str] = mapped_column(String(24), primary_key=True)  # G-JH-01
    district: Mapped[str] = mapped_column(String(32), index=True)
    name: Mapped[str] = mapped_column(String(96))
    organization: Mapped[str] = mapped_column(String(96))
    owner: Mapped[str] = mapped_column(String(64))
    contact: Mapped[str] = mapped_column(String(64), default="")
    bbox: Mapped[list[float]] = mapped_column(JSON, default=list)
    risk_types: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime)


class EmergencyResource(Base):
    """应急资源点位的可调度能力；空间点位仍以 Poi 目录为准。"""

    __tablename__ = "emergency_resources"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)  # P0001
    name: Mapped[str] = mapped_column(String(128))
    kind: Mapped[str] = mapped_column(String(24), index=True)
    longitude: Mapped[float] = mapped_column(Float)
    latitude: Mapped[float] = mapped_column(Float)
    capability: Mapped[str] = mapped_column(String(128), default="")
    capacity: Mapped[int] = mapped_column(Integer, default=0)
    available: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="available", index=True)
    contact: Mapped[str] = mapped_column(String(64), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime)


class NotificationRecord(Base):
    """站内通知；面向演示角色和目标单位投递。"""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    target: Mapped[str] = mapped_column(String(96), default="")
    title: Mapped[str] = mapped_column(String(128))
    body: Mapped[str] = mapped_column(Text, default="")
    level: Mapped[str] = mapped_column(String(16), default="info", index=True)
    entity_type: Mapped[str] = mapped_column(String(24), default="")
    entity_id: Mapped[str] = mapped_column(String(32), default="")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, index=True)


class AuditLog(Base):
    """跨模块写操作审计；记录请求身份、对象、修改前后值和响应状态。"""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    method: Mapped[str] = mapped_column(String(12))
    path: Mapped[str] = mapped_column(String(255), index=True)
    action: Mapped[str] = mapped_column(String(24), default="api_write")
    entity_type: Mapped[str] = mapped_column(String(24), default="")
    entity_id: Mapped[str] = mapped_column(String(32), default="")
    operator_id: Mapped[str] = mapped_column(String(16), default="")
    operator_name: Mapped[str] = mapped_column(String(64), default="系统")
    role: Mapped[str] = mapped_column(String(24), default="")
    status_code: Mapped[int] = mapped_column(Integer, default=200)
    summary: Mapped[str] = mapped_column(Text, default="")
    before_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    after_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, index=True)


class ScenarioSession(Base):
    """多轮情景推演会话。"""

    __tablename__ = "scenario_sessions"

    id: Mapped[str] = mapped_column(String(24), primary_key=True)
    title: Mapped[str] = mapped_column(String(128), default="未命名情景")
    scenario_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    state: Mapped[str] = mapped_column(String(16), default="initial")
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    messages: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    current_version_id: Mapped[str | None] = mapped_column(String(24), nullable=True)
    last_comparison: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)


class ScenarioVersion(Base):
    """不可变的情景参数版本。"""

    __tablename__ = "scenario_versions"

    id: Mapped[str] = mapped_column(String(24), primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("scenario_sessions.id", ondelete="CASCADE"), index=True)
    version_no: Mapped[int] = mapped_column(Integer)
    scenario_type: Mapped[str] = mapped_column(String(16))
    title: Mapped[str] = mapped_column(String(128))
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime)


class ScenarioTemplate(Base):
    """可复用的情景假设与参数模板。"""

    __tablename__ = "scenario_templates"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)  # ST0001
    name: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text, default="")
    scenario_type: Mapped[str] = mapped_column(String(16), index=True)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)


class ScenarioTemplateRevision(Base):
    """情景模板的不可变修订版本，保留完整假设与参数。"""

    __tablename__ = "scenario_template_revisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    template_id: Mapped[str] = mapped_column(
        ForeignKey("scenario_templates.id", ondelete="CASCADE"), index=True
    )
    version_no: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text, default="")
    scenario_type: Mapped[str] = mapped_column(String(16))
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    operator: Mapped[str] = mapped_column(String(64), default="情景模板编辑员")
    created_at: Mapped[datetime] = mapped_column(DateTime)


class ScenarioResourceReservation(Base):
    """情景会话对应急资源的预留占用。"""

    __tablename__ = "scenario_resource_reservations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("scenario_sessions.id", ondelete="CASCADE"), index=True
    )
    resource_id: Mapped[str] = mapped_column(
        ForeignKey("emergency_resources.id", ondelete="CASCADE"), index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(16), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)


class ScenarioRunRecord(Base):
    """一次情景推演结果，frames 与报告输入均保存在 payload。"""

    __tablename__ = "scenario_runs"

    id: Mapped[str] = mapped_column(String(24), primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("scenario_sessions.id", ondelete="CASCADE"), index=True)
    version_id: Mapped[str] = mapped_column(ForeignKey("scenario_versions.id", ondelete="CASCADE"), index=True)
    scenario_type: Mapped[str] = mapped_column(String(16), index=True)
    provider: Mapped[str] = mapped_column(String(32))
    data_classification: Mapped[str] = mapped_column(String(24))
    status: Mapped[str] = mapped_column(String(16), default="success")
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime)
