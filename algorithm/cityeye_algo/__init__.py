"""城市智眼 CityEye 算法包：火灾 / 交通 / 建筑 / 内涝 的经典图像与时序分析算法。

仅依赖 numpy + Pillow。所有检测结论均由算法在输入数据上实际计算得出。
"""
from .base import AlgorithmMeta, AnalysisResult, Artifact, Detection, InputError
from .registry import ANALYZERS, BY_KEY, EVENT_TYPES, TYPE_CN, algorithms, file_kind, run, select, validate

__version__ = "1.0.0"

__all__ = [
    "ANALYZERS",
    "BY_KEY",
    "EVENT_TYPES",
    "TYPE_CN",
    "AlgorithmMeta",
    "AnalysisResult",
    "Artifact",
    "Detection",
    "InputError",
    "algorithms",
    "file_kind",
    "run",
    "select",
    "validate",
]
