"""请求 / 响应模型（字段与 docs/api.md 一一对应；响应模型同时用于 /docs 文档与输出校验）。"""
from __future__ import annotations

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


class TaskCreate(BaseModel):
    type: str
    fileCount: int = 0
    sample_id: str | None = None
    longitude: float | None = Field(default=None, ge=-180, le=180)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    create_event: bool = True


class ScenarioRequest(BaseModel):
    scenario: Literal["fire", "traffic", "building", "flood", "random"] = "random"


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
    metrics: dict[str, Metric]
    assignee: str | None = None
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


class TypeCount(BaseModel):
    type: str
    count: int


class DataStatsOut(BaseModel):
    total: int
    total_size: str
    by_type: list[TypeCount]


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
