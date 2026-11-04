"""其他团队成员实现的空间分析提供方协议。

提供方只负责生成结构化时间帧；自然语言、会话、版本和可视化由本模块负责。
"""

from __future__ import annotations

from typing import Protocol

from .models import ScenarioDraft, ScenarioRun


class SpatialAnalysisProvider(Protocol):
    name: str

    def run(self, draft: ScenarioDraft, run_id: str, version_id: str) -> ScenarioRun:
        """返回带 provider、data_classification、frames 和 limitations 的推演结果。"""
        ...


class ExternalAnalysisUnavailable(RuntimeError):
    """外部专业分析未配置或不可用；不得用未标记模拟结果替代。"""
