"""经典图像处理算子 —— 纯 numpy 实现（无 OpenCV / scipy 依赖）。

包含：色彩空间转换、积分图盒式滤波、二值形态学、Sobel 梯度、Otsu 阈值、
基于游程（run-length）+ 并查集的 8 邻域连通域标记。
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

from .base import InputError

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def load_rgb(path: Path, max_side: int | None = None) -> tuple[np.ndarray, float]:
    """读取图片为 float32 RGB 数组（0~255）。

    返回 (数组, 缩放系数)；缩放系数 = 分析图尺寸 / 原图尺寸，用于把检测框还原到原图坐标。
    """
    try:
        with Image.open(path) as im:
            im = im.convert("RGB")
            scale = 1.0
            if max_side and max(im.size) > max_side:
                scale = max_side / max(im.size)
                im = im.resize((max(1, round(im.width * scale)), max(1, round(im.height * scale))), Image.BILINEAR)
            return np.asarray(im, dtype=np.float32), scale
    except (OSError, ValueError) as e:
        raise InputError(f"无法读取图片 {Path(path).name}：{e}") from e


def rgb_to_ycbcr(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """ITU-R BT.601 全范围 YCbCr。"""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    y = 0.299 * r + 0.587 * g + 0.114 * b
    cb = 128.0 - 0.168736 * r - 0.331264 * g + 0.5 * b
    cr = 128.0 + 0.5 * r - 0.418688 * g - 0.081312 * b
    return y, cb, cr


def rgb_to_hsv(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """向量化 RGB→HSV。H 为角度 [0, 360)，S、V ∈ [0, 1]。"""
    x = rgb / 255.0
    r, g, b = x[..., 0], x[..., 1], x[..., 2]
    mx = x.max(axis=-1)
    mn = x.min(axis=-1)
    d = mx - mn
    s = np.where(mx > 1e-6, d / np.maximum(mx, 1e-6), 0.0)
    safe = np.maximum(d, 1e-6)
    h = np.where(
        mx == r,
        ((g - b) / safe) % 6.0,
        np.where(mx == g, (b - r) / safe + 2.0, (r - g) / safe + 4.0),
    )
    h = np.where(d > 1e-6, h * 60.0, 0.0)
    return h.astype(np.float32), s.astype(np.float32), mx.astype(np.float32)


def to_gray(rgb: np.ndarray) -> np.ndarray:
    return (0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]).astype(np.float32)


def box_sum(a: np.ndarray, k: int) -> np.ndarray:
    """k×k（奇数）窗口求和，积分图实现，复杂度与 k 无关；边界外按 0 处理。"""
    if k < 1 or k % 2 == 0:
        raise ValueError("窗口尺寸必须为正奇数")
    r = k // 2
    p = np.pad(a.astype(np.float64), ((r + 1, r), (r + 1, r)))
    ii = p.cumsum(0).cumsum(1)
    return ii[k:, k:] - ii[:-k, k:] - ii[k:, :-k] + ii[:-k, :-k]


def box_mean(a: np.ndarray, k: int) -> np.ndarray:
    """k×k 均值滤波（边界按有效像素数归一化）。"""
    ones = np.ones(a.shape, dtype=np.float64)
    return (box_sum(a, k) / box_sum(ones, k)).astype(np.float32)


def local_std(a: np.ndarray, k: int) -> np.ndarray:
    """局部标准差，衡量纹理强度。"""
    m = box_mean(a, k)
    m2 = box_mean(a.astype(np.float64) ** 2, k)
    return np.sqrt(np.maximum(m2 - m.astype(np.float64) ** 2, 0.0)).astype(np.float32)


def blur(a: np.ndarray, k: int = 5, passes: int = 3) -> np.ndarray:
    """多次盒式滤波近似高斯模糊（中心极限定理）。"""
    out = a.astype(np.float32)
    for _ in range(passes):
        out = box_mean(out, k)
    return out


def dilate(mask: np.ndarray, k: int) -> np.ndarray:
    return box_sum(mask.astype(np.float32), k) > 0.5


def erode(mask: np.ndarray, k: int) -> np.ndarray:
    return box_sum(mask.astype(np.float32), k) > k * k - 0.5


def opening(mask: np.ndarray, k: int) -> np.ndarray:
    """开运算：先腐蚀后膨胀，去除小于结构元的噪点与细线。"""
    return dilate(erode(mask, k), k)


def closing(mask: np.ndarray, k: int) -> np.ndarray:
    """闭运算：先膨胀后腐蚀，填补区域内部空洞与缝隙。"""
    return erode(dilate(mask, k), k)


def sobel_magnitude(gray: np.ndarray) -> np.ndarray:
    """Sobel 梯度幅值（边界复制填充）。"""
    p = np.pad(gray.astype(np.float32), 1, mode="edge")
    gx = (p[:-2, 2:] + 2 * p[1:-1, 2:] + p[2:, 2:]) - (p[:-2, :-2] + 2 * p[1:-1, :-2] + p[2:, :-2])
    gy = (p[2:, :-2] + 2 * p[2:, 1:-1] + p[2:, 2:]) - (p[:-2, :-2] + 2 * p[:-2, 1:-1] + p[:-2, 2:])
    return np.hypot(gx, gy).astype(np.float32)


def otsu_threshold(values: np.ndarray, bins: int = 256) -> float:
    """Otsu 最大类间方差阈值。values 为任意实数数组。"""
    v = np.asarray(values, dtype=np.float64).ravel()
    if v.size == 0:
        return 0.0
    lo, hi = float(v.min()), float(v.max())
    if hi - lo < 1e-9:
        return lo
    hist, edges = np.histogram(v, bins=bins, range=(lo, hi))
    centers = (edges[:-1] + edges[1:]) / 2
    w0 = np.cumsum(hist)
    w1 = w0[-1] - w0
    m0 = np.cumsum(hist * centers)
    mu0 = m0 / np.maximum(w0, 1)
    mu1 = (m0[-1] - m0) / np.maximum(w1, 1)
    between = w0 * w1 * (mu0 - mu1) ** 2
    # 两峰之间存在空直方格时类间方差呈平台，取平台中点（避免阈值贴近一侧峰）
    best = np.flatnonzero(between >= between.max() * (1 - 1e-9))
    return float(edges[int(round(best.mean())) + 1])


@dataclass
class Region:
    """连通域统计。bbox 为 (x, y, w, h)。"""

    label: int
    area: int
    bbox: tuple[int, int, int, int]
    centroid: tuple[float, float]

    @property
    def extent(self) -> float:
        """矩形度：面积 / 外接矩形面积（人工构筑物趋近 1，火焰等不规则目标偏低）。"""
        w, h = self.bbox[2], self.bbox[3]
        return self.area / max(1, w * h)

    @property
    def aspect(self) -> float:
        w, h = self.bbox[2], self.bbox[3]
        return max(w, h) / max(1, min(w, h))


def label_components(mask: np.ndarray, min_area: int = 1) -> tuple[np.ndarray, list[Region]]:
    """8 邻域连通域标记（游程编码 + 并查集）。

    返回 (标签图 int32，0 为背景, 区域列表)；面积小于 min_area 的区域被剔除（其像素标签置 0）。
    """
    m = np.asarray(mask, dtype=bool)
    h, w = m.shape
    padded = np.zeros((h, w + 2), dtype=np.int8)
    padded[:, 1:-1] = m
    d = np.diff(padded, axis=1)
    rows, starts = np.nonzero(d == 1)
    _, ends = np.nonzero(d == -1)
    ends = ends - 1  # 闭区间末端
    n = len(rows)
    labels = np.zeros((h, w), dtype=np.int32)
    if n == 0:
        return labels, []

    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    row_ptr = np.searchsorted(rows, np.arange(h + 1))
    s_list, e_list = starts.tolist(), ends.tolist()
    for r in range(1, h):
        a, a1 = int(row_ptr[r - 1]), int(row_ptr[r])
        b, b1 = a1, int(row_ptr[r + 1])
        while a < a1 and b < b1:
            if s_list[a] <= e_list[b] + 1 and s_list[b] <= e_list[a] + 1:
                ra, rb = find(a), find(b)
                if ra != rb:
                    parent[max(ra, rb)] = min(ra, rb)
            if e_list[a] < e_list[b]:
                a += 1
            else:
                b += 1

    roots = np.fromiter((find(i) for i in range(n)), dtype=np.int64, count=n)
    uniq, run_label = np.unique(roots, return_inverse=True)
    lengths = ends - starts + 1
    k = len(uniq)
    area = np.bincount(run_label, weights=lengths, minlength=k)
    x0 = np.full(k, w, dtype=np.int64)
    y0 = np.full(k, h, dtype=np.int64)
    x1 = np.zeros(k, dtype=np.int64)
    y1 = np.zeros(k, dtype=np.int64)
    np.minimum.at(x0, run_label, starts)
    np.minimum.at(y0, run_label, rows)
    np.maximum.at(x1, run_label, ends)
    np.maximum.at(y1, run_label, rows)
    sx = np.bincount(run_label, weights=lengths * (starts + ends) / 2.0, minlength=k)
    sy = np.bincount(run_label, weights=lengths * rows, minlength=k)

    keep = area >= min_area
    new_id = np.zeros(k, dtype=np.int32)
    new_id[keep] = np.arange(1, int(keep.sum()) + 1, dtype=np.int32)

    # 向量化回填标签图
    total = int(lengths.sum())
    run_start_flat = rows * w + starts
    offsets = np.cumsum(lengths) - lengths
    flat = np.repeat(run_start_flat, lengths) + (np.arange(total) - np.repeat(offsets, lengths))
    labels.ravel()[flat] = np.repeat(new_id[run_label], lengths)

    regions = [
        Region(
            label=int(new_id[i]),
            area=int(area[i]),
            bbox=(int(x0[i]), int(y0[i]), int(x1[i] - x0[i] + 1), int(y1[i] - y0[i] + 1)),
            centroid=(float(sx[i] / area[i]), float(sy[i] / area[i])),
        )
        for i in np.nonzero(keep)[0]
    ]
    return labels, regions


def region_means(labels: np.ndarray, count: int, values: np.ndarray) -> np.ndarray:
    """每个标签（1..count）上 values 的均值，返回长度 count+1 的数组（下标 0 为背景）。"""
    flat = labels.ravel()
    s = np.bincount(flat, weights=values.ravel().astype(np.float64), minlength=count + 1)
    c = np.bincount(flat, minlength=count + 1)
    return s / np.maximum(c, 1)


def region_stds(labels: np.ndarray, count: int, values: np.ndarray) -> np.ndarray:
    mean = region_means(labels, count, values)
    mean2 = region_means(labels, count, values.astype(np.float64) ** 2)
    return np.sqrt(np.maximum(mean2 - mean**2, 0.0))


def scale_bbox(bbox: tuple[int, int, int, int], scale: float, size: tuple[int, int]) -> tuple[int, int, int, int]:
    """把分析图上的 bbox 还原到原图坐标（scale = 分析图 / 原图），并裁剪到原图范围。"""
    if scale == 1.0:
        return bbox
    x, y, w, h = (v / scale for v in bbox)
    W, H = size
    x0, y0 = max(0, int(round(x))), max(0, int(round(y)))
    return x0, y0, min(W - x0, int(round(w))), min(H - y0, int(round(h)))
