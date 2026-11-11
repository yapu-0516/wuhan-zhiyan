"""AI 分析任务：创建 → 线程池异步执行真实算法 → 分阶段推送进度 → 保存结果 →（检出且有位置时）生成事件。

阶段与进度：10 加载输入 → 35 算法推理 → 70 生成结论 → 100 完成。
task_pacing 只控制每个阶段推送后的最短停顿，便于前端展示进度，不影响算法结果。
"""
from __future__ import annotations

import logging
import time
import hashlib
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

import cityeye_algo as ca
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import timeutil
from ..models import MonitoringRun, MonitoringTask, Task
from .events import event_from_result, event_to_dict, next_id

if TYPE_CHECKING:
    from ..context import AppContext

log = logging.getLogger("cityeye.tasks")


def task_to_dict(t: Task) -> dict[str, Any]:
    return {
        "id": t.id,
        "type": t.type,
        "status": t.status,
        "createdAt": timeutil.fmt(t.created_at),
        "finished_at": timeutil.fmt(t.finished_at),
        "progress": t.progress,
        "file_count": t.file_count,
        "inputs": t.inputs or [],
        "algorithm": t.algorithm or None,
        "location": {"longitude": t.longitude, "latitude": t.latitude} if t.longitude is not None and t.latitude is not None else None,
        "result": t.result,
        "error": t.error,
    }


def create_task(
    ctx: "AppContext",
    session: Session,
    *,
    event_type: str,
    paths: list[Path],
    inputs: list[dict[str, str]],
    longitude: float | None,
    latitude: float | None,
    create_event: bool,
    sample_id: str | None,
    origin: str,
    created_at: Any = None,
) -> Task:
    """校验输入并入库（status=pending）。输入不合法时抛出 ca.InputError。"""
    analyzer = ca.validate(event_type, paths)
    meta = analyzer.meta.public()
    meta.pop("type")
    with ctx.id_lock:
        t = Task(
            id=next_id(session, Task.id, "T"), type=event_type, status="pending", origin=origin,
            created_at=created_at or timeutil.now(), progress=0, stage="排队中", file_count=len(paths),
            inputs=inputs, algorithm=meta, sample_id=sample_id, longitude=longitude, latitude=latitude,
            create_event=create_event,
        )
        session.add(t)
        session.commit()
    return t


def submit(ctx: "AppContext", task: Task, paths: list[Path]) -> None:
    ctx.hub.publish("task.updated", task_to_dict(task))
    ctx.executor.submit(run_task, ctx, task.id, paths)


def _input_label(ctx: "AppContext", t: Task) -> str:
    if t.sample_id and t.sample_id in ctx.samples.by_id:
        return f"输入：示例数据「{ctx.samples.by_id[t.sample_id]['name']}」（合成演示数据），任务 {t.id}"
    return f"输入：用户上传 {t.file_count} 个文件，任务 {t.id}"


