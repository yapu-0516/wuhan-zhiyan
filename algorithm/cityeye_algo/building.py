"""建筑安全分析。

(a) SettleWatch —— 沉降监测时序（CSV：date,displacement_mm；负值表示下沉）：
    - 近 30 天 Theil–Sen 稳健斜率 → 沉降速率（mm/月，1 月按 30.44 天）；
    - 近 90 天二次多项式拟合 → 加速度（mm/月²，二阶导）；
    - 滚动中位数 + MAD 修正 z 分数（|z|>3.5）→ 异常测点；
    - 风险分级（阈值可配置，默认值为演示用工程经验值）：
        * normal：|速率| ≤ 2 mm/月；
        * watch ：|速率| > 2 mm/月，或近 30 天异常测点 ≥ 3 个；
        * warning：|速率| > 4 mm/月，或 |速率| > 2 mm/月 且同向加速度 > 0.5 mm/月²（加速沉降）。
      参考：JGJ 8-2016《建筑变形测量规范》以最后 100 d 沉降速率小于 0.01~0.04 mm/d
      （约 0.3~1.2 mm/月）作为沉降稳定判据；超过该量级数倍即应关注。实际项目须按结构类型、
      地基条件与设计允许值重新标定。
(b) ChangeScope —— 前后两时相影像变化检测：
    辐射归一化（均值/方差匹配）→ 灰度差 + Sobel 梯度差融合 → 局部均值聚合 →
    Otsu 自适应阈值（并设噪声自适应下限 中位数+8σ_MAD，防止"无变化时强行二分"）→ 形态学 →
    连通域 → 变化区域与变化率。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Sequence

import numpy as np
from PIL import Image

from . import imgproc as ip
from . import timeseries as ts
from .base import AlgorithmMeta, AnalysisResult, Artifact, Detection, InputError, clamp01
from .render import Chart, HLine, Line, Marker, annotate_image, render_chart

DAYS_PER_MONTH = 30.44
RISK_CN = {"normal": "正常", "watch": "关注", "warning": "预警"}


@dataclass(frozen=True)
class SettlementThresholds:
    watch_rate: float = 2.0         # mm/月
    warning_rate: float = 4.0       # mm/月
    accel_warning: float = 0.5      # mm/月²（与速率同向时视为加速沉降）
    anomaly_watch: int = 3          # 近 30 天异常测点数
    recent_days: int = 30
    accel_days: int = 90
    mad_z: float = 3.5


@dataclass
class SettlementReport:
    rate_mm_per_month: float
    overall_rate_mm_per_month: float
    acceleration: float
    cumulative_mm: float
    risk_level: str
    analysis: str
    anomalies: list[int] = field(default_factory=list)
    trend: list[float] = field(default_factory=list)


def assess_settlement(
    days: Sequence[date | datetime], disp: Sequence[float], th: SettlementThresholds | None = None
) -> SettlementReport:
    """对位移序列做沉降评估（供 CSV 分析与后端种子数据共用）。"""
    th = th or SettlementThresholds()
    y = np.asarray(disp, dtype=np.float64)
    if len(y) < 10:
        raise InputError("沉降序列至少需要 10 个观测点")
    if np.isnan(y).any():
        y = np.where(np.isnan(y), np.nanmedian(y), y)
    stamps = [d if isinstance(d, datetime) else datetime.combine(d, datetime.min.time()) for d in days]
    x = np.array([(d - stamps[0]).total_seconds() / 86400 for d in stamps], dtype=np.float64)
    end = x[-1]

    recent = x >= end - th.recent_days
    if recent.sum() < 5:
        recent = np.zeros_like(recent)
        recent[-5:] = True
    slope_recent, _ = ts.theil_sen(x[recent], y[recent])
    slope_all, icpt_all = ts.theil_sen(x, y)
    rate = slope_recent * DAYS_PER_MONTH
    overall = slope_all * DAYS_PER_MONTH

    win = x >= end - th.accel_days
    if win.sum() >= 8:
        a2 = np.polyfit(x[win], y[win], 2)[0]
        accel = 2 * a2 * DAYS_PER_MONTH**2
    else:
        accel = 0.0

    z = ts.rolling_mad_z(y, 15)
    anomalies = [int(i) for i in np.nonzero(np.abs(z) > th.mad_z)[0]]
    recent_anom = sum(1 for i in anomalies if recent[i])
    cumulative = float(y[-1] - y[0])

    mag = abs(rate)
    same_dir_accel = accel * np.sign(rate) if rate != 0 else 0.0
    direction = "沉降" if rate <= 0 else "上抬"
    if mag > th.warning_rate:
        risk = "warning"
        reason = f"超过 {th.warning_rate:g} mm/月 预警阈值"
    elif mag > th.watch_rate and same_dir_accel > th.accel_warning:
        risk = "warning"
        reason = f"超过 {th.watch_rate:g} mm/月 关注阈值且呈加速趋势（{abs(accel):.2f} mm/月²）"
    elif mag > th.watch_rate:
        risk = "watch"
        reason = f"超过 {th.watch_rate:g} mm/月 关注阈值"
    elif recent_anom >= th.anomaly_watch:
        risk = "watch"
        reason = f"近 {th.recent_days} 天出现 {recent_anom} 个异常测点，需复测确认"
    else:
        risk = "normal"
        reason = f"低于 {th.watch_rate:g} mm/月 关注阈值，变形趋于稳定"
    analysis = (
        f"近 {th.recent_days} 天{direction}速率 {mag:.1f} mm/月，{reason}；"
        f"监测期累计位移 {cumulative:+.1f} mm，全期平均速率 {abs(overall):.1f} mm/月"
    )
    trend = (icpt_all + slope_all * x).tolist()
    return SettlementReport(
        rate_mm_per_month=round(float(rate), 2),
        overall_rate_mm_per_month=round(float(overall), 2),
        acceleration=round(float(accel), 3),
        cumulative_mm=round(cumulative, 2),
        risk_level=risk,
        analysis=analysis,
        anomalies=anomalies,
        trend=[round(v, 2) for v in trend],
    )


class SettlementAnalyzer:
    meta = AlgorithmMeta(
        type="building",
        key="building.series",
        name="SettleWatch",
        version="1.0.0",
        method="Theil–Sen 稳健趋势 + 二次拟合加速度 + 滚动 MAD 异常检测 + 分级阈值",
        input_kind="csv",
    )

    def __init__(self, thresholds: SettlementThresholds | None = None) -> None:
        self.th = thresholds or SettlementThresholds()

    def analyze(self, inputs: Sequence[Path], out_dir: Path, prefix: str, **_: Any) -> AnalysisResult:
        t0 = time.perf_counter()
        table = ts.read_table(Path(inputs[0]), ["date", "displacement_mm"], min_rows=10)
        days = table.times("date")
        disp = table.floats("displacement_mm")
        assert disp is not None
        rep = assess_settlement(days, disp, self.th)
        detected = rep.risk_level != "normal"
        conf = 0.0
        if detected:
            conf = min(0.97, 0.6 + 0.3 * clamp01(abs(rep.rate_mm_per_month) / (2 * self.th.warning_rate)) + 0.05 * min(1.0, len(disp) / 120))
        anomaly_set = set(rep.anomalies)
        series = [
            {"t": d.strftime("%m-%d"), "v": round(float(v), 2), "trend": rep.trend[i], "anomaly": int(i in anomaly_set)}
            for i, (d, v) in enumerate(zip(days, disp))
        ]
        chart = Chart(
            title=f"SettleWatch  rate {rep.rate_mm_per_month:+.2f} mm/month  accel {rep.acceleration:+.2f}",
            x_labels=[p["t"] for p in series],
            lines=[
                Line([p["v"] for p in series], (155, 143, 255), "displacement (mm)"),
                Line(rep.trend, (240, 192, 80), "Theil-Sen trend", dashed=True),
            ],
            y_label="mm",
            hlines=[HLine(0.0, (120, 150, 190), "baseline")],
            markers=[Marker(i, float(disp[i])) for i in rep.anomalies],
        )
        out = render_chart(chart, out_dir / f"{prefix}_chart.png")
        metrics: dict[str, float | int | str] = {
            "rate_mm_per_month": rep.rate_mm_per_month,
            "overall_rate_mm_per_month": rep.overall_rate_mm_per_month,
            "acceleration": rep.acceleration,
            "cumulative_mm": rep.cumulative_mm,
            "anomaly_points": len(rep.anomalies),
            "risk_level": rep.risk_level,
            "samples": len(disp),
            "span_days": int((days[-1] - days[0]).days),
            "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
        }
        summary = f"风险等级：{RISK_CN[rep.risk_level]}。{rep.analysis}"
        return AnalysisResult(detected, round(conf, 3), summary, [], metrics, series, [Artifact("沉降时序与趋势", out, "chart")], rep.risk_level)


@dataclass(frozen=True)
class ChangeParams:
    analysis_side: int = 960
    abs_floor: float = 8.0         # 变化强度绝对下限（灰度级）
    noise_k: float = 8.0           # 噪声自适应下限：中位数 + k·σ（σ 由 MAD 估计）
    min_area_ratio: float = 0.002  # 最小变化区域占比
    grad_weight: float = 0.45


class ChangeDetector:
    meta = AlgorithmMeta(
        type="building",
        key="building.change",
        name="ChangeScope",
        version="1.0.0",
        method="辐射归一化 + 灰度/梯度差分融合 + Otsu 自适应阈值 + 形态学 + 连通域",
        input_kind="image_pair",
    )

    def __init__(self, params: ChangeParams | None = None) -> None:
        self.p = params or ChangeParams()

    def analyze(self, inputs: Sequence[Path], out_dir: Path, prefix: str, **_: Any) -> AnalysisResult:
        if len(inputs) != 2:
            raise InputError("变化检测需要前后两个时相的 2 张图片")
        return self.analyze_pair(Path(inputs[0]), Path(inputs[1]), out_dir / f"{prefix}_annotated.jpg")

    def analyze_pair(self, before_path: Path, after_path: Path, out_path: Path) -> AnalysisResult:
        t0 = time.perf_counter()
        p = self.p
        before, scale = ip.load_rgb(before_path, p.analysis_side)
        after_img = Image.open(after_path).convert("RGB")
        resized = after_img.size != (round(before.shape[1] / scale), round(before.shape[0] / scale))
        after = np.asarray(after_img.resize((before.shape[1], before.shape[0]), Image.BILINEAR), dtype=np.float32)
        H, W = before.shape[:2]
        n_px = H * W

        gb = ip.blur(ip.to_gray(before), 3, 2)
        ga = ip.blur(ip.to_gray(after), 3, 2)
        ga = (ga - ga.mean()) / (ga.std() + 1e-6) * gb.std() + gb.mean()  # 辐射归一化
        d_int = np.abs(gb - ga)
        sb, sa = ip.sobel_magnitude(gb) / 4.0, ip.sobel_magnitude(ga) / 4.0
        d_grad = np.abs(sb - sa)
        mag = ip.box_mean((1 - p.grad_weight) * d_int + p.grad_weight * d_grad, 9)

        med = float(np.median(mag))
        sigma = 1.4826 * float(np.median(np.abs(mag - med)))
        thr = max(ip.otsu_threshold(mag), p.abs_floor, med + p.noise_k * sigma)
        mask = ip.closing(ip.opening(mag > thr, 5), 9)
        labels, regs = ip.label_components(mask, min_area=int(p.min_area_ratio * n_px))
        orig = (round(W / scale), round(H / scale))
        dets: list[Detection] = []
        kinds: list[str] = []
        if regs:
            k = len(regs)
            m_mag = ip.region_means(labels, k, mag)
            m_ta = ip.region_means(labels, k, sa)
            m_tb = ip.region_means(labels, k, sb)
            m_ia = ip.region_means(labels, k, ga)
            m_ib = ip.region_means(labels, k, gb)
            for r in sorted(regs, key=lambda r: -r.area):
                i = r.label
                conf = clamp01(0.5 + 0.45 * (m_mag[i] - thr) / thr + 0.1 * min(1.0, r.area / (0.02 * n_px)))
                dets.append(Detection("change", min(0.97, conf), ip.scale_bbox(r.bbox, scale, orig), r.area / n_px))
                tex_ratio = (m_ta[i] + 1) / (m_tb[i] + 1)
                if tex_ratio > 1.3:
                    kinds.append("结构破损 / 杂乱堆积（纹理显著增强）")
                elif tex_ratio < 0.77:
                    kinds.append("构筑物拆除或被覆盖（纹理显著减弱）")
                else:
                    kinds.append("新增 / 改建构筑物（亮度显著变化）" if m_ia[i] > m_ib[i] else "屋面 / 立面颜色变暗（疑似过火、渗水或拆改）")
        change_ratio = float(mask.sum()) / n_px if regs else 0.0
        detected = bool(dets)
        conf = max((d.confidence for d in dets), default=0.0)
        if detected:
            summary = f"检测到 {len(dets)} 处显著变化区域，变化面积占比 {change_ratio:.1%}；最大区域变化类型初判：{kinds[0]}"
        else:
            summary = f"两时相影像无显著变化（变化强度阈值 {thr:.1f}，未发现超过最小面积的变化区域）"

        # 证据图：前后时相并排（各缩放至 640 宽），右图叠加变化掩膜
        half_w = 640
        s2 = half_w / W
        bimg = Image.fromarray(before.astype(np.uint8)).resize((half_w, round(H * s2)))
        aimg = Image.fromarray(after.astype(np.uint8)).resize((half_w, round(H * s2)))
        canvas = Image.new("RGB", (half_w * 2 + 8, bimg.height), (8, 16, 32))
        canvas.paste(bimg, (0, 0))
        mask_small = np.asarray(Image.fromarray(mask.astype(np.uint8) * 255).resize(aimg.size)) > 127
        tint = Image.new("RGB", aimg.size, (255, 64, 160))
        aimg = Image.composite(tint, aimg, Image.fromarray((mask_small * 80).astype(np.uint8)))
        canvas.paste(aimg, (half_w + 8, 0))
        k2 = s2 * scale  # 原图坐标 → 画布坐标
        pair_dets = []
        for d in dets:
            x, y, w, h = d.bbox
            box = (round(x * k2), round(y * k2), round(w * k2), round(h * k2))
            pair_dets.append(Detection(d.label, d.confidence, box))
            pair_dets.append(Detection(d.label, d.confidence, (box[0] + half_w + 8, box[1], box[2], box[3])))
        out = annotate_image(
            canvas,
            pair_dets,
            out_path,
            [f"{self.meta.name} v{self.meta.version}  BEFORE | AFTER", f"changed {change_ratio:.1%} | regions {len(dets)} | thr {thr:.1f}"],
        )
        metrics: dict[str, float | int | str] = {
            "change_ratio": round(change_ratio, 4),
            "changed_regions": len(dets),
            "threshold": round(thr, 2),
            "mean_change": round(float(mag.mean()), 2),
            "dominant_change": kinds[0] if kinds else "无",
            "resized_after": int(resized),
            "image_size": f"{orig[0]}x{orig[1]}",
            "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
        }
        return AnalysisResult(detected, round(conf, 3), summary, dets, metrics, None, [Artifact("前后时相变化标注", out, "image")], None)
