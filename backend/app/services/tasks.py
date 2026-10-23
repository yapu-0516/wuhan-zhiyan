"""AI 分析任务：创建 → 线程池异步执行真实算法 → 分阶段推送进度 → 保存结果 →（检出且有位置时）生成事件。

阶段与进度：10 加载输入 → 35 算法推理 → 70 生成结论 → 100 完成。
task_pacing 只控制每个阶段推送后的最短停顿，便于前端展示进度，不影响算法结果。
"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

import cityeye_algo as ca
from sqlalchemy.orm import Session

from .. import timeutil
from ..models import Task
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
            analyzer, result = ca.run(t.type, paths, ctx.results_dir, t.id)
            stage(70, "生成结论")
            res = result.to_dict(ctx.url_for)
            res["event_ids"] = []
            if result.detected and t.create_event and t.longitude is not None and t.latitude is not None:
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
    s.commit()
    ctx.hub.publish("task.updated", task_to_dict(t))
