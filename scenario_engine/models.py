"""情景推演的数据契约，独立于 FastAPI、数据库和前端。"""

from __future__ import annotations

from typing import Literal

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ScenarioType = Literal["flood", "traffic", "fire"]
RiskLevel = Literal["unknown", "low", "medium", "high", "critical"]
DataClass = Literal["real", "professional_analysis", "simulated", "llm_inference", "unknown"]


class ScenarioParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    location_name: str | None = None
    longitude: float | None = Field(default=None, ge=-180, le=180)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    start_time: str | None = None
    duration_min: int | None = Field(default=None, ge=1, le=1440)

    rainfall_mm_h: float | None = Field(default=None, ge=0, le=300)
    congestion_level: Literal["light", "moderate", "severe"] | None = None
    traffic_cause: str | None = None
    fire_severity: Literal["small", "medium", "large"] | None = None
    danger_radius_m: float | None = Field(default=None, ge=10, le=3000)
    people_count: int | None = Field(default=None, ge=0, le=5000)
    population_profile: Literal["workday", "weekend_day", "weekend_night"] | None = None
    response_delay_min: int | None = Field(default=None, ge=0, le=60)
    closed_exit_count: int | None = Field(default=None, ge=0, le=4)
    variation_seed: int | None = Field(default=None, ge=0, le=2_147_483_647)

    @field_validator("congestion_level", mode="before")
    @classmethod
    def normalize_congestion(cls, value: object) -> object:
        if isinstance(value, str):
            return {"轻度": "light", "中度": "moderate", "严重": "severe"}.get(value.strip(), value)
        return value

    @field_validator("fire_severity", mode="before")
    @classmethod
    def normalize_fire_severity(cls, value: object) -> object:
        if isinstance(value, str):
            return {
                "小型": "small",
                "中型": "medium",
                "大型": "large",
                "小": "small",
                "中": "medium",
                "大": "large",
            }.get(value.strip(), value)
        return value

    @field_validator(
        "duration_min",
        "people_count",
        "response_delay_min",
        "closed_exit_count",
        "variation_seed",
        mode="before",
    )
    @classmethod
    def normalize_integer(cls, value: object) -> object:
        if isinstance(value, str):
            match = re.search(r"\d+", value)
            return int(match.group()) if match else value
        return value

    @field_validator("rainfall_mm_h", "danger_radius_m", mode="before")
    @classmethod
    def normalize_float(cls, value: object) -> object:
        if isinstance(value, str):
            match = re.search(r"\d+(?:\.\d+)?", value)
            return float(match.group()) if match else value
        return value


class ScenarioDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_type: ScenarioType
    title: str
    parameters: ScenarioParameters
    data_classification: DataClass = "unknown"


class ImpactZone(BaseModel):
    id: str
    risk_level: RiskLevel
    longitude: float
    latitude: float
    radius_m: float | None = Field(default=None, gt=0)
    polygon: list[tuple[float, float]] | None = None
    data_classification: DataClass

    @model_validator(mode="after")
    def require_geometry(self) -> "ImpactZone":
        if self.radius_m is None and (not self.polygon or len(self.polygon) < 3):
            raise ValueError("风险区域必须提供 radius_m 或至少三个 polygon 顶点")
        return self


class PeopleState(BaseModel):
    id: str
    longitude: float
    latitude: float
    state: Literal["idle", "queued", "moving", "safe"]


class ScenarioFrame(BaseModel):
    offset_min: int = Field(ge=0)
    timestamp: str | None = None
    risk_level: RiskLevel
    zones: list[ImpactZone]
    metrics: dict[str, float | int | str | None]
    affected_building_ids: list[str] = Field(default_factory=list)
    affected_road_ids: list[str] = Field(default_factory=list)
    people: list[PeopleState] = Field(default_factory=list)
    data_classification: DataClass
    limitations: list[str] = Field(default_factory=list)


class ScenarioRun(BaseModel):
    run_id: str
    version_id: str
    scenario_type: ScenarioType
    variant_label: str = "默认方案"
    status: Literal["preview", "success", "failed"] = "success"
    provider: str
    data_classification: DataClass
    frames: list[ScenarioFrame]
    summary: str
    assumptions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    generated_at: str


class ScenarioComparison(BaseModel):
    left_run_id: str
    right_run_id: str
    parameter_changes: list[dict[str, str | float | int | None]]
    risk_changes: list[dict[str, str]]
    metric_changes: dict[str, dict[str, float | int | None]]
    summary: str
    data_classification: DataClass


def missing_fields(scenario_type: ScenarioType, params: ScenarioParameters) -> list[str]:
    missing: list[str] = []
    if not params.location_name and (params.longitude is None or params.latitude is None):
        missing.append("事件地点")
    if not params.start_time:
        missing.append("开始时间")
    if not params.duration_min:
        missing.append("持续时间")
    if scenario_type == "flood" and params.rainfall_mm_h is None:
        missing.append("降雨强度")
    if scenario_type == "traffic":
        if not params.congestion_level:
            missing.append("拥堵程度")
        if not params.traffic_cause:
            missing.append("拥堵原因")
    if scenario_type == "fire":
        if not params.fire_severity and not params.danger_radius_m:
            missing.append("火灾规模或危险半径")
        if params.people_count is None:
            missing.append("影响人数")
    return missing
