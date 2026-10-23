"""算法公共数据结构：算法元信息、检测框、分析结果、输入异常。"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Literal, Protocol, Sequence

InputKind = Literal["image", "image_pair", "csv"]
ArtifactKind = Literal["image", "chart", "json"]
MetricValue = float | int | str


class InputError(ValueError):
    """输入数据不合法（文件类型、列名、数量等），message 为面向用户的中文说明。"""


@dataclass(frozen=True)
class AlgorithmMeta:
    """算法元信息。type 对应事件类型；key 为注册表内唯一键，如 fire.image。"""

    type: str
    key: str
    name: str
    version: str
    method: str
    input_kind: InputKind

    def public(self) -> dict[str, str]:
        """对外暴露的字段（/api/system/info 与 AnalysisTask.algorithm）。"""
        return {"type": self.type, "name": self.name, "version": self.version, "method": self.method}


@dataclass
class Detection:
    """单个检测目标，bbox 为原图像素坐标 [x, y, w, h]。"""

    label: str
    confidence: float
    bbox: tuple[int, int, int, int]
    area_ratio: float | None = None
    image: int | None = None  # 批量分析时所属图片序号（从 0 开始）

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "label": self.label,
            "confidence": round(float(self.confidence), 3),
            "bbox": [int(v) for v in self.bbox],
        }
        if self.area_ratio is not None:
            d["area_ratio"] = round(float(self.area_ratio), 5)
        if self.image is not None:
            d["image"] = self.image
        return d


@dataclass
class Artifact:
    """算法产物文件（标注图、图表）。"""

    name: str
    path: Path
    kind: ArtifactKind = "image"


@dataclass
class AnalysisResult:
    """统一的分析结果。

    - detected / confidence / summary：是否发现异常、置信度（0~1）、中文结论；
    - level：语义等级（如 TrafficLevel / RiskLevel / 积水等级），供后端映射事件等级；
    - series：时序类分析的绘图数据，每项至少包含 t 与 v。
    """

    detected: bool
    confidence: float
    summary: str
    detections: list[Detection] = field(default_factory=list)
    metrics: dict[str, MetricValue] = field(default_factory=dict)
    series: list[dict[str, Any]] | None = None
    artifacts: list[Artifact] = field(default_factory=list)
    level: str | None = None

    @property
    def primary_artifact(self) -> Artifact | None:
        return self.artifacts[0] if self.artifacts else None

    def to_dict(self, url_for: Callable[[Path], str] = lambda p: str(p)) -> dict[str, Any]:
        """转为 docs/api.md 中 AnalysisTask.result 结构（event_ids 由后端补齐）。"""
        return {
            "detected": bool(self.detected),
            "confidence": round(float(self.confidence), 3),
            "summary": self.summary,
            "detections": [d.to_dict() for d in self.detections],
            "metrics": {k: _clean_metric(v) for k, v in self.metrics.items()},
            "artifacts": [{"name": a.name, "url": url_for(a.path), "kind": a.kind} for a in self.artifacts],
            "series": self.series,
            "level": self.level,
        }


def _clean_metric(v: MetricValue) -> MetricValue:
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, float):
        return round(v, 4)
    if hasattr(v, "item"):  # numpy 标量
        return _clean_metric(v.item())  # type: ignore[union-attr]
    return v


class Analyzer(Protocol):
    meta: AlgorithmMeta

    def analyze(self, inputs: Sequence[Path], out_dir: Path, prefix: str, **params: Any) -> AnalysisResult:
        ...


def clamp01(x: float) -> float:
    return float(min(1.0, max(0.0, x)))
