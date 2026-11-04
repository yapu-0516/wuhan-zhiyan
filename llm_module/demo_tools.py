"""只用于 Tool Calling 验证的固定演示数据。"""

from __future__ import annotations

from typing import Any

DEMO_EVENTS = {
    "DEMO-FIRE-001": {
        "data_type": "示例数据",
        "event_id": "DEMO-FIRE-001",
        "event_type": "fire",
        "name": "示例商圈火情",
        "location": "武汉市江汉区示例商圈",
        "event_time": "2026-10-29 14:30",
        "status": "待核查",
        "details": "代码内固定演示记录，不是真实事件。",
    }
}

DEMO_FACILITIES = {
    "江汉路": [
        {
            "name": "示例中心医院",
            "type": "hospital",
            "distance_m": 800,
            "data_type": "示例数据",
        },
        {
            "name": "示例解放大道",
            "type": "road",
            "distance_m": 350,
            "data_type": "示例数据",
        },
    ]
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_demo_event",
            "description": "按事件编号查询一条固定在代码中的 CityEye 演示事件。",
            "parameters": {
                "type": "object",
                "properties": {
                    "event_id": {"type": "string", "description": "例如 DEMO-FIRE-001"}
                },
                "required": ["event_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_demo_facilities",
            "description": "查询固定在代码中的演示设施。目前只有江汉路。",
            "parameters": {
                "type": "object",
                "properties": {
                    "area": {"type": "string", "description": "区域名称，例如 江汉路" },
                    "facility_type": {
                        "type": "string",
                        "enum": ["hospital", "road"],
                        "description": "设施类型",
                    },
                },
                "required": ["area", "facility_type"],
                "additionalProperties": False,
            },
        },
    },
]


def get_demo_event(event_id: str) -> dict[str, Any]:
    event = DEMO_EVENTS.get(event_id)
    if event is None:
        raise ValueError(f"未找到示例事件：{event_id}")
    return event


def list_demo_facilities(area: str, facility_type: str) -> dict[str, Any]:
    facilities = DEMO_FACILITIES.get(area)
    if facilities is None:
        raise ValueError(f"没有区域 {area} 的示例设施")
    matched = [item for item in facilities if item["type"] == facility_type]
    if not matched:
        raise ValueError(f"区域 {area} 没有类型 {facility_type} 的示例设施")
    return {"data_type": "示例数据", "area": area, "facilities": matched}
