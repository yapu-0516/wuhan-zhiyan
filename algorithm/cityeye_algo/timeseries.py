"""时序分析公共工具：CSV 读取、时间解析、稳健统计与短临预测。"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Sequence

import numpy as np

from .base import InputError

_TIME_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y/%m/%d %H:%M:%S",
    "%Y/%m/%d %H:%M",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%d",
    "%Y/%m/%d",
)


@dataclass
class Table:
    """CSV 解析结果：列名（小写）→ 原始字符串列。"""

    columns: dict[str, list[str]]
    source: str

    def __len__(self) -> int:
        return len(next(iter(self.columns.values()), []))

    def floats(self, name: str, optional: bool = False) -> np.ndarray | None:
        if name not in self.columns:
            if optional:
                return None
            raise InputError(f"{self.source} 缺少列 {name}")
        out = np.empty(len(self), dtype=np.float64)
        for i, s in enumerate(self.columns[name]):
            try:
                out[i] = float(s) if s.strip() != "" else np.nan
            except ValueError as e:
                raise InputError(f"{self.source} 第 {i + 2} 行列 {name} 不是数值：{s!r}") from e
        return out

    def times(self, name: str) -> list[datetime]:
        if name not in self.columns:
            raise InputError(f"{self.source} 缺少列 {name}")
        return parse_times(self.columns[name], self.source)


def read_header(path: Path) -> list[str]:
    """只读取表头（用于上传时快速校验）。"""
    try:
        with open(path, newline="", encoding="utf-8-sig") as f:
            row = next(csv.reader(f), [])
    except (OSError, UnicodeDecodeError) as e:
        raise InputError(f"无法读取 CSV 文件 {Path(path).name}：{e}") from e
    return [c.strip().lower() for c in row]


def read_table(path: Path, required: Sequence[str], min_rows: int = 3) -> Table:
    name = Path(path).name
    try:
        with open(path, newline="", encoding="utf-8-sig") as f:
            rows = [r for r in csv.reader(f) if any(c.strip() for c in r)]
    except (OSError, UnicodeDecodeError) as e:
        raise InputError(f"无法读取 CSV 文件 {name}：{e}") from e
    if not rows:
        raise InputError(f"CSV 文件 {name} 为空")
    header = [c.strip().lower() for c in rows[0]]
    missing = [c for c in required if c not in header]
    if missing:
        raise InputError(f"CSV 文件 {name} 缺少必需列：{', '.join(missing)}（需要 {', '.join(required)}）")
    body = rows[1:]
    if len(body) < min_rows:
        raise InputError(f"CSV 文件 {name} 数据行过少（至少 {min_rows} 行）")
    cols = {h: [r[i].strip() if i < len(r) else "" for r in body] for i, h in enumerate(header)}
    return Table(cols, name)


def parse_times(values: Sequence[str], source: str = "CSV") -> list[datetime]:
    """解析时间列。支持完整日期时间、日期，以及仅有 HH:MM 的当日时刻（跨零点自动顺延一天）。"""
    out: list[datetime] = []
    base = date(2000, 1, 1)
    day_offset = 0
    prev: datetime | None = None
    for i, raw in enumerate(values):
        s = raw.strip()
        dt = None
        for fmt in _TIME_FORMATS:
            try:
                dt = datetime.strptime(s, fmt)
                break
            except ValueError:
                continue
        if dt is None:
            for fmt in ("%H:%M:%S", "%H:%M"):
                try:
                    t = datetime.strptime(s, fmt).time()
                    dt = datetime.combine(base + timedelta(days=day_offset), t)
                    if prev is not None and dt < prev:
                        day_offset += 1
                        dt += timedelta(days=1)
                    break
                except ValueError:
                    continue
        if dt is None:
            raise InputError(f"{source} 第 {i + 2} 行时间格式无法识别：{raw!r}")
        out.append(dt)
        prev = dt
    if any(b <= a for a, b in zip(out, out[1:])):
        raise InputError(f"{source} 时间列必须严格递增")
    return out


def median_step_minutes(times: Sequence[datetime]) -> float:
    d = np.diff([t.timestamp() for t in times]) / 60.0
    return float(np.median(d)) if len(d) else 1.0


def theil_sen(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    """Theil–Sen 稳健线性回归：斜率取所有点对斜率的中位数，对离群值不敏感（崩溃点 29.3%）。"""
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    if len(x) < 2:
        return 0.0, float(y[0]) if len(y) else 0.0
    i, j = np.triu_indices(len(x), k=1)
    dx = x[j] - x[i]
    ok = dx != 0
    slope = float(np.median((y[j] - y[i])[ok] / dx[ok]))
    intercept = float(np.median(y - slope * x))
    return slope, intercept


def rolling_mad_z(y: np.ndarray, window: int = 15) -> np.ndarray:
    """滚动中位数 + MAD 的稳健 z 分数（Iglewicz & Hoaglin 修正 z：0.6745·(x−med)/MAD）。"""
    y = np.asarray(y, dtype=np.float64)
    n = len(y)
    half = window // 2
    z = np.zeros(n)
    for k in range(n):
        seg = y[max(0, k - half) : min(n, k + half + 1)]
        med = np.median(seg)
        mad = np.median(np.abs(seg - med))
        z[k] = 0.6745 * (y[k] - med) / max(mad, 1e-6)
    return z


def damped_holt(y: np.ndarray, horizon: int, alpha: float = 0.5, beta: float = 0.2, phi: float = 0.9) -> np.ndarray:
    """阻尼趋势 Holt 双指数平滑（Gardner & McKenzie, 1985），返回未来 horizon 步预测。

    阻尼系数 phi<1 使趋势随步长衰减，避免短临预测线性外推过冲。
    """
    y = np.asarray(y, dtype=np.float64)
    y = y[~np.isnan(y)]
    if len(y) == 0:
        return np.zeros(horizon)
    level, trend = y[0], (y[1] - y[0]) if len(y) > 1 else 0.0
    for v in y[1:]:
        prev_level = level
        level = alpha * v + (1 - alpha) * (level + phi * trend)
        trend = beta * (level - prev_level) + (1 - beta) * phi * trend
    out = np.empty(horizon)
    acc = 0.0
    for h in range(1, horizon + 1):
        acc += phi**h
        out[h - 1] = level + acc * trend
    return out


def moving_average(y: np.ndarray, k: int) -> np.ndarray:
    """居中滑动平均（边界按有效点数归一化）。"""
    y = np.asarray(y, dtype=np.float64)
    if k <= 1 or len(y) < 2:
        return y.copy()
    kernel = np.ones(k)
    num = np.convolve(np.nan_to_num(y), kernel, mode="same")
    den = np.convolve(np.ones_like(y), kernel, mode="same")
    return num / den


def runs_where(mask: np.ndarray) -> list[tuple[int, int]]:
    """布尔序列中连续为 True 的区间 [start, end]（闭区间）。"""
    m = np.concatenate([[False], np.asarray(mask, bool), [False]])
    d = np.diff(m.astype(np.int8))
    starts = np.nonzero(d == 1)[0]
    ends = np.nonzero(d == -1)[0] - 1
    return list(zip(starts.tolist(), ends.tolist()))


def fmt_t(t: datetime, with_date: bool = False) -> str:
    return t.strftime("%m-%d %H:%M" if with_date else "%H:%M")