def _file_hashes(paths: list[Path]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in paths:
        digest = hashlib.sha256()
        with path.open("rb") as source:
            while chunk := source.read(1 << 20):
                digest.update(chunk)
        rows.append({"name": path.name, "sha256": digest.hexdigest()})
    return rows


def _rule_triggered(
    task: MonitoringTask | None,
    result: Any,
    previous_runs: list[MonitoringRun] | None = None,
    now: Any = None,
) -> tuple[bool, str]:
    """算法检出后再应用任务阈值；未配置阈值的任务沿用算法结论。"""
    if task is None:
        return True, "no_business_task"
    config = task.rule_config or {}
    metrics = result.metrics or {}

    def number(*keys: str) -> float | None:
        for key in keys:
            value = metrics.get(key)
            if isinstance(value, (int, float)):
                return float(value)
        return None

    def limit(key: str) -> float | None:
        try:
            value = float(config.get(key))
        except (TypeError, ValueError):
            return None
        return value if value >= 0 else None

    threshold: float | None = None
    measured: float | None = None
    if task.event_type == "flood":
        threshold = limit("water_level_threshold_cm")
        measured = number("max_level_cm", "current_level_cm", "peak_level_cm")
    elif task.event_type == "traffic":
        threshold = limit("tpi_threshold")
        measured = number("equivalent_tpi", "tpi", "tpi_peak")
    elif task.event_type == "building":
        threshold = limit("settlement_rate_mm_month")
        measured = number("rate_mm_per_month", "overall_rate_mm_per_month")
        measured = abs(measured) if measured is not None else None
    elif task.event_type == "fire":
        threshold = limit("confidence_threshold")
        measured = float(result.confidence)
    if threshold is None:
        return True, "no_threshold"
    if measured is None:
        return True, "metric_unavailable"
    passed = measured >= threshold
    details = [f"threshold:measured={measured:.3f};threshold={threshold:.3f}"]

    conditions = config.get("conditions") or []
    if isinstance(conditions, list):
        for condition in conditions:
            if not isinstance(condition, dict):
                continue
            metric = str(condition.get("metric") or "")
            operator = str(condition.get("operator") or ">=")
            expected = condition.get("value")
            actual = metrics.get(metric)
            if not isinstance(actual, (int, float)) or not isinstance(expected, (int, float)):
                passed = False
                details.append(f"{metric}:metric_unavailable")
                continue
            comparisons = {
                ">=": actual >= expected,
                ">": actual > expected,
                "<=": actual <= expected,
                "<": actual < expected,
                "==": actual == expected,
                "!=": actual != expected,
            }
            condition_passed = comparisons.get(operator, False)
            passed = passed and condition_passed
            details.append(f"{metric}:{actual}{operator}{expected}={condition_passed}")

    try:
        minimum = max(1, int(config.get("min_consecutive") or 1))
    except (TypeError, ValueError):
        minimum = 1
    if minimum > 1:
        hits = 1 if passed else 0
        for previous in previous_runs or []:
            if (previous.quality or {}).get("rule_triggered") is True:
                hits += 1
            else:
                break
        if hits < minimum:
            passed = False
        details.append(f"consecutive:{hits}/{minimum}")

    try:
        cooldown = max(0, int(config.get("cooldown_minutes") or 0))
    except (TypeError, ValueError):
        cooldown = 0
    current_time = now or timeutil.now()
    if cooldown > 0:
        for previous in previous_runs or []:
            if not previous.event_ids or previous.finished_at is None:
                continue
            elapsed = (current_time - previous.finished_at).total_seconds() / 60
            if elapsed < cooldown:
                passed = False
                details.append(f"cooldown:last_event={elapsed:.1f}/{cooldown}min")
                break
    return passed, "；".join(details)


def run_task(ctx: "AppContext", task_id: str, paths: list[Path], pace: float | None = None) -> Task | None:
    """执行任务（在线程池或调用线程中运行），返回最终任务对象。"""
    pace = ctx.settings.task_pacing if pace is None else pace
    with ctx.session() as s:
        t = s.get(Task, task_id)
        if t is None:
            return None

        def stage(progress: int, name: str, status: str = "running") -> None:
            t.progress, t.stage, t.status = progress, name, status
            s.commit()
            ctx.hub.publish("task.updated", task_to_dict(t))
            if pace and status == "running":
                time.sleep(pace)

        try:
            t.started_at = timeutil.now()
            stage(10, "加载输入")
            stage(35, "算法推理")
            run = s.scalar(select(MonitoringRun).where(MonitoringRun.analysis_task_id == t.id))
            business_task = s.get(MonitoringTask, run.monitoring_task_id) if run is not None else None
            algorithm_params = (
                dict((business_task.rule_config or {}).get("algorithm_params") or {})
                if business_task is not None
                else {}
            )
            analyzer, result = ca.run(t.type, paths, ctx.results_dir, t.id, **algorithm_params)
            stage(70, "生成结论")
            res = result.to_dict(ctx.url_for)
            res["event_ids"] = []
            provenance = {
                "input_sha256": _file_hashes(paths),
                "algorithm": analyzer.meta.name,
                "algorithm_version": analyzer.meta.version,
            }
            res["provenance"] = provenance
            t.inputs = [
                {**item, "sha256": next(
                    (record["sha256"] for record in provenance["input_sha256"] if record["name"] == item.get("name")),
                    None,
                )}
                for item in (t.inputs or [])
            ]
            previous_runs = list(
                s.scalars(
                    select(MonitoringRun)
                    .where(
                        MonitoringRun.monitoring_task_id == business_task.id if business_task is not None else False,
                        MonitoringRun.id != run.id if run is not None else True,
                    )
                    .order_by(MonitoringRun.created_at.desc())
                    .limit(20)
                )
            ) if business_task is not None else []
            rule_triggered, trigger_detail = _rule_triggered(
                business_task,
                result,
                previous_runs=previous_runs,
                now=timeutil.now(),
            )
            res["trigger"] = {
                "rule_triggered": rule_triggered,
                "detail": trigger_detail,
            }
            if (
                result.detected
                and rule_triggered
                and t.create_event
                and t.longitude is not None
                and t.latitude is not None
            ):
                art = result.primary_artifact
                ev = event_from_result(
                    ctx, s, event_type=t.type, algorithm_name=analyzer.meta.name, result=result,
                    longitude=t.longitude, latitude=t.latitude, source="ai_task", task_id=t.id,
                    input_kind=analyzer.meta.input_kind, input_label=_input_label(ctx, t),
                    evidence_src=art.path if art else None, creator=f"AI 分析任务 {t.id}",
                )
                res["event_ids"].append(ev.id)
                ctx.hub.publish("event.created", event_to_dict(ev))
            t.result = res
            t.finished_at = timeutil.now()
            if run is not None:
                run.status = "completed"
                run.event_ids = res.get("event_ids", [])
                run.finished_at = t.finished_at
                run.quality = {
                    "confidence": result.confidence,
                    "detected": result.detected,
                    "algorithm": analyzer.meta.name,
                    "rule_triggered": rule_triggered,
                    "trigger_detail": trigger_detail,
                    "provenance": provenance,
                }
                if business_task is not None:
                    recurring = (
                        business_task.schedule_type == "periodic"
                        and (business_task.end_at is None or business_task.end_at > t.finished_at)
                    )
                    business_task.status = "scheduled" if recurring else "completed"
                    if recurring and business_task.next_run_at is None:
                        raw = (business_task.rule_config or {}).get("interval_minutes", 60)
                        try:
                            interval = max(1, min(10_080, int(raw)))
                        except (TypeError, ValueError):
                            interval = 60
                        business_task.next_run_at = t.finished_at + timedelta(minutes=interval)
                    business_task.updated_at = t.finished_at
            stage(100, "完成", status="done")
        except ca.InputError as e:
            _fail(ctx, s, t, str(e))
        except Exception as e:  # noqa: BLE001 - 任务失败需落库并推送，不能让线程静默崩溃
            log.exception("任务 %s 执行异常", task_id)
            _fail(ctx, s, t, f"算法执行异常：{e.__class__.__name__}: {e}")
        return t


def _fail(ctx: "AppContext", s: Session, t: Task, msg: str) -> None:
    s.rollback()
    t.status, t.error, t.stage, t.finished_at = "failed", msg, "失败", timeutil.now()
    run = s.scalar(select(MonitoringRun).where(MonitoringRun.analysis_task_id == t.id))
    if run is not None:
        run.status = "failed"
        run.failure_reason = msg
        run.finished_at = t.finished_at
        business_task = s.get(MonitoringTask, run.monitoring_task_id)
        if business_task is not None:
            business_task.status = "failed"
            business_task.updated_at = t.finished_at
    s.commit()
    ctx.hub.publish("task.updated", task_to_dict(t))
