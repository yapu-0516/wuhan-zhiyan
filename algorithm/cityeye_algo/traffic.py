"""交通运行分析。

(a) TrafficPulse —— 时序路况：
    相对速度 r = v / v_ff（v_ff 为自由流速度，缺省取限速，无限速时取序列 90 分位速度）映射为
    交通运行指数 TPI（0~10，五级划分沿用北京 DB11/T 785《城市道路交通运行评价指标体系》的
    0-2/2-4/4-6/6-8/8-10 分级），映射锚点：
        r ≥ 0.80 → 0~2 畅通；0.65~0.80 → 2~4 基本畅通；0.50~0.65 → 4~6 轻度拥堵；
        0.35~0.50 → 6~8 中度拥堵；r < 0.35 → 8~10 严重拥堵。
    （标准原文以拥堵里程比例计算路网 TPI，这里对单条道路采用相对速度近似，属工程简化。）
    在此基础上识别持续拥堵时段（TPI≥6 持续 ≥15 分钟）、峰值与早晚高峰，并用阻尼 Holt
    双指数平滑做 30~60 分钟短临预测。
(b) RoadOcc —— 航拍路面车辆占有率：
    沥青路面色彩掩膜 + 闭运算得到路面区域，局部背景差分提取车辆像素，开运算剔除车道线，
    连通域按尺寸/长宽比/矩形度筛选车辆，按路面占有率经验映射为等效 TPI。
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from . import imgproc as ip
from . import timeseries as ts
from .base import AlgorithmMeta, AnalysisResult, Artifact, Detection, InputError, clamp01
from .render import Band, Chart, Line, Marker, annotate_image, render_chart

TrafficLevel = str
LEVEL_CN: dict[str, str] = {
    "smooth": "畅通",
    "basic": "基本畅通",
    "light": "轻度拥堵",
    "moderate": "中度拥堵",
    "heavy": "严重拥堵",
}
_LEVEL_BOUNDS = ((2.0, "smooth"), (4.0, "basic"), (6.0, "light"), (8.0, "moderate"))
_RATIO_XP = np.array([0.0, 0.35, 0.50, 0.65, 0.80, 1.0])
_TPI_FP = np.array([10.0, 8.0, 6.0, 4.0, 2.0, 0.0])
_LEVEL_RGBA = {
    "smooth": (46, 212, 122, 28),
    "basic": (155, 225, 93, 28),
    "light": (240, 192, 80, 30),
    "moderate": (255, 138, 61, 32),
    "heavy": (255, 59, 59, 34),
}


def speed_to_tpi(speed: float | np.ndarray, free_flow: float | np.ndarray) -> np.ndarray:
    """速度 → TPI（0~10），支持向量化。"""
    r = np.clip(np.asarray(speed, dtype=np.float64) / np.maximum(np.asarray(free_flow, dtype=np.float64), 1e-6), 0.0, 1.0)
    return np.interp(r, _RATIO_XP, _TPI_FP)


def tpi_level(tpi: float) -> TrafficLevel:
    for bound, level in _LEVEL_BOUNDS:
        if tpi < bound:
            return level
    return "heavy"


def network_tpi(tpis: Sequence[float], lengths: Sequence[float]) -> float:
    """路网 TPI：按道路长度加权平均。"""
    w = np.asarray(lengths, dtype=np.float64)
    if w.sum() <= 0:
        return 0.0
    return float(np.average(np.asarray(tpis, dtype=np.float64), weights=w))


class TrafficSeriesAnalyzer:
    meta = AlgorithmMeta(
        type="traffic",
        key="traffic.series",
        name="TrafficPulse",
        version="1.1.0",
        method="相对速度→TPI 五级映射 + 持续拥堵时段识别 + 阻尼 Holt 短临预测",
        input_kind="csv",
    )

    def analyze(self, inputs: Sequence[Path], out_dir: Path, prefix: str, **params: Any) -> AnalysisResult:
        table = ts.read_table(Path(inputs[0]), ["time", "speed"])
        times = table.times("time")
        speeds = table.floats("speed")
        assert speeds is not None
        flows = table.floats("flow", optional=True)
        return self.analyze_series(times, speeds, out_dir / f"{prefix}_chart.png", flows=flows, **params)

    def analyze_series(
        self,
        times: Sequence[datetime],
        speeds: np.ndarray,
        chart_path: Path | None,
        flows: np.ndarray | None = None,
        free_flow_kmh: float | None = None,
        road_name: str = "",
        min_congestion_min: float = 15.0,
        smooth_min: float = 15.0,
        forecast_min: float = 60.0,
    ) -> AnalysisResult:
        t0 = time.perf_counter()
        speeds = np.asarray(speeds, dtype=np.float64)
        if np.isnan(speeds).all():
            raise InputError("速度列全部为空")
        speeds = np.where(np.isnan(speeds), np.nanmedian(speeds), speeds)
        if (speeds < 0).any():
            raise InputError("速度不能为负数")
        n = len(speeds)
        step = ts.median_step_minutes(times)
        ff = float(free_flow_kmh) if free_flow_kmh else max(20.0, float(np.percentile(speeds, 90)))
        tpi = speed_to_tpi(speeds, ff)
        k = int(np.clip(round(smooth_min / step), 1, max(1, n // 4)))
        tpi_s = ts.moving_average(tpi, k)

        periods = [
            (s, e) for s, e in ts.runs_where(tpi_s >= 6.0) if (e - s + 1) * step >= min_congestion_min
        ]
        peaks = [s + int(np.argmax(tpi_s[s : e + 1])) for s, e in periods]
        congested_min = float((tpi_s >= 6.0).sum() * step)
        slow_min = float((tpi_s >= 4.0).sum() * step)
        imax = int(np.argmax(tpi_s))
        cur = float(tpi_s[-1])
        ongoing = bool(periods and periods[-1][1] == n - 1)

        horizon = int(np.clip(round(forecast_min / step), 1, 120))
        hist = speeds[-min(n, max(12, 4 * horizon)) :]
        fc_speed = np.clip(ts.damped_holt(hist, horizon), 2.0, ff * 1.05)
        fc_tpi = speed_to_tpi(fc_speed, ff)

        span_days = (times[-1] - times[0]).total_seconds() / 86400
        with_date = span_days > 1.0
        detected = bool(periods)
        max_tpi = float(tpi_s[imax])
        level = tpi_level(cur if ongoing else max_tpi)
        confidence = 0.0
        if detected:
            confidence = clamp01(0.62 + 0.07 * (max_tpi - 6.0) + 0.12 * min(1.0, congested_min / 60.0) + 0.04 * min(1.0, n / 60))
            confidence = min(0.97, confidence)

        name = road_name or "该路段"
        fc_txt = f"预计未来 {int(horizon * step)} 分钟 TPI {fc_tpi.min():.1f}~{fc_tpi.max():.1f}"
        if detected:
            peak_i = peaks[int(np.argmax([tpi_s[p] for p in peaks]))]
            summary = (
                f"{name}识别到 {len(periods)} 个持续拥堵时段（TPI≥6 累计 {congested_min:.0f} 分钟），"
                f"峰值出现在 {ts.fmt_t(times[peak_i], with_date)}，TPI {tpi_s[peak_i]:.1f}（{LEVEL_CN[tpi_level(tpi_s[peak_i])]}），"
                f"当前 TPI {cur:.1f}（{LEVEL_CN[tpi_level(cur)]}）；{fc_txt}"
            )
        else:
            summary = (
                f"{name}未出现持续 ≥{min_congestion_min:.0f} 分钟的中度以上拥堵，平均 TPI {tpi.mean():.1f}"
                f"（{LEVEL_CN[tpi_level(float(tpi.mean()))]}），当前 TPI {cur:.1f}；{fc_txt}"
            )

        metrics: dict[str, float | int | str] = {
            "free_flow_kmh": round(ff, 1),
            "mean_speed_kmh": round(float(speeds.mean()), 1),
            "min_speed_kmh": round(float(speeds.min()), 1),
            "current_speed_kmh": round(float(speeds[-1]), 1),
            "mean_tpi": round(float(tpi.mean()), 2),
            "max_tpi": round(max_tpi, 2),
            "current_tpi": round(cur, 2),
            "current_level": tpi_level(cur),
            "congested_minutes": round(congested_min, 1),
            "slow_minutes": round(slow_min, 1),
            "congestion_periods": len(periods),
            "ongoing": int(ongoing),
            "peak_time": ts.fmt_t(times[imax], with_date),
            "forecast_tpi": round(float(fc_tpi[-1]), 2),
            "forecast_minutes": int(horizon * step),
            "samples": n,
            "step_min": round(step, 2),
        }
        if flows is not None and not np.isnan(flows).all():
            metrics["mean_flow"] = round(float(np.nanmean(flows)), 1)
            metrics["max_flow"] = round(float(np.nanmax(flows)), 1)
        for label, (h0, h1) in (("am_peak", (6, 10)), ("pm_peak", (16, 20))):
            idx = [i for i, t in enumerate(times) if h0 <= t.hour < h1]
            if idx and span_days >= 0.5:
                j = idx[int(np.argmax(tpi_s[idx]))]
                metrics[f"{label}_time"] = ts.fmt_t(times[j])
                metrics[f"{label}_tpi"] = round(float(tpi_s[j]), 2)

        # 绘图数据（降采样至 ≤240 点）+ 预测段
        stride = max(1, n // 240)
        series: list[dict[str, Any]] = [
            {"t": ts.fmt_t(times[i], with_date), "v": round(float(speeds[i]), 1), "tpi": round(float(tpi_s[i]), 2), "kind": "observed"}
            for i in range(0, n, stride)
        ]
        fc_times = [times[-1] + timedelta(minutes=step * (h + 1)) for h in range(horizon)]
        fstride = max(1, horizon // 24)
        series += [
            {"t": ts.fmt_t(fc_times[h], with_date), "v": round(float(fc_speed[h]), 1), "tpi": round(float(fc_tpi[h]), 2), "kind": "forecast"}
            for h in range(0, horizon, fstride)
        ]

        artifacts: list[Artifact] = []
        if chart_path is not None:
            obs = [p["tpi"] for p in series if p["kind"] == "observed"]
            fc = [p["tpi"] for p in series if p["kind"] == "forecast"]
            chart = Chart(
                title=f"TrafficPulse  TPI  (free-flow {ff:.0f} km/h)",
                x_labels=[p["t"] for p in series],
                lines=[
                    Line(obs + [None] * len(fc), (79, 195, 247), "TPI observed"),
                    Line([None] * (len(obs) - 1) + [obs[-1]] + fc, (255, 159, 67), "forecast", dashed=True),
                ],
                y_label="TPI",
                y_range=(0.0, 10.0),
                bands=[Band(lo, hi, _LEVEL_RGBA[lv]) for (lo, hi, lv) in ((0, 2, "smooth"), (2, 4, "basic"), (4, 6, "light"), (6, 8, "moderate"), (8, 10, "heavy"))],
                markers=[Marker(p // stride, float(tpi_s[p])) for p in peaks if p // stride < len(obs)],
            )
            artifacts.append(Artifact("TPI 时序与预测", render_chart(chart, chart_path), "chart"))

        metrics["elapsed_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        return AnalysisResult(detected, round(confidence, 3), summary, [], metrics, series, artifacts, level)


class VehicleOccupancyAnalyzer:
    meta = AlgorithmMeta(
        type="traffic",
        key="traffic.image",
        name="RoadOcc",
        version="1.0.0",
        method="沥青路面掩膜 + 局部背景差分 + 形态学 + 连通域车辆计数 → 路面占有率",
        input_kind="image",
    )
    # 路面占有率 → 等效 TPI 锚点（航拍单帧，仅作拥堵程度粗估）：
    # 车道全部排队（阻塞密度约 140 veh/km/车道，车长 4.6 m、车宽 1.85 m、车道 3.5 m）时占有率约 0.33 → TPI 10；
    # 临界密度约为阻塞密度的 1/3（占有率约 0.11）→ TPI 4，即开始进入拥堵区间。
    _OCC_XP = np.array([0.0, 0.06, 0.11, 0.17, 0.24, 0.33])

    def analyze(self, inputs: Sequence[Path], out_dir: Path, prefix: str, **_: Any) -> AnalysisResult:
        return self.analyze_image(Path(inputs[0]), out_dir / f"{prefix}_annotated.jpg")

    def analyze_image(self, path: Path, out_path: Path) -> AnalysisResult:
        t0 = time.perf_counter()
        rgb, scale = ip.load_rgb(path, 960)
        H, W = rgb.shape[:2]
        n_px = H * W
        gray = ip.to_gray(rgb)
        Hh, S, V = ip.rgb_to_hsv(rgb)

        # 1) 路面：沥青色掩膜闭运算填补车辆 / 标线空洞，再扣除"外部"非沥青区域
        #    （触及画面边缘或面积较大的连通域：人行道、地面、行道树带等），避免路面外溢；
        #    悬挑到路面上方的行道树树冠与人行道连通，因此也被归为外部。
        asphalt = (S < 0.20) & (V > 0.10) & (V < 0.50)
        # 先开运算去掉 1~2 px 的车道线与细连接，防止"车辆—标线—车辆"链式连通到画面边缘
        non_lab, non_regs = ip.label_components(ip.opening(~asphalt, 3), min_area=1)
        exterior_ids = [r.label for r in non_regs if _touches_border(r.bbox, W, H) or r.area >= 0.015 * n_px]
        exterior = np.isin(non_lab, exterior_ids)
        road_lab, _ = ip.label_components(ip.closing(asphalt, 25) & ~exterior, min_area=int(0.03 * n_px))
        road = road_lab > 0
        road_area = int(road.sum())
        orig_size = (round(W / scale), round(H / scale))
        if road_area < 0.03 * n_px:
            out = annotate_image(path, [], out_path, [f"{self.meta.name} v{self.meta.version}", "road surface not found"])
            return AnalysisResult(
                False, 0.0, "画面中未识别到足够的沥青路面区域，无法估计车辆占有率",
                metrics={"road_area_ratio": round(road_area / n_px, 4), "vehicles": 0, "image_size": f"{orig_size[0]}x{orig_size[1]}"},
                artifacts=[Artifact("标注结果", out, "image")],
            )

        # 2) 车辆像素 = 路面内非沥青且与局部路面背景差异显著的像素，剔除细线状标线
        surface = road & asphalt
        bg = (ip.box_sum(gray * surface, 41) / np.maximum(ip.box_sum(surface.astype(np.float32), 41), 1.0)).astype(np.float32)
        diff = np.abs(gray - bg)
        marking_color = ((V > 0.70) & (S < 0.25)) | ((Hh > 35) & (Hh < 65) & (S > 0.45) & (V > 0.5))
        thin = marking_color & ~ip.opening(marking_color, 5)
        thin_lab, thin_regs = ip.label_components(thin, min_area=1)
        thin_marking = np.isin(thin_lab, [r.label for r in thin_regs if r.aspect >= 3.5 or r.extent < 0.3])
        vehicle_px = road & ~asphalt & ~thin_marking & ((diff > 30) | (S > 0.35))
        vehicle_px = ip.opening(ip.closing(vehicle_px, 5), 5)
        _, regs = ip.label_components(vehicle_px, min_area=60)

        areas = [r.area for r in regs if 1.15 <= r.aspect <= 4.5 and r.extent >= 0.5]
        unit = float(np.median(areas)) if areas else 320.0
        dets: list[Detection] = []
        count = 0
        veh_area = 0
        for r in regs:
            if r.extent < 0.45 or r.area < 0.35 * unit:
                continue
            if r.area > 2.2 * unit:  # 排队车辆粘连：按单车面积估算数量
                n_cars = int(round(r.area / unit))
            elif 1.15 <= r.aspect <= 4.5:
                n_cars = 1
            else:
                continue
            count += n_cars
            veh_area += r.area
            conf = clamp01(0.55 + 0.25 * r.extent + 0.1 * min(1.0, r.area / unit))
            dets.append(Detection("vehicle", min(0.97, conf), ip.scale_bbox(r.bbox, scale, orig_size), r.area / n_px))

        occ = veh_area / road_area
        tpi_eq = float(np.interp(occ, self._OCC_XP, _TPI_FP[::-1]))
        level = tpi_level(tpi_eq)
        detected = level in ("moderate", "heavy")
        summary = (
            f"识别车辆 {count} 辆，路面占有率 {occ:.1%}，等效 TPI {tpi_eq:.1f}（{LEVEL_CN[level]}）"
            + ("，存在明显排队拥堵" if detected else "")
        )
        metrics: dict[str, float | int | str] = {
            "vehicles": count,
            "occupancy": round(occ, 4),
            "road_area_ratio": round(road_area / n_px, 4),
            "equivalent_tpi": round(tpi_eq, 2),
            "level": level,
            "image_size": f"{orig_size[0]}x{orig_size[1]}",
            "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
        }
        banner = [
            f"{self.meta.name} v{self.meta.version}",
            f"vehicles {count} | occupancy {occ:.1%} | TPI~{tpi_eq:.1f} {level}",
        ]
        out = annotate_image(path, dets, out_path, banner, overlay_mask=road, overlay_color=(0, 120, 255))
        confidence = round(clamp01(0.55 + 0.4 * min(1.0, (tpi_eq - 6.0) / 4.0 + 0.5)), 3) if detected else 0.0
        return AnalysisResult(detected, confidence, summary, dets, metrics, None, [Artifact("标注结果", out, "image")], level)


def _touches_border(bbox: tuple[int, int, int, int], W: int, H: int) -> bool:
    x, y, w, h = bbox
    return x == 0 or y == 0 or x + w >= W or y + h >= H
