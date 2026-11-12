"""FlameNet-Lite：基于色彩规则的火焰 / 烟雾检测（经典方法，无深度学习）。

流程：
1. 火焰候选像素 = YCbCr 规则 ∧ RGB/HSV 规则
   - YCbCr（Celik & Demirel, 2009）：Y>Cb，Cr>Cb，Y>Ȳ，Cb<C̄b，Cr>C̄r，|Cb−Cr|≥τ；
   - RGB/HSV（Chen et al., 2004）：R>R_T，R≥G>B，S≥(255−R)·S_T/R_T；
   - 高亮"焰心"像素（黄白色、饱和度低、Cb−Cr 差小，色彩规则会漏掉）在邻近候选时并入。
2. 形态学开运算去噪、闭运算补洞，8 邻域连通域分析，剔除过小区域。
3. 区域级校验（抑制红/橙色屋顶、橙色车辆等误报）：
   - 焰心占比：真实火焰存在黄白高亮核心，红瓦屋顶 / 车漆没有；
   - 亮度纹理：火焰内部亮度起伏剧烈，人工涂层均匀；
   - 形状：火焰轮廓不规则（矩形度低），屋顶与车辆接近矩形；
   - 规则一致率与区域平均红色强度。
   区域置信度为以上因子的加权和（焰心与纹理权重最高，二者对红瓦屋面 / 车漆区分度最强），
   超过阈值且焰心占比达标才判为火焰。
4. 烟雾得分：与火焰相连的"低饱和、偏亮、低纹理"灰雾连通域占火点邻域的比例，扣除全图背景同类像素占比。
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from . import imgproc as ip
from .base import AlgorithmMeta, AnalysisResult, Artifact, Detection, clamp01
from .render import annotate_image


@dataclass(frozen=True)
class FireParams:
    analysis_side: int = 960      # 分析分辨率（长边像素）
    tau: float = 40.0             # |Cb−Cr| 阈值（Celik 2009）
    r_t: float = 135.0            # R 分量阈值（Chen 2004 推荐 115~135）
    s_t: float = 60.0             # 饱和度阈值（Chen 2004 推荐 55~65）
    min_area_ratio: float = 0.0004  # 最小火焰区域占比（0.04%）
    min_core_ratio: float = 0.03  # 区域内焰心像素最低占比
    accept_conf: float = 0.55     # 区域置信度阈值


class FireDetector:
    meta = AlgorithmMeta(
        type="fire",
        key="fire.image",
        name="FlameNet-Lite",
        version="1.2.0",
        method="YCbCr+HSV 火焰色彩规则 + 形态学 + 连通域分析 + 焰心/纹理/形状校验 + 烟雾邻域分析",
        input_kind="image",
    )

    def __init__(self, params: FireParams | None = None) -> None:
        self.p = params or FireParams()

    def analyze(self, inputs: Sequence[Path], out_dir: Path, prefix: str, **_: Any) -> AnalysisResult:
        return self.analyze_image(Path(inputs[0]), out_dir / f"{prefix}_annotated.jpg")

    def analyze_image(self, path: Path, out_path: Path) -> AnalysisResult:
        t0 = time.perf_counter()
        p = self.p
        rgb, scale = ip.load_rgb(path, p.analysis_side)
        H, W = rgb.shape[:2]
        n_px = H * W
        R, G, B = rgb[..., 0], rgb[..., 1], rgb[..., 2]
        Y, Cb, Cr = ip.rgb_to_ycbcr(rgb)
        _, S, V = ip.rgb_to_hsv(rgb)

        ycc = (Y > Cb) & (Cr > Cb) & (Y > Y.mean()) & (Cb < Cb.mean()) & (Cr > Cr.mean()) & (np.abs(Cb - Cr) >= p.tau)
        rgb_rule = (R > p.r_t) & (R >= G) & (G > B) & (S * 255.0 >= (255.0 - R) * p.s_t / p.r_t)
        candidate = ycc & rgb_rule
        hot = (Y > 205) & (R > 235) & (G > 165) & (B < 235) & (R >= G)
        flame = candidate | (hot & ip.dilate(candidate, 9))
        flame = ip.closing(ip.opening(flame, 3), 7)

        min_area = max(30, int(p.min_area_ratio * n_px))
        labels, regions = ip.label_components(flame, min_area=min_area)
        k = len(regions)
        accepted: list[tuple[ip.Region, float, dict[str, float]]] = []
        best_candidate = 0.0
        if k:
            core_frac = ip.region_means(labels, k, hot.astype(np.float32))
            agree = ip.region_means(labels, k, candidate.astype(np.float32))
            mean_r = ip.region_means(labels, k, R)
            std_y = ip.region_stds(labels, k, Y)
            for reg in regions:
                i = reg.label
                f = {
                    "core": float(core_frac[i]),
                    "agree": float(agree[i]),
                    "mean_r": float(mean_r[i]),
                    "std_y": float(std_y[i]),
                    "extent": reg.extent,
                }
                s_core = clamp01(f["core"] / 0.15)
                s_tex = clamp01((f["std_y"] - 10.0) / 30.0)
                s_shape = clamp01((0.92 - f["extent"]) / 0.40)
                s_color = clamp01((f["mean_r"] - 160.0) / 80.0)
                s_area = clamp01(reg.area / (0.01 * n_px))
                conf = 0.34 * s_core + 0.26 * s_tex + 0.12 * f["agree"] + 0.12 * s_color + 0.08 * s_shape + 0.08 * s_area
                best_candidate = max(best_candidate, conf)
                if f["core"] >= p.min_core_ratio and conf >= p.accept_conf:
                    accepted.append((reg, conf, f))

        flame_union = np.isin(labels, [r.label for r, _, _ in accepted]) if accepted else np.zeros((H, W), bool)
        smoke_score, smoke_regions = self._smoke(rgb, S, V, flame_union, n_px)

        orig_size = (round(W / scale), round(H / scale))
        detections: list[Detection] = []
        for reg, conf, _ in sorted(accepted, key=lambda a: -a[0].area):
            detections.append(
                Detection("flame", min(0.99, conf), ip.scale_bbox(reg.bbox, scale, orig_size), reg.area / n_px)
            )
        for reg in smoke_regions:
            detections.append(
                Detection("smoke", clamp01(0.4 + 0.6 * smoke_score), ip.scale_bbox(reg.bbox, scale, orig_size), reg.area / n_px)
            )

        flame_ratio = float(flame_union.sum()) / n_px
        detected = bool(accepted)
        confidence = min(0.99, max((c for _, c, _ in accepted), default=0.0) + 0.06 * smoke_score) if detected else 0.0
        n_rejected = k - len(accepted)
        max_ratio = max((r.area / n_px for r, _, _ in accepted), default=0.0)
        if detected:
            smoke_txt = "伴随明显烟雾特征" if smoke_score >= 0.35 else ("可见少量烟雾" if smoke_score >= 0.15 else "未见明显烟雾")
            summary = f"检测到 {len(accepted)} 处火焰区域，最大区域占画面 {max_ratio:.1%}，{smoke_txt}"
        elif k:
            summary = f"未检测到火情：{k} 个暖色候选区域均未通过焰心 / 纹理 / 形状校验（疑似红色屋顶、车辆等）"
        else:
            summary = "未检测到火焰色彩特征"

        elapsed = (time.perf_counter() - t0) * 1000
        metrics: dict[str, float | int | str] = {
            "flame_area_ratio": round(flame_ratio, 5),
            "smoke_score": round(smoke_score, 3),
            "flame_regions": len(accepted),
            "rejected_candidates": n_rejected,
            "best_candidate_score": round(best_candidate, 3),
            "candidate_pixel_ratio": round(float(candidate.mean()), 5),
            "image_size": f"{orig_size[0]}x{orig_size[1]}",
            "elapsed_ms": round(elapsed, 1),
        }
        banner = [
            f"{self.meta.name} v{self.meta.version}",
            f"flame {flame_ratio:.2%} | regions {len(accepted)} | smoke {smoke_score:.2f}",
            "FIRE DETECTED" if detected else "no fire",
        ]
        out = annotate_image(path, detections, out_path, banner)
        return AnalysisResult(
            detected=detected,
            confidence=round(confidence, 3),
            summary=summary,
            detections=detections,
            metrics=metrics,
            artifacts=[Artifact("标注结果", out, "image")],
            level=None,
        )

    def _smoke(
        self, rgb: np.ndarray, S: np.ndarray, V: np.ndarray, flame: np.ndarray, n_px: int
    ) -> tuple[float, list[ip.Region]]:
        """火点邻域烟羽分析，返回 (烟雾得分 0~1, 烟雾区域)。无火焰时不评估烟雾。

        烟羽像素：低饱和、比全图中位亮度更亮、低纹理（烟雾遮挡使下垫面细节模糊）。只统计与火焰区域相连的
        灰雾连通域（烟羽从火点升起并顺风扩散），并扣除全图背景中同类像素的占比（浅色屋面、地面）。
        """
        if not flame.any():
            return 0.0, []
        H, W = flame.shape
        texture = ip.local_std(ip.to_gray(rgb), 9)
        v_floor = max(0.30, float(np.median(V)) + 0.12)  # 相对全图偏亮（兼容夜间场景）
        smoke_like = (S < 0.20) & (V > v_floor) & (V < 0.96) & (texture < 7.0)
        reach = int(0.16 * min(H, W)) | 1
        near = ip.dilate(flame, reach)
        ring = near & ~flame
        if not ring.any():
            return 0.0, []
        lab, regs = ip.label_components(smoke_like & ring, min_area=int(0.002 * n_px))
        touch = ip.dilate(flame, 31) & ~flame  # 火焰外缘辉光区饱和度高，放宽相连判定范围
        attached = [r for r in regs if touch[lab == r.label].any()]
        plume_frac = sum(r.area for r in attached) / float(ring.sum())
        bg_frac = float(smoke_like[~near].mean()) if (~near).any() else 0.0
        score = clamp01((plume_frac - 0.5 * bg_frac) / 0.5)
        regs_out = sorted(attached, key=lambda r: -r.area)[:2] if score >= 0.15 else []
        return score, regs_out
