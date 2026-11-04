"""大模型桥接接口：把 llm_module（DeepSeek）的能力暴露为 HTTP。

- GET  /api/llm/status       密钥是否已配置（不发起模型调用）
- POST /api/llm/parse-task   自然语言 → 结构化任务（llm_module.task_parser）
- POST /api/llm/report       以事件目录数据 + 周边 POI/道路为输入生成结构化研判报告（llm_module.report_generator）
- POST /api/llm/chat         受控多轮城市治理问答，可选关联一个现有事件（llm_module.chat）

模型调用为付费 API 且耗时数秒，仅在用户点击时触发；密钥缺失 / 模型异常统一返回 503。
"""
from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..context import AppContext, get_ctx, not_found
from ..models import Event, Task
from ..services.events import event_to_dict

# llm_module 位于仓库根目录；若以 `cd backend && uvicorn app.main:app` 启动，根目录不在 sys.path
_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from llm_module.client import LLMError, Settings  # noqa: E402
from llm_module.chat import ChatTurn, answer_chat  # noqa: E402
from llm_module.report_generator import ReportError, generate_report  # noqa: E402
from llm_module.task_parser import TaskParseError, parse_task  # noqa: E402

router = APIRouter(prefix="/llm", tags=["大模型"])

_TYPE_LABEL = {"fire": "火灾", "traffic": "交通拥堵", "building": "建筑异常", "flood": "内涝积水"}


class ParseTaskIn(BaseModel):
    text: str = Field(min_length=2, max_length=500)


class ReportIn(BaseModel):
    event_id: str = Field(min_length=1, max_length=32)


class ChatMessageIn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ChatIn(BaseModel):
    messages: list[ChatMessageIn] = Field(min_length=1, max_length=8)
    event_id: str | None = Field(default=None, min_length=1, max_length=32)


def _call_llm(fn: Any, *args: Any, **kwargs: Any) -> Any:
    """统一把 LLMError 转为 503，不向客户端透出内部异常。

    模型偶发输出非法 JSON / 结构不符（ReportError / TaskParseError）属瞬时抖动，自动重试一次；
    认证、限流、连接类错误不会瞬时自愈，直接失败。注意：重试意味着本次请求可能计费两次。
    """
    try:
        try:
            return fn(*args, **kwargs)
        except (ReportError, TaskParseError):
            return fn(*args, **kwargs)
    except LLMError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _distance_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    r = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _event_view(ev: dict[str, Any]) -> dict[str, Any]:
    """给模型的事件视图：把区/地址/网格合并成一个 location 字符串。

    模型习惯把散落的地址字段自行拼成对象，而报告 schema 要求 location 是字符串，
    会稳定触发校验失败；预先合并后模型只会照抄该字段。
    """
    loc = " · ".join(p for p in (ev.get("district"), ev.get("address"), ev.get("grid")) if p) or None
    view = {
        "event_id": ev["id"],
        "event_type": ev["event_type"],
        "name": ev["name"],
        "location": loc,
        "longitude": ev["longitude"],
        "latitude": ev["latitude"],
        "timestamp": ev["timestamp"],
        "updated_at": ev["updated_at"],
        "status": ev["status"],
        "severity": ev["severity"],
        "source": ev["source"],
        "confidence": ev["confidence"],
        "description": ev["description"],
        "metrics": ev["metrics"],
        "assignee": ev["assignee"],
        "building_id": ev["building_id"],
        "task_id": ev["task_id"],
    }
    return {k: v for k, v in view.items() if v not in (None, "")}


def _event_data_nature(ctx: AppContext, ev: dict[str, Any], task: Task | None) -> tuple[str, list[str]]:
    """判定事件输入的真实性质，供报告生成与最终结果共同使用。

    事件表本身没有独立的数据性质字段，因此按可验证来源保守判断：
    分析任务优先看 origin/sample_id；其余事件看市民上报与描述中的合成/模拟标记。
    无法确认时返回“未经核验”，不得把演示记录表述为真实监测事件。
    """
    if task is not None:
        if task.origin in ("seed", "demo") or task.sample_id:
            return "示例数据，不代表真实事件", [
                "事件由示例或演示数据经算法分析生成，不是真实监测结果",
            ]
        if task.origin == "upload":
            return "用户上传数据分析结果，真实性未核验", [
                "上传文件、任务位置和算法结论均未经现场核验",
            ]
        return "算法分析结果，事件真实性未核验", [
            "事件来自算法分析任务，输入数据与现场情况尚未核验",
        ]

    if ev.get("source") == "citizen":
        return "市民上报事件，尚未经现场核验", [
            "上报内容尚未经现场核验，不能视为已确认的城市事件",
        ]

    description = ev.get("description") or ""
    if "合成演示数据" in description or "模拟数据" in description:
        return "模拟器数据，不代表真实事件", [
            "事件来自合成或模拟监测数据，仅用于功能演示",
        ]

    if ctx.settings.demo_mode:
        return "演示环境数据，真实性未核验", [
            "当前运行于演示模式，事件来源尚未经现场核验",
        ]
    return "监测系统事件，真实性未核验", [
        "事件来源缺少独立核验信息",
    ]


