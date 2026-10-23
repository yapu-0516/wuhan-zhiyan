"""算法注册表：按事件类型 + 输入文件类型分派到具体分析器。

| 类型      | 输入                  | 分析器                         |
| --------- | --------------------- | ------------------------------ |
| fire      | 图片 ×N               | FlameNet-Lite                  |
| traffic   | CSV(time,speed[,flow])| TrafficPulse                   |
| traffic   | 图片 ×N               | RoadOcc                        |
| building  | CSV(date,displacement_mm) | SettleWatch                |
| building  | 图片 ×2（前、后时相） | ChangeScope                    |
| flood     | CSV(time,water_level_cm[,rainfall_mm]) | AquaLevel     |
| flood     | 图片 ×N               | AquaSeg                        |

单图分析器接收多张图片时逐张分析并汇总。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, Sequence

from .base import Analyzer, AnalysisResult, Artifact, InputError
from .building import ChangeDetector, SettlementAnalyzer
from .fire import FireDetector
from .flood import WaterLevelAnalyzer, WaterSegmenter
from .imgproc import IMAGE_SUFFIXES
from .timeseries import read_header
from .traffic import TrafficSeriesAnalyzer, VehicleOccupancyAnalyzer

EVENT_TYPES = ("fire", "traffic", "building", "flood")
TYPE_CN = {"fire": "火灾", "traffic": "交通拥堵", "building": "建筑异常", "flood": "内涝积水"}
MAX_FILES = 10

ANALYZERS: list[Analyzer] = [
    FireDetector(),
    TrafficSeriesAnalyzer(),
    VehicleOccupancyAnalyzer(),
    SettlementAnalyzer(),
    ChangeDetector(),
    WaterLevelAnalyzer(),
    WaterSegmenter(),
]
BY_KEY: dict[str, Analyzer] = {a.meta.key: a for a in ANALYZERS}

_CSV_COLUMNS = {
    "traffic.series": ("time", "speed"),
    "building.series": ("date", "displacement_mm"),
    "flood.series": ("time", "water_level_cm"),
}
_CSV_HINT = {
    "traffic": "CSV（列 time,speed[,flow]）或路面航拍图片",
    "building": "1 个沉降 CSV（列 date,displacement_mm）或前后时相 2 张图片",
    "flood": "CSV（列 time,water_level_cm[,rainfall_mm]）或积水现场图片",
    "fire": "jpg / png 图片",
}


def file_kind(path: Path | str) -> Literal["image", "csv"] | None:
    suffix = Path(path).suffix.lower()
    if suffix in IMAGE_SUFFIXES:
        return "image"
    if suffix == ".csv":
        return "csv"
    return None


def algorithms() -> list[dict[str, str]]:
    """全部算法的公开元信息（/api/system/info）。"""
    return [a.meta.public() for a in ANALYZERS]


def select(event_type: str, paths: Sequence[Path | str]) -> Analyzer:
    """根据类型与文件选择分析器；不合法时抛出 InputError（中文说明）。"""
    if event_type not in EVENT_TYPES:
        raise InputError(f"不支持的分析类型：{event_type}（可选 fire / traffic / building / flood）")
    if not paths:
        raise InputError("请至少提供 1 个输入文件")
    if len(paths) > MAX_FILES:
        raise InputError(f"单个任务最多 {MAX_FILES} 个文件")
    kinds = {file_kind(p) for p in paths}
    if None in kinds:
        bad = next(Path(p).name for p in paths if file_kind(p) is None)
        raise InputError(f"不支持的文件格式：{bad}；{TYPE_CN[event_type]}分析需要 {_CSV_HINT[event_type]}")
    if len(kinds) > 1:
        raise InputError("同一任务中不能混合图片与 CSV 文件")
    kind = kinds.pop()
    if event_type == "fire":
        if kind != "image":
            raise InputError("火灾检测需要 jpg / png 图片")
        return BY_KEY["fire.image"]
    if event_type == "building":
        if kind == "csv":
            if len(paths) != 1:
                raise InputError("沉降分析一次仅支持 1 个 CSV 文件")
            return BY_KEY["building.series"]
        if len(paths) != 2:
            raise InputError("建筑变化检测需要前后两个时相的 2 张图片（按 前、后 顺序上传）")
        return BY_KEY["building.change"]
    key = f"{event_type}.{'series' if kind == 'csv' else 'image'}"
    if kind == "csv" and len(paths) != 1:
        raise InputError("时序分析一次仅支持 1 个 CSV 文件")
    return BY_KEY[key]


def validate(event_type: str, paths: Sequence[Path | str]) -> Analyzer:
    """select + 轻量内容校验（CSV 表头），用于上传时同步返回 400。"""
    analyzer = select(event_type, paths)
    required = _CSV_COLUMNS.get(analyzer.meta.key)
    if required:
        header = read_header(Path(paths[0]))
        missing = [c for c in required if c not in header]
        if missing:
            raise InputError(
                f"CSV 文件 {Path(paths[0]).name} 缺少必需列：{', '.join(missing)}（需要 {', '.join(required)}）"
            )
    return analyzer


def run(
    event_type: str, paths: Sequence[Path | str], out_dir: Path, prefix: str, **params: Any
) -> tuple[Analyzer, AnalysisResult]:
    """执行分析。产物写入 out_dir，文件名以 prefix 开头。"""
    analyzer = select(event_type, paths)
    files = [Path(p) for p in paths]
    out_dir.mkdir(parents=True, exist_ok=True)
    if analyzer.meta.input_kind == "image" and len(files) > 1:
        return analyzer, _run_batch(analyzer, files, out_dir, prefix, params)
    return analyzer, analyzer.analyze(files, out_dir, prefix, **params)


def _run_batch(analyzer: Analyzer, files: list[Path], out_dir: Path, prefix: str, params: dict[str, Any]) -> AnalysisResult:
    results = [analyzer.analyze([f], out_dir, f"{prefix}_{i + 1}", **params) for i, f in enumerate(files)]
    for i, r in enumerate(results):
        for d in r.detections:
            d.image = i
    positives = [i for i, r in enumerate(results) if r.detected]
    best_i = max(range(len(results)), key=lambda i: (results[i].detected, results[i].confidence))
    best = results[best_i]
    summary = f"共分析 {len(files)} 张图片，{len(positives)} 张检出异常；第 {best_i + 1} 张：{best.summary}"
    metrics = dict(best.metrics)
    metrics.update({"images": len(files), "positive_images": len(positives), "best_image": best_i + 1})
    artifacts = [
        Artifact(f"{a.name}（第 {i + 1} 张）", a.path, a.kind) for i, r in enumerate(results) for a in r.artifacts
    ]
    # 主产物放在首位（证据图取最可信的一张）
    artifacts.sort(key=lambda a: 0 if f"第 {best_i + 1} 张" in a.name else 1)
    return AnalysisResult(
        detected=bool(positives),
        confidence=best.confidence,
        summary=summary,
        detections=[d for r in results for d in r.detections],
        metrics=metrics,
        series=None,
        artifacts=artifacts,
        level=best.level,
    )
