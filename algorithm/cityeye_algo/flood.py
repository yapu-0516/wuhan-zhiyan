"""城市内涝分析。

(a) AquaLevel —— 积水监测时序（CSV：time,water_level_cm[,rainfall_mm]）：
    - 分级阈值（演示默认值，可配置）：15 cm 影响通行、27 cm 危及车辆（约小汽车排气管 / 半轮高度）、
      40 cm 严重积水；
    - 涨水速率：滑动 10 分钟水位差（cm/10min）；
    - 雨洪响应：降雨序列与水位增量的互相关，取相关最大的滞后时间；
    - 预测：ARX(1) 降雨-径流模型 L_t = a·L_{t−1} + b·R_{t−lag} + c（最小二乘），
      利用"已降雨但尚未汇流"的滞后降雨外推未来水位（滞后窗口之外假设无新增降雨）；
      无降雨列或模型不稳定时退化为阻尼 Holt 平滑。
(b) AquaSeg —— 积水影像分割：
    低纹理（局部标准差）× 水体色彩似然（浑浊泥水的黄褐色调 / 邻近泥水的灰蓝反光）
    → Otsu 自适应阈值（设绝对下限）→ 形态学 → 连通域 → 积水范围占比。
    注意：单张影像只能估计积水范围，无法估计水深。
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from . import imgproc as ip
from . import timeseries as ts
from .base import AlgorithmMeta, AnalysisResult, Artifact, Detection, InputError, clamp01
from .render import Bars, Chart, HLine, Line, annotate_image, render_chart

FLOOD_LEVEL_CN = {"none": "无明显积水", "minor": "轻度积水", "moderate": "中度积水", "severe": "严重积水"}


@dataclass(frozen=True)
class FloodThresholds:
    passable_cm: float = 15.0   # 影响通行
    vehicle_cm: float = 27.0    # 危及车辆
    severe_cm: float = 40.0     # 严重积水

    def level(self, cm: float) -> str:
        if cm >= self.severe_cm:
            return "severe"
        if cm >= self.vehicle_cm:
            return "moderate"
        if cm >= self.passable_cm:
            return "minor"
        return "none"


class WaterLevelAnalyzer:
    meta = AlgorithmMeta(
        type="flood",
        key="flood.series",
        name="AquaLevel",
        version="1.0.0",
        method="分级水位阈值 + 涨水速率 + 雨洪互相关滞后 + ARX 降雨-径流预测",
        input_kind="csv",
    )

    def __init__(self, thresholds: FloodThresholds | None = None) -> None:
        self.th = thresholds or FloodThresholds()

    def analyze(self, inputs: Sequence[Path], out_dir: Path, prefix: str, **params: Any) -> AnalysisResult:
        table = ts.read_table(Path(inputs[0]), ["time", "water_level_cm"])
        level = table.floats("water_level_cm")
        assert level is not None
        return self.analyze_series(
            table.times("time"), level, out_dir / f"{prefix}_chart.png", rain=table.floats("rainfall_mm", optional=True), **params
        )

    def analyze_series(
        self,
        times: Sequence[datetime],
        level: np.ndarray,
        chart_path: Path | None,
        rain: np.ndarray | None = None,
        site_name: str = "",
        forecast_min: float = 60.0,
    ) -> AnalysisResult:
        t0 = time.perf_counter()
        th = self.th
        L = np.asarray(level, dtype=np.float64)
        if np.isnan(L).all():
            raise InputError("水位列全部为空")
        L = np.where(np.isnan(L), np.nanmedian(L), np.clip(L, 0, None))
        n = len(L)
        step = ts.median_step_minutes(times)
        R = None if rain is None or np.isnan(rain).all() else np.nan_to_num(np.asarray(rain, dtype=np.float64))

        imax = int(np.argmax(L))
        w = max(1, int(round(10 / step)))
        rise = np.zeros(n)
        rise[w:] = (L[w:] - L[:-w]) / (w * step) * 10.0
        k_tail = max(3, int(round(15 / step)))
        tail_slope, _ = ts.theil_sen(np.arange(min(n, k_tail)) * step, L[-k_tail:])
        tail_rate = tail_slope * 10.0
        trend = "上涨" if tail_rate > 0.3 else ("回落" if tail_rate < -0.3 else "平稳")

        lag_steps, lag_corr = 0, 0.0
        if R is not None and R.sum() > 0:
            dL = np.diff(L, prepend=L[0])
            max_lag = min(int(180 / step), n // 2)
            best = (-1.0, 0)
            for lag in range(0, max_lag + 1):
                a, b = R[: n - lag], dL[lag:]
                if a.std() < 1e-9 or b.std() < 1e-9:
                    continue
                c = float(np.corrcoef(a, b)[0, 1])
                if c > best[0]:
                    best = (c, lag)
            lag_corr, lag_steps = best

        horizon = int(np.clip(round(forecast_min / step), 1, 180))
        fc, model = self._forecast(L, R, lag_steps, horizon)
        fc_times = [times[-1] + timedelta(minutes=step * (h + 1)) for h in range(horizon)]
        fc_peak_i = int(np.argmax(fc))
        fc_peak = float(fc[fc_peak_i])

        obs_max = float(L[imax])
        worst = max(obs_max, fc_peak)
        lvl = th.level(worst)
        detected = worst >= th.passable_cm
        mins = {c: float((L >= c).sum() * step) for c in (th.passable_cm, th.vehicle_cm, th.severe_cm)}
        with_date = (times[-1] - times[0]).total_seconds() > 86400

        name = site_name or "监测点"
        parts = [f"{name}最高积水 {obs_max:.1f} cm（{ts.fmt_t(times[imax], with_date)}）"]
        if obs_max >= th.passable_cm:
            hit = th.severe_cm if obs_max >= th.severe_cm else th.vehicle_cm if obs_max >= th.vehicle_cm else th.passable_cm
            tag = {th.severe_cm: "严重积水", th.vehicle_cm: "危及车辆", th.passable_cm: "影响通行"}[hit]
            parts.append(f"超过 {hit:g} cm {tag}阈值，≥{th.passable_cm:g} cm 持续 {mins[th.passable_cm]:.0f} 分钟")
        parts.append(f"最大涨水速率 {rise.max():.1f} cm/10min，当前水位 {L[-1]:.1f} cm（{trend}）")
        if R is not None and lag_corr > 0.2:
            parts.append(f"降雨-积水响应滞后约 {lag_steps * step:.0f} 分钟（相关系数 {lag_corr:.2f}）")
        parts.append(f"预计未来 {horizon * step:.0f} 分钟峰值 {fc_peak:.1f} cm（{model}）")
        summary = "；".join(parts)

        conf = 0.0
        if detected:
            conf = min(0.97, 0.7 + 0.25 * clamp01((worst - th.passable_cm) / (th.severe_cm - th.passable_cm)))
        metrics: dict[str, float | int | str] = {
            "max_level_cm": round(obs_max, 1),
            "max_time": ts.fmt_t(times[imax], with_date),
            "current_level_cm": round(float(L[-1]), 1),
            "trend": trend,
            "minutes_over_15cm": round(mins[th.passable_cm], 1),
            "minutes_over_27cm": round(mins[th.vehicle_cm], 1),
            "minutes_over_40cm": round(mins[th.severe_cm], 1),
            "max_rise_cm_per_10min": round(float(rise.max()), 2),
            "forecast_peak_cm": round(fc_peak, 1),
            "forecast_peak_time": ts.fmt_t(fc_times[fc_peak_i], with_date),
            "forecast_model": model,
            "level": lvl,
            "samples": n,
            "step_min": round(step, 2),
        }
        if R is not None:
            metrics["total_rainfall_mm"] = round(float(R.sum()), 1)
            metrics["max_rain_intensity_mm_h"] = round(float(R.max() / step * 60), 1)
            metrics["response_lag_min"] = round(lag_steps * step, 1)
            metrics["lag_correlation"] = round(lag_corr, 3)

        stride = max(1, n // 240)
        series: list[dict[str, Any]] = []
        for i in range(0, n, stride):
            row: dict[str, Any] = {"t": ts.fmt_t(times[i], with_date), "v": round(float(L[i]), 1), "kind": "observed"}
            if R is not None:
                row["rain"] = round(float(R[i : i + stride].sum()), 2)
            series.append(row)
        fstride = max(1, horizon // 24)
        series += [
            {"t": ts.fmt_t(fc_times[h], with_date), "v": round(float(fc[h]), 1), "kind": "forecast"} for h in range(0, horizon, fstride)
        ]

        artifacts: list[Artifact] = []
        if chart_path is not None:
            obs = [p["v"] for p in series if p["kind"] == "observed"]
            fcs = [p["v"] for p in series if p["kind"] == "forecast"]
            chart = Chart(
                title=f"AquaLevel  water level (cm)  max {obs_max:.1f}",
                x_labels=[p["t"] for p in series],
                lines=[
                    Line(obs + [None] * len(fcs), (63, 169, 255), "level"),
                    Line([None] * (len(obs) - 1) + [obs[-1]] + fcs, (255, 159, 67), "forecast", dashed=True),
                ],
                y_label="cm",
                y_range=(0.0, max(50.0, worst * 1.15)),
                hlines=[
                    HLine(th.passable_cm, (240, 192, 80), f"{th.passable_cm:g} cm"),
                    HLine(th.vehicle_cm, (255, 138, 61), f"{th.vehicle_cm:g} cm"),
                    HLine(th.severe_cm, (255, 77, 79), f"{th.severe_cm:g} cm"),
                ],
                bars=[Bars([p.get("rain") for p in series], (120, 200, 255, 110), "rain mm")] if R is not None else [],
            )
            artifacts.append(Artifact("水位时序与预测", render_chart(chart, chart_path), "chart"))
        metrics["elapsed_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        return AnalysisResult(detected, round(conf, 3), summary, [], metrics, series, artifacts, lvl)

    @staticmethod
    def _forecast(L: np.ndarray, R: np.ndarray | None, lag: int, horizon: int) -> tuple[np.ndarray, str]:
        n = len(L)
        if R is not None and R.sum() > 0 and n > lag + 8:
            t = np.arange(lag + 1, n)
            X = np.column_stack([L[t - 1], R[t - lag], np.ones(len(t))])
            coef, *_ = np.linalg.lstsq(X, L[t], rcond=None)
            a, b, c = (float(v) for v in coef)
            if 0.0 < a < 1.0 and b >= 0:
                out = np.empty(horizon)
                prev = L[-1]
                for h in range(1, horizon + 1):
                    idx = n - 1 + h - lag
                    r = R[idx] if idx < n else 0.0
                    prev = max(0.0, a * prev + b * r + c)
                    out[h - 1] = prev
                return out, "ARX 降雨-径流模型"
        return np.clip(ts.damped_holt(L, horizon), 0, None), "阻尼 Holt 平滑"


@dataclass(frozen=True)
class WaterSegParams:
    analysis_side: int = 960
    texture_k: int = 11
    score_floor: float = 0.40
    min_region_ratio: float = 0.004
    detect_ratio: float = 0.04


class WaterSegmenter:
    meta = AlgorithmMeta(
        type="flood",
        key="flood.image",
        name="AquaSeg",
        version="1.0.0",
        method="低纹理 × 水体色彩似然 + Otsu 自适应阈值 + 形态学 + 连通域",
        input_kind="image",
    )
    _RATIO_LEVEL = ((0.25, "severe"), (0.12, "moderate"), (0.04, "minor"))

    def __init__(self, params: WaterSegParams | None = None) -> None:
        self.p = params or WaterSegParams()

    def analyze(self, inputs: Sequence[Path], out_dir: Path, prefix: str, **_: Any) -> AnalysisResult:
        return self.analyze_image(Path(inputs[0]), out_dir / f"{prefix}_annotated.jpg")

    def analyze_image(self, path: Path, out_path: Path) -> AnalysisResult:
        t0 = time.perf_counter()
        p = self.p
        rgb, scale = ip.load_rgb(path, p.analysis_side)
        H, W = rgb.shape[:2]
        n_px = H * W
        gray = ip.to_gray(rgb)
        Hh, S, V = ip.rgb_to_hsv(rgb)
        texture = ip.local_std(gray, p.texture_k)

        # 软似然：纹理越低越像静水面；泥水黄褐色调；反光为与泥水相邻的低饱和亮灰蓝
        tex_like = np.clip(1.0 - (texture - 3.0) / 9.0, 0.0, 1.0)
        hue_mud = np.clip(1.0 - np.abs(Hh - 40.0) / 22.0, 0.0, 1.0)
        sat_mud = np.clip(1.0 - np.abs(S - 0.33) / 0.22, 0.0, 1.0)
        val_mud = ((V > 0.28) & (V < 0.80)).astype(np.float32)
        mud = hue_mud * sat_mud * val_mud
        B, R_ = rgb[..., 2], rgb[..., 0]
        reflect = ((S < 0.22) & (V > 0.50) & (B >= R_ - 6)).astype(np.float32)
        near_mud = ip.dilate(mud > 0.5, 21)
        color_like = np.maximum(mud, reflect * near_mud * 0.85)
        score = ip.box_mean(tex_like * color_like, 5)

        thr = max(ip.otsu_threshold(score[score > 0.05]) if (score > 0.05).any() else 1.0, p.score_floor)
        mask = ip.opening(ip.closing(score > thr, 9), 5)
        labels, regs = ip.label_components(mask, min_area=int(p.min_region_ratio * n_px))
        water = labels > 0
        ratio = float(water.sum()) / n_px
        level = next((lv for r, lv in self._RATIO_LEVEL if ratio >= r), "none")
        detected = ratio >= p.detect_ratio
        orig = (round(W / scale), round(H / scale))
        dets: list[Detection] = []
        if regs:
            k = len(regs)
            m_score = ip.region_means(labels, k, score)
            for r in sorted(regs, key=lambda r: -r.area)[:6]:
                conf = clamp01(0.45 + 0.6 * float(m_score[r.label]))
                dets.append(Detection("water", min(0.97, conf), ip.scale_bbox(r.bbox, scale, orig), r.area / n_px))
        conf = 0.0
        if detected:
            conf = min(0.96, 0.55 + 0.35 * clamp01(ratio / 0.3) + 0.1 * float(score[water].mean()))
        summary = (
            f"识别积水区域 {len(regs)} 处，积水范围占画面 {ratio:.1%}（{FLOOD_LEVEL_CN[level]}，按范围分级，影像无法估计水深）"
            if detected
            else f"未发现成片积水（疑似水面像素占比 {ratio:.1%}，低于 {p.detect_ratio:.0%} 判定阈值）"
        )
        metrics: dict[str, float | int | str] = {
            "water_area_ratio": round(ratio, 4),
            "water_regions": len(regs),
            "threshold": round(thr, 3),
            "level": level,
            "image_size": f"{orig[0]}x{orig[1]}",
            "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
        }
        out = annotate_image(
            path,
            dets,
            out_path,
            [f"{self.meta.name} v{self.meta.version}", f"water {ratio:.1%} | regions {len(regs)} | {level}"],
            overlay_mask=water,
            overlay_color=(0, 200, 255),
        )
        return AnalysisResult(detected, round(conf, 3), summary, dets, metrics, None, [Artifact("积水分割标注", out, "image")], level)
