"""使用固定演示数据生成结构化报告。"""

from __future__ import annotations

from .client import LLMError
from .demo_tools import get_demo_event, list_demo_facilities
from .report_generator import generate_report


def build_input() -> dict:
    return {
        "data_type": "示例数据",
        "analysis_goal": "分析火灾对周边医院和道路的影响",
        "event": get_demo_event("DEMO-FIRE-001"),
        "facilities": list_demo_facilities("江汉路", "hospital")["facilities"]
        + list_demo_facilities("江汉路", "road")["facilities"],
        "known_gaps": ["火势规模", "人员伤亡", "周边交通状态", "医院接诊能力"],
    }


def main() -> None:
    try:
        report = generate_report(build_input())
    except LLMError as exc:
        raise SystemExit(f"报告生成失败：{exc}") from exc
    print(report.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
