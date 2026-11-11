"""请求 / 响应模型（字段与 docs/api.md 一一对应；响应模型同时用于 /docs 文档与输出校验）。"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

EventType = Literal["fire", "traffic", "building", "flood"]
EventStatus = Literal["pending", "monitoring", "processing", "resolved"]
Severity = Literal["low", "medium", "high", "critical"]
EventSource = Literal["drone", "satellite", "video", "sensor", "citizen", "ai_task"]
TrafficLevel = Literal["smooth", "basic", "light", "moderate", "heavy"]
RiskLevel = Literal["normal", "watch", "warning"]
TaskStatus = Literal["prototype", "pending", "running", "done", "failed"]
LogAction = Literal["created", "status_changed", "assigned", "comment", "ai_detected"]
MonitoringTaskStatus = Literal["draft", "scheduled", "running", "completed", "failed"]
ScheduleType = Literal["instant", "periodic", "special", "drill"]
MonitoringRunStatus = Literal["pending", "running", "completed", "failed"]
AssessmentDecision = Literal["candidate", "needs_review", "confirmed", "false_alarm"]
WorkOrderStatus = Literal["pending", "accepted", "in_progress", "completed", "verified", "rejected", "cancelled"]
ReviewEntityType = Literal["event", "monitoring_task", "drill"]
ReviewStatus = Literal["draft", "confirmed"]
DataAnalysisStatus = Literal["ready", "pending", "unavailable", "unknown"]
DataValidationDecision = Literal["pass", "needs_repair", "reject"]
OperatorRole = Literal["duty", "analyst", "dispatcher", "field", "data_admin", "admin"]
NotificationLevel = Literal["info", "success", "warning", "critical"]
Metric = float | int | str


# ------------------------------------------------------------------ 请求体

class EventCreate(BaseModel):
    event_type: EventType
    name: str = Field(min_length=1, max_length=128)
    longitude: float = Field(ge=-180, le=180)
    latitude: float = Field(ge=-90, le=90)
    severity: Severity = "medium"
    description: str = Field(default="", max_length=2000)
    source: EventSource = "citizen"
    confidence: float = Field(default=1.0, ge=0, le=1)


class EventPatch(BaseModel):
    status: EventStatus | None = None
    assignee: str | None = Field(default=None, max_length=64)
    operator: str | None = Field(default=None, max_length=64)
    note: str | None = Field(default=None, max_length=2000)


class CandidateMergeCreate(BaseModel):
    primary_event_id: str
    related_event_id: str
    note: str = Field(default="", max_length=2000)
    operator: str = Field(default="值班员", max_length=64)


class TaskCreate(BaseModel):
    type: str
    fileCount: int = 0
    sample_id: str | None = None
    longitude: float | None = Field(default=None, ge=-180, le=180)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    create_event: bool = True


class MonitoringTaskCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    event_type: EventType
    schedule_type: ScheduleType = "instant"
    area_name: str = Field(default="武汉中心城区", max_length=64)
    bbox: list[float] = Field(default_factory=list, min_length=0, max_length=4)
    data_source_ids: list[str] = Field(default_factory=list)
    rule_config: dict[str, Any] = Field(default_factory=dict)
    owner: str = Field(default="", max_length=64)
    notify_targets: list[str] = Field(default_factory=list)
    template_key: str | None = Field(default=None, max_length=32)
    start_at: datetime | None = None
    end_at: datetime | None = None
    next_run_at: datetime | None = None


class MonitoringTaskPatch(BaseModel):
    status: MonitoringTaskStatus | None = None
    owner: str | None = Field(default=None, max_length=64)
    rule_config: dict[str, Any] | None = None
    next_run_at: datetime | None = None


class MonitoringTaskTemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str = Field(default="", max_length=1000)
    event_type: EventType
    schedule_type: ScheduleType = "instant"
    area_name: str = Field(default="武汉中心城区", max_length=64)
    bbox: list[float] = Field(default_factory=list, max_length=4)
    data_source_ids: list[str] = Field(default_factory=list)
    rule_config: dict[str, Any] = Field(default_factory=dict)
    owner: str = Field(default="", max_length=64)
    notify_targets: list[str] = Field(default_factory=list)


class MonitoringTaskTemplateOut(MonitoringTaskTemplateCreate):
    id: str
    created_at: str
    updated_at: str


class MonitoringTaskTemplatePatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=1000)
    schedule_type: ScheduleType | None = None
    area_name: str | None = Field(default=None, max_length=64)
    bbox: list[float] | None = Field(default=None, min_length=0, max_length=4)
    data_source_ids: list[str] | None = None
    rule_config: dict[str, Any] | None = None
    owner: str | None = Field(default=None, max_length=64)
    notify_targets: list[str] | None = None


class MonitoringRunCreate(BaseModel):
    monitoring_task_id: str
    analysis_task_id: str | None = None
    event_ids: list[str] = Field(default_factory=list)
    status: MonitoringRunStatus = "pending"
    coverage: dict[str, Any] = Field(default_factory=dict)
    quality: dict[str, Any] = Field(default_factory=dict)
    failure_reason: str | None = Field(default=None, max_length=2000)
    started_at: datetime | None = None
    finished_at: datetime | None = None


class MonitoringTaskExecute(BaseModel):
    sample_id: str | None = None


class AssessmentCreate(BaseModel):
    event_id: str
    monitoring_run_id: str | None = None
    decision: AssessmentDecision
    summary: str = Field(default="", max_length=4000)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    impact: dict[str, Any] = Field(default_factory=dict)
    missing_information: list[str] = Field(default_factory=list)
    priority: Severity = "medium"
    operator: str = Field(default="值班员", max_length=64)


class WorkOrderCreate(BaseModel):
    event_id: str
    assessment_id: str | None = None
    scenario_run_id: str | None = None
    title: str = Field(min_length=1, max_length=128)
    unit: str = Field(default="", max_length=64)
    assignee: str = Field(default="", max_length=64)
    priority: Severity = "medium"
    description: str = Field(default="", max_length=4000)
    due_at: datetime | None = None


class WorkOrderPatch(BaseModel):
    status: WorkOrderStatus | None = None
    assignee: str | None = Field(default=None, max_length=64)
    operator: str = Field(default="值班员", max_length=64)
    note: str = Field(default="", max_length=2000)
    feedback: dict[str, Any] | None = None


class WorkOrderFeedbackAssessmentCreate(BaseModel):
    summary: str = Field(default="", max_length=4000)
    operator: str = Field(default="现场处置人员", max_length=64)


class WorkOrderResourceUseCreate(BaseModel):
    resource_id: str
    quantity: int = Field(default=1, ge=1, le=1000)
    note: str = Field(default="", max_length=2000)
    operator: str = Field(default="现场处置人员", max_length=64)


class ReviewCreate(BaseModel):
    entity_type: ReviewEntityType
    entity_id: str = Field(min_length=1, max_length=32)
    status: ReviewStatus = "draft"
    summary: str = Field(default="", max_length=4000)
    metrics: dict[str, Any] = Field(default_factory=dict)
    findings: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class ReviewUpdate(BaseModel):
    status: ReviewStatus | None = None
    summary: str | None = Field(default=None, max_length=4000)
    metrics: dict[str, Any] | None = None
    findings: list[str] | None = None
    recommendations: list[str] | None = None


class TaskTemplateApply(BaseModel):
    template_id: str
    rule_config: dict[str, Any] = Field(default_factory=dict)
    operator: str = Field(default="系统管理员", max_length=64)


class TaskTemplateRevisionOut(BaseModel):
    id: int
    template_id: str
    version_no: int
    rule_config: dict[str, Any]
    source_review_id: str | None
    operator: str
    created_at: str


class ReviewDraftOut(BaseModel):
    entity_type: ReviewEntityType
    entity_id: str
    summary: str
    metrics: dict[str, Any]
    findings: list[str]
    recommendations: list[str]
    timeline: list[dict[str, Any]]


class ScenarioRequest(BaseModel):
    scenario: Literal["fire", "traffic", "building", "flood", "random"] = "random"


class ScenarioTemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str = Field(default="", max_length=1000)
    scenario_type: Literal["flood", "traffic", "fire", "building"]
    parameters: dict[str, Any] = Field(default_factory=dict)


class ScenarioTemplateOut(ScenarioTemplateCreate):
    id: str
    created_at: str
    updated_at: str


class ScenarioTemplatePatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=1000)
    scenario_type: Literal["flood", "traffic", "fire", "building"] | None = None
    parameters: dict[str, Any] | None = None
    operator: str = Field(default="情景模板编辑员", max_length=64)


class ScenarioTemplateRevisionOut(BaseModel):
    id: int
    template_id: str
    version_no: int
    name: str
    description: str
    scenario_type: Literal["flood", "traffic", "fire", "building"]
    parameters: dict[str, Any]
    operator: str
    created_at: str


class ScenarioResourceSelection(BaseModel):
    resource_ids: list[str] = Field(default_factory=list, max_length=20)


class ScenarioActionIn(BaseModel):
    title: str = Field(min_length=1, max_length=128)
    unit: str = Field(default="", max_length=64)
    assignee: str = Field(default="", max_length=64)
    priority: Severity = "medium"
    description: str = Field(default="", max_length=4000)


class ScenarioDispatchIn(BaseModel):
    event_id: str
    assessment_id: str | None = None
    actions: list[ScenarioActionIn] = Field(default_factory=list)


# ------------------------------------------------------------------ 响应体

class HealthOut(BaseModel):
    status: str
    time: str


class CityEventOut(BaseModel):
    id: str
    event_type: EventType
    name: str
    longitude: float
    latitude: float
    confidence: float
    status: EventStatus
    timestamp: str
    severity: Severity
    source: EventSource
    district: str
    address: str
    grid: str
    description: str
    building_id: str | None = None
    road_id: str | None = None
    task_id: str | None = None
    evidence_url: str | None = None
    metrics: dict[str, Any]
    assignee: str | None = None
    updated_at: str


class CandidateMergeOut(BaseModel):
    primary: CityEventOut
    merged: CityEventOut


class MonitoringTaskOut(BaseModel):
    id: str
    name: str
    event_type: EventType
    schedule_type: ScheduleType
    status: MonitoringTaskStatus
    area_name: str
    bbox: list[float]
    data_source_ids: list[str]
    rule_config: dict[str, Any]
    owner: str
    notify_targets: list[str]
    template_key: str | None
    start_at: str | None
    end_at: str | None
    next_run_at: str | None
    last_run_at: str | None
    created_at: str
    updated_at: str


class MonitoringRunOut(BaseModel):
    id: str
    monitoring_task_id: str
    analysis_task_id: str | None
    event_ids: list[str]
    status: MonitoringRunStatus
    coverage: dict[str, Any]
    quality: dict[str, Any]
    failure_reason: str | None
    started_at: str | None
    finished_at: str | None
    created_at: str


class NearbyBuildingOut(BaseModel):
    id: str
    name: str
    category: str
    distance_m: float
    risk_level: str


class NearbyRoadOut(BaseModel):
    id: str
    name: str
    highway: str
    distance_m: float


class NearbyPoiOut(BaseModel):
    id: str
    name: str
    kind: str
    distance_m: float


class AssessmentContextOut(BaseModel):
    event_id: str
    longitude: float
    latitude: float
    district: str
    grid: str
    radius_m: float
    buildings: list[NearbyBuildingOut]
    roads: list[NearbyRoadOut]
    pois: list[NearbyPoiOut]


class AssessmentOut(BaseModel):
    id: str
    event_id: str
    monitoring_run_id: str | None
    decision: AssessmentDecision
    summary: str
    evidence: list[dict[str, Any]]
    impact: dict[str, Any]
    missing_information: list[str]
    priority: Severity
    operator: str
    created_at: str


class WorkOrderSlaOut(BaseModel):
    accepted_at: str | None
    started_at: str | None
    completed_at: str | None
    verified_at: str | None
    response_min: int | None
    execution_min: int | None
    review_min: int | None
    elapsed_min: int
    remaining_min: int | None
    overdue: bool


class WorkOrderOut(BaseModel):
    id: str
    event_id: str
    assessment_id: str | None
    scenario_run_id: str | None
    title: str
    unit: str
    assignee: str
    status: WorkOrderStatus
    priority: Severity
    description: str
    due_at: str | None
    feedback: list[dict[str, Any]]
    sla: WorkOrderSlaOut
    created_at: str
    updated_at: str


class AccountOut(BaseModel):
    id: str
    name: str
    role: OperatorRole
    organization: str
    grid_ids: list[str]
    status: Literal["active", "inactive"]
    contact: str
    created_at: str
    updated_at: str


class ResponsibilityGridOut(BaseModel):
    id: str
    district: str
    name: str
    organization: str
    owner: str
    contact: str
    bbox: list[float]
    risk_types: list[str]
    created_at: str


class ResponsibilityGridPatch(BaseModel):
    organization: str | None = Field(default=None, max_length=96)
    owner: str | None = Field(default=None, max_length=64)
    contact: str | None = Field(default=None, max_length=64)
    risk_types: list[str] | None = None
    bbox: list[float] | None = Field(default=None, min_length=0, max_length=4)


class EmergencyResourceOut(BaseModel):
    id: str
    name: str
    kind: str
    longitude: float
    latitude: float
    capability: str
    capacity: int
    available: int
    status: Literal["available", "limited", "unavailable"]
    contact: str
    notes: str
    updated_at: str


class EmergencyResourcePatch(BaseModel):
    capability: str | None = Field(default=None, max_length=128)
    capacity: int | None = Field(default=None, ge=0, le=1_000_000)
    available: int | None = Field(default=None, ge=0, le=1_000_000)
    status: Literal["available", "limited", "unavailable"] | None = None
    contact: str | None = Field(default=None, max_length=64)
    notes: str | None = Field(default=None, max_length=2000)


class NotificationOut(BaseModel):
    id: int
    target: str
    title: str
    body: str
    level: NotificationLevel
    entity_type: str
    entity_id: str
    is_read: bool
    created_at: str


class AuditLogOut(BaseModel):
    id: int
    method: str
    path: str
    action: str
    entity_type: str
    entity_id: str
    operator_id: str
    operator_name: str
    role: str
    status_code: int
    summary: str
    before_data: dict[str, Any]
    after_data: dict[str, Any]
    created_at: str


class SlaTrendPointOut(BaseModel):
    date: str
    total: int
    verified: int
    overdue: int
    avg_response_min: float | None
    avg_execution_min: float | None


class SlaSummaryOut(BaseModel):
    total_orders: int
    active_orders: int
    overdue_orders: int
    verified_orders: int
    avg_response_min: float | None
    avg_execution_min: float | None
    avg_review_min: float | None
    by_unit: list[dict[str, Any]]
    by_priority: list[dict[str, Any]]
    by_scenario: list[dict[str, Any]]
    trend: list[SlaTrendPointOut]
    orders: list[WorkOrderOut]


class ServiceStatusOut(BaseModel):
    database: str
    simulator_enabled: bool
    workflow_interval_sec: float
    task_pacing_sec: float
    max_upload_mb: float
    work_order_max_attachment_mb: float
    task_counts: dict[str, int]
    run_counts: dict[str, int]
    overdue_orders: int
    unread_notifications: int
    data_counts: dict[str, int]
    algorithms: list[dict[str, Any]]


class RuntimeConfigPatch(BaseModel):
    task_pacing_sec: float | None = Field(default=None, ge=0, le=10)
    workflow_interval_sec: float | None = Field(default=None, ge=5, le=3600)
    max_upload_mb: float | None = Field(default=None, ge=1, le=500)
    work_order_max_attachment_mb: float | None = Field(default=None, ge=1, le=2048)


class ReviewStatsOut(BaseModel):
    confirmed: int
    draft: int
    by_entity_type: list[dict[str, Any]]


class ReviewOut(BaseModel):
    id: str
    entity_type: ReviewEntityType
    entity_id: str
    status: ReviewStatus
    summary: str
    metrics: dict[str, Any]
    findings: list[str]
    recommendations: list[str]
    created_at: str
    updated_at: str


class EventLogOut(BaseModel):
    id: int
    event_id: str
    action: LogAction
    from_status: EventStatus | None
    to_status: EventStatus | None
    operator: str
    note: str
    timestamp: str


class SettlementPoint(BaseModel):
    date: str
    displacement_mm: float


class BuildingMonitoringOut(BaseModel):
    series: list[SettlementPoint]
    rate_mm_per_month: float
    acceleration: float
    cumulative_mm: float
    risk_level: RiskLevel
    analysis: str


class BuildingDetailOut(BaseModel):
    properties: dict[str, Any]
    monitoring: BuildingMonitoringOut | None
    events: list[CityEventOut]


class SpatialFeaturePatch(BaseModel):
    properties: dict[str, Any] = Field(default_factory=dict)
    geometry: dict[str, Any] | None = None


class SpatialFeatureOut(BaseModel):
    entity_type: Literal["building", "road"]
    entity_id: str
    geometry: dict[str, Any]
    properties: dict[str, Any]


class PoiOut(BaseModel):
    id: str
    name: str
    kind: Literal["hospital", "fire_station", "police", "school"]
    longitude: float
    latitude: float


class CityIndex(BaseModel):
    traffic_tpi: float
    traffic_level: TrafficLevel
    safety_score: int
    sensors_online: int
    sensors_total: int


class DistrictCount(BaseModel):
    name: str
    count: int


class OverviewOut(BaseModel):
    total: int
    active: int
    today: int
    resolved_today: int
    resolve_rate: float
    avg_response_min: float
    by_type: dict[EventType, int]
    by_status: dict[EventStatus, int]
    by_severity: dict[Severity, int]
    by_district: list[DistrictCount]
    trend: list[dict[str, int | str]]
    city_index: CityIndex
    updated_at: str


class DataItemOut(BaseModel):
    id: str
    name: str
    type: str
    time: str
    status: str
    source: str
    format: str
    size: str
    size_bytes: int
    records: int
    description: str
    url: str | None
    spatial_extent: dict[str, Any]
    time_start: str | None
    time_end: str | None
    crs: str
    quality_score: float
    quality_notes: list[str]
    version: str
    analysis_status: DataAnalysisStatus


class TypeCount(BaseModel):
    type: str
    count: int


class DataStatsOut(BaseModel):
    total: int
    total_size: str
    by_type: list[TypeCount]
    analyzable: int
    by_analysis_status: list[TypeCount]


class DataValidationCreate(BaseModel):
    decision: DataValidationDecision
    coordinate_check: bool = False
    time_check: bool = False
    fields_check: bool = False
    notes: list[str] = Field(default_factory=list)
    operator: str = Field(default="数据管理员", max_length=64)


class DataValidationOut(BaseModel):
    id: str
    asset_id: str
    decision: DataValidationDecision
    checks: dict[str, bool]
    quality_score: float
    notes: list[str]
    operator: str
    created_at: str


class TaskInput(BaseModel):
    name: str
    url: str


class AlgorithmOut(BaseModel):
    name: str
    version: str
    method: str


class Location(BaseModel):
    longitude: float
    latitude: float


class AnalysisTaskOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    type: str
    status: TaskStatus
    createdAt: str
    finished_at: str | None = None
    progress: int = 0
    file_count: int = 0
    inputs: list[TaskInput] = []
    algorithm: AlgorithmOut | None = None
    location: Location | None = None
    result: dict[str, Any] | None = None
    error: str | None = None


class MonitoringExecuteOut(BaseModel):
    monitoring_run: MonitoringRunOut
    analysis_task: AnalysisTaskOut


class SampleOut(BaseModel):
    id: str
    type: EventType
    name: str
    description: str
    kind: Literal["image", "csv", "image_pair"]
    thumbnail_url: str
    files: list[str]
    longitude: float | None = None
    latitude: float | None = None


class SourceOut(BaseModel):
    id: str
    name: str
    type: Literal["drone", "satellite", "video", "sensor", "other"]
    icon: str
    desc: str
    status: Literal["在线", "采集中", "离线", "待接入"]
    devices_online: int
    devices_total: int
    throughput: float
    unit: str
    last_active: str
    coverage: str


class AlgorithmInfoOut(BaseModel):
    type: EventType
    name: str
    method: str
    version: str


class SimulatorInfo(BaseModel):
    enabled: bool
    interval_sec: float


class RegionInfo(BaseModel):
    name: str
    city: str
    center: tuple[float, float]
    bbox: tuple[float, float, float, float]


class SystemInfoOut(BaseModel):
    name: str
    version: str
    demo_mode: bool
    simulator: SimulatorInfo
    database: str
    uptime_sec: int
    region: RegionInfo
    algorithms: list[AlgorithmInfoOut]
    data_attribution: str


class ScenarioOut(BaseModel):
    task_id: str
    event_id: str | None


class OkOut(BaseModel):
    ok: bool