def _load_event_context(ctx: AppContext, event_id: str) -> tuple[dict[str, Any], str, list[str], list[dict[str, Any]]]:
    with ctx.session() as s:
        event = s.get(Event, event_id)
        if event is None:
            raise not_found(f"事件 {event_id} 不存在")
        ev = event_to_dict(event)
        task = s.get(Task, event.task_id) if event.task_id else None
        data_type, known_gaps = _event_data_nature(ctx, ev, task)

    lon, lat = ev["longitude"], ev["latitude"]
    facilities: list[dict[str, Any]] = []
    for poi in ctx.geo.pois:
        distance = _distance_m(lon, lat, poi["longitude"], poi["latitude"])
        if distance <= 1000:
            facilities.append({"name": poi["name"], "kind": poi["kind"], "distance_m": round(distance)})
    facilities.sort(key=lambda item: item["distance_m"])
    for road, distance in ctx.geo.nearest_roads(lon, lat, within_m=200.0, k=3):
        facilities.append(
            {"name": getattr(road, "name", "未知道路"), "kind": "road", "distance_m": round(distance)}
        )
    return ev, data_type, known_gaps, facilities[:10]


@router.get("/status", summary="大模型服务可用性（不调用模型）")
def llm_status() -> dict[str, Any]:
    try:
        Settings.from_env()
    except LLMError as exc:
        return {"available": False, "reason": str(exc)}
    return {"available": True}


@router.post("/parse-task", summary="自然语言任务解析")
def post_parse_task(body: ParseTaskIn) -> dict[str, Any]:
    task = _call_llm(parse_task, body.text.strip())
    return task.model_dump()


@router.post("/chat", summary="城市治理助手多轮问答")
def post_chat(body: ChatIn, ctx: AppContext = Depends(get_ctx)) -> dict[str, Any]:
    normalized = [(item.role, item.content.strip()) for item in body.messages]
    if any(not content for _, content in normalized):
        raise HTTPException(status_code=422, detail="对话内容不能为空")
    messages = [ChatTurn(role=role, content=content) for role, content in normalized]
    if messages[-1].role != "user":
        raise HTTPException(status_code=422, detail="最后一条消息必须来自用户")

    event_id: str | None = None
    data_type: str | None = None
    context: dict[str, Any] | None = None
    if body.event_id:
        ev, data_type, known_gaps, facilities = _load_event_context(ctx, body.event_id)
        event_id = ev["id"]
        context = {
            "data_type": data_type,
            "known_gaps": known_gaps,
            "event": _event_view(ev),
            "facilities": facilities,
        }
    answer = _call_llm(answer_chat, messages, context=context)
    return {"answer": answer, "event_id": event_id, "data_type": data_type}


@router.post("/report", summary="基于事件目录数据生成结构化研判报告")
def post_report(body: ReportIn, ctx: AppContext = Depends(get_ctx)) -> dict[str, Any]:
    ev, data_type, known_gaps, facilities = _load_event_context(ctx, body.event_id)

    report_input = {
        "data_type": data_type,
        "analysis_goal": f"评估{_TYPE_LABEL.get(ev['event_type'], '城市')}事件的影响与风险，给出处置建议",
        "event": _event_view(ev),
        "facilities": facilities,
        "known_gaps": known_gaps,
    }
    report = _call_llm(generate_report, report_input)
    result = report.model_dump()
    # 数据性质由后端事实判定，避免模型照抄错误标签或自行改写。
    result["data_classification"] = data_type
    result["event_overview"]["data_type"] = data_type
    return result
