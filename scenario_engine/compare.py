"""两个已运行情景的确定性差异计算。"""

from __future__ import annotations

from .models import ScenarioComparison, ScenarioParameters, ScenarioRun

METRICS = ("water_depth_cm", "tpi", "people", "evacuated")


def compare_runs(
    left: ScenarioRun,
    right: ScenarioRun,
    left_params: ScenarioParameters,
    right_params: ScenarioParameters,
) -> ScenarioComparison:
    changes = []
    for key in ScenarioParameters.model_fields:
        before = getattr(left_params, key)
        after = getattr(right_params, key)
        if before != after:
            changes.append({"field": key, "before": before, "after": after})

    left_peak = max((frame.risk_level for frame in left.frames), key=_risk_rank, default="unknown")
    right_peak = max((frame.risk_level for frame in right.frames), key=_risk_rank, default="unknown")
    risk_changes = [{"field": "peak_risk", "before": left_peak, "after": right_peak}]

    metric_changes: dict[str, dict[str, float | int | None]] = {}
    for metric in METRICS:
        before_values = [f.metrics.get(metric) for f in left.frames if isinstance(f.metrics.get(metric), (int, float))]
        after_values = [f.metrics.get(metric) for f in right.frames if isinstance(f.metrics.get(metric), (int, float))]
        if before_values or after_values:
            metric_changes[metric] = {
                "before": max(before_values) if before_values else None,
                "after": max(after_values) if after_values else None,
            }

    return ScenarioComparison(
        left_run_id=left.run_id,
        right_run_id=right.run_id,
        parameter_changes=changes,
        risk_changes=risk_changes,
        metric_changes=metric_changes,
        summary=f"共 {len(changes)} 项参数变化，峰值风险由 {left_peak} 变为 {right_peak}。",
        data_classification="simulated"
        if "simulated" in (left.data_classification, right.data_classification)
        else "professional_analysis",
    )


def _risk_rank(level: str) -> int:
    return {"unknown": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}.get(level, 0)
