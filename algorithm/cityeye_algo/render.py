"""算法产物渲染：检测框标注图、时序折线图（Pillow 实现）。

图中文字仅使用 ASCII，避免依赖系统中文字体；中文结论放在 API 的 summary 字段。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .base import Detection

LABEL_COLORS: dict[str, tuple[int, int, int]] = {
    "flame": (255, 48, 48),
    "smoke": (190, 190, 200),
    "vehicle": (255, 214, 0),
    "change": (255, 64, 160),
    "water": (0, 200, 255),
}

_FONT_CACHE: dict[int, ImageFont.ImageFont | ImageFont.FreeTypeFont] = {}


def font(size: int) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    if size not in _FONT_CACHE:
        try:
            _FONT_CACHE[size] = ImageFont.load_default(size=size)
        except TypeError:  # 旧版 Pillow 不支持 size 参数
            _FONT_CACHE[size] = ImageFont.load_default()
    return _FONT_CACHE[size]


def _text_box(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, fnt, fg, bg) -> None:
    x, y = xy
    l, t, r, b = draw.textbbox((x, y), text, font=fnt)
    draw.rectangle((l - 3, t - 2, r + 3, b + 2), fill=bg)
    draw.text((x, y), text, font=fnt, fill=fg)


def annotate_image(
    src: Path | Image.Image,
    detections: Sequence[Detection],
    out_path: Path,
    banner: Sequence[str] = (),
    overlay_mask: np.ndarray | None = None,
    overlay_color: tuple[int, int, int] = (0, 200, 255),
) -> Path:
    """在原图上绘制检测框、可选的半透明掩膜与左上角信息栏，保存为 JPEG。"""
    im = src.convert("RGB") if isinstance(src, Image.Image) else Image.open(src).convert("RGB")
    if overlay_mask is not None:
        m = Image.fromarray((overlay_mask.astype(np.uint8) * 90)).resize(im.size, Image.NEAREST)
        tint = Image.new("RGB", im.size, overlay_color)
        im = Image.composite(tint, im, m)
    draw = ImageDraw.Draw(im, "RGBA")
    lw = max(2, round(min(im.size) / 260))
    f_label = font(max(12, round(min(im.size) / 42)))
    crowded = len(detections) > 24  # 目标过多时只画框不写标签，避免遮挡
    for det in detections:
        x, y, w, h = det.bbox
        color = LABEL_COLORS.get(det.label, (255, 255, 255))
        draw.rectangle((x, y, x + w, y + h), outline=color + (255,), width=lw)
        if crowded:
            continue
        tag = f"{det.label.upper()} {det.confidence:.2f}"
        ty = y - f_label.size - 6 if y > f_label.size + 8 else y + 3  # type: ignore[union-attr]
        _text_box(draw, (x + 2, ty), tag, f_label, (0, 0, 0, 255), color + (230,))
    if banner:
        f_banner = font(max(12, round(min(im.size) / 40)))
        y = 8
        for line in banner:
            _text_box(draw, (10, y), line, f_banner, (255, 255, 255, 255), (8, 16, 32, 190))
            y += f_banner.size + 10  # type: ignore[union-attr]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    im.save(out_path, "JPEG", quality=86, optimize=True)
    return out_path


# ---------------------------------------------------------------- 折线图

BG = (11, 22, 41)
GRID = (36, 56, 88)
AXIS = (120, 150, 190)
TEXT = (205, 220, 240)


@dataclass
class Line:
    values: Sequence[float | None]
    color: tuple[int, int, int]
    label: str
    dashed: bool = False
    width: int = 2


@dataclass
class HLine:
    y: float
    color: tuple[int, int, int]
    label: str


@dataclass
class Band:
    y0: float
    y1: float
    color: tuple[int, int, int, int]


@dataclass
class Bars:
    """副轴柱状序列（如降雨量），按自身最大值缩放到绘图区下部 35%。"""

    values: Sequence[float | None]
    color: tuple[int, int, int, int]
    label: str


@dataclass
class Marker:
    index: int
    value: float
    color: tuple[int, int, int] = (255, 80, 80)


@dataclass
class Chart:
    title: str
    x_labels: Sequence[str]
    lines: list[Line]
    y_label: str = ""
    y_range: tuple[float, float] | None = None
    hlines: list[HLine] = field(default_factory=list)
    bands: list[Band] = field(default_factory=list)
    markers: list[Marker] = field(default_factory=list)
    bars: list[Bars] = field(default_factory=list)
    size: tuple[int, int] = (760, 360)


def _nice_range(lo: float, hi: float) -> tuple[float, float]:
    if hi - lo < 1e-9:
        hi = lo + 1.0
    pad = (hi - lo) * 0.08
    return lo - pad, hi + pad


def render_chart(chart: Chart, out_path: Path) -> Path:
    """渲染深色主题折线图（与大屏风格一致），保存为调色板 PNG（体积小）。"""
    W, H = chart.size
    left, right, top, bottom = 58, 18, 40, 46
    im = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(im, "RGBA")
    f_small, f_title = font(11), font(14)
    n = len(chart.x_labels)

    vals = [v for ln in chart.lines for v in ln.values if v is not None]
    vals += [h.y for h in chart.hlines]
    lo, hi = chart.y_range if chart.y_range else _nice_range(min(vals, default=0.0), max(vals, default=1.0))
    pw, ph = W - left - right, H - top - bottom

    def px(i: float) -> float:
        return left + (i / max(1, n - 1)) * pw

    def py(v: float) -> float:
        return top + (1 - (v - lo) / (hi - lo)) * ph

    for band in chart.bands:
        y0, y1 = py(min(hi, max(lo, band.y1))), py(min(hi, max(lo, band.y0)))
        draw.rectangle((left, y0, left + pw, y1), fill=band.color)
    for k in range(6):
        v = lo + (hi - lo) * k / 5
        y = py(v)
        draw.line((left, y, left + pw, y), fill=GRID, width=1)
        draw.text((6, y - 6), f"{v:.1f}", font=f_small, fill=AXIS)
    ticks = min(n, 7)
    for k in range(ticks):
        i = round(k * (n - 1) / max(1, ticks - 1))
        x = px(i)
        draw.line((x, top + ph, x, top + ph + 4), fill=AXIS)
        lbl = str(chart.x_labels[i])
        tw = draw.textlength(lbl, font=f_small)
        draw.text((min(W - tw - 2, max(2, x - tw / 2)), top + ph + 8), lbl, font=f_small, fill=AXIS)
    draw.rectangle((left, top, left + pw, top + ph), outline=AXIS, width=1)

    for bars in chart.bars:
        bmax = max((v for v in bars.values if v), default=0.0)
        if bmax > 0:
            bw = max(1.0, pw / max(1, n) * 0.8)
            for i, v in enumerate(bars.values):
                if v:
                    x = px(i)
                    draw.rectangle((x - bw / 2, top + ph - v / bmax * ph * 0.35, x + bw / 2, top + ph), fill=bars.color)
            draw.text((left + pw - 120, top + ph - ph * 0.35 - 14), f"{bars.label} max {bmax:.1f}", font=f_small, fill=bars.color[:3])

    for hl in chart.hlines:
        if lo <= hl.y <= hi:
            y = py(hl.y)
            for x in range(left, left + pw, 10):
                draw.line((x, y, min(x + 5, left + pw), y), fill=hl.color, width=1)
            draw.text((left + pw - draw.textlength(hl.label, font=f_small) - 4, y - 14), hl.label, font=f_small, fill=hl.color)

    for ln in chart.lines:
        pts: list[tuple[float, float] | None] = [
            (px(i), py(v)) if v is not None else None for i, v in enumerate(ln.values)
        ]
        seg: list[tuple[float, float]] = []
        for p in pts + [None]:
            if p is None:
                if len(seg) > 1:
                    if ln.dashed:
                        for j in range(0, len(seg) - 1, 2):
                            draw.line(seg[j : j + 2], fill=ln.color, width=ln.width)
                    else:
                        draw.line(seg, fill=ln.color, width=ln.width, joint="curve")
                seg = []
            else:
                seg.append(p)
    for mk in chart.markers:
        x, y = px(mk.index), py(mk.value)
        draw.ellipse((x - 4, y - 4, x + 4, y + 4), outline=mk.color, width=2)

    draw.text((left, 12), chart.title, font=f_title, fill=TEXT)
    lx = W - right
    for ln in reversed(chart.lines):
        tw = draw.textlength(ln.label, font=f_small)
        lx -= tw + 30
        draw.line((lx, 20, lx + 18, 20), fill=ln.color, width=3)
        draw.text((lx + 22, 14), ln.label, font=f_small, fill=TEXT)
    if chart.y_label:
        draw.text((6, top - 16), chart.y_label, font=f_small, fill=AXIS)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    im.convert("P", palette=Image.Palette.ADAPTIVE, colors=96).save(out_path, "PNG", optimize=True)
    return out_path
