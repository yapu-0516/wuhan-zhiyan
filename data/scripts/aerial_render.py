"""俯视航拍风格场景渲染器（用于生成合成演示数据）。

以 data/geo/buildings.geojson 中的 OpenStreetMap 真实建筑轮廓为骨架，按给定中心点与地面分辨率
（米/像素）投影到图像平面，依次绘制：地面 → 植被 → 道路（含车道线）→ 建筑阴影 → 屋顶（含女儿墙、
设备）→ 车辆，再叠加火焰 / 烟雾 / 积水 / 坍塌等特效与相机后处理（噪声、暗角、色调）。

注意：渲染结果是合成图像，仅用于演示算法流程，不代表真实现场。
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterable, Sequence

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

M_PER_DEG_LAT = 110_540.0
M_PER_DEG_LON_EQ = 111_320.0

Color = tuple[int, int, int]


def value_noise(h: int, w: int, rng: np.random.Generator, cells: float = 6, octaves: int = 4, persistence: float = 0.5) -> np.ndarray:
    """分形值噪声（双三次插值的随机网格叠加），返回 [0,1] float32。"""
    out = np.zeros((h, w), np.float32)
    amp, total = 1.0, 0.0
    for o in range(octaves):
        c = cells * (2**o)
        gh = max(2, int(math.ceil(c * h / max(h, w)))) + 1
        gw = max(2, int(math.ceil(c * w / max(h, w)))) + 1
        grid = rng.random((gh, gw)).astype(np.float32)
        layer = np.asarray(Image.fromarray(grid, mode="F").resize((w, h), Image.BICUBIC), dtype=np.float32)
        out += amp * layer
        total += amp
        amp *= persistence
    out /= total
    lo, hi = float(out.min()), float(out.max())
    return (out - lo) / max(1e-6, hi - lo)


@dataclass
class BuildingShape:
    poly: list[tuple[float, float]]  # 像素坐标
    height: float
    category: str
    name: str = ""


@dataclass
class Corridor:
    """穿过画面中心的直线街道：angle 为与 x 轴夹角（度），宽度单位为米。"""

    angle: float
    lanes_per_dir: int = 3
    lane_m: float = 3.5
    median_m: float = 1.0
    sidewalk_m: float = 4.0

    @property
    def road_m(self) -> float:
        return self.lanes_per_dir * 2 * self.lane_m + self.median_m


@dataclass
class Scene:
    """渲染结果：图像（float32 RGB）与供特效使用的几何信息。"""

    img: np.ndarray
    mpp: float
    buildings: list[BuildingShape]
    building_ids: np.ndarray  # 每像素所属建筑序号+1，0 为非建筑
    road_mask: np.ndarray
    sidewalk_mask: np.ndarray
    corridor: Corridor | None = None
    meta: dict = field(default_factory=dict)

    @property
    def size(self) -> tuple[int, int]:
        return self.img.shape[1], self.img.shape[0]

    def copy(self) -> "Scene":
        return Scene(self.img.copy(), self.mpp, self.buildings, self.building_ids, self.road_mask, self.sidewalk_mask, self.corridor, dict(self.meta))

    def corridor_frame(self) -> tuple[float, float, float, float]:
        """返回 (cx, cy, cosθ, sinθ)。"""
        assert self.corridor is not None
        W, H = self.size
        t = math.radians(self.corridor.angle)
        return W / 2, H / 2, math.cos(t), math.sin(t)


class Projector:
    def __init__(self, lon0: float, lat0: float, mpp: float, size: tuple[int, int], rot_deg: float = 0.0) -> None:
        self.lon0, self.lat0, self.mpp = lon0, lat0, mpp
        self.W, self.H = size
        self.kx = M_PER_DEG_LON_EQ * math.cos(math.radians(lat0)) / mpp
        self.ky = M_PER_DEG_LAT / mpp
        self.c, self.s = math.cos(math.radians(rot_deg)), math.sin(math.radians(rot_deg))

    def __call__(self, lon: float, lat: float) -> tuple[float, float]:
        x = (lon - self.lon0) * self.kx
        y = -(lat - self.lat0) * self.ky
        return self.W / 2 + x * self.c - y * self.s, self.H / 2 + x * self.s + y * self.c


def project_buildings(features: Sequence[dict], proj: Projector, margin: float = 400) -> list[BuildingShape]:
    out = []
    for f in features:
        ring = f["geometry"]["coordinates"][0]
        pts = [proj(lon, lat) for lon, lat in ring]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        if max(xs) < -margin or min(xs) > proj.W + margin or max(ys) < -margin or min(ys) > proj.H + margin:
            continue
        p = f["properties"]
        out.append(BuildingShape(pts, float(p.get("height") or 12.0), p.get("category", "other"), p.get("name", "")))
    return out


def procedural_buildings(size: tuple[int, int], mpp: float, rng: np.random.Generator) -> list[BuildingShape]:
    """无 OSM 数据时的后备：街区网格 + 随机矩形建筑。"""
    W, H = size
    blocks: list[BuildingShape] = []
    block = 70 / mpp
    street = 14 / mpp
    y = -block / 2
    while y < H + block:
        x = -block / 2
        while x < W + block:
            n = rng.integers(2, 5)
            for _ in range(n):
                bw, bh = rng.uniform(0.25, 0.6) * block, rng.uniform(0.25, 0.6) * block
                bx, by = x + rng.uniform(0, block - bw), y + rng.uniform(0, block - bh)
                cat = str(rng.choice(["residential", "commercial", "office", "other"]))
                blocks.append(BuildingShape([(bx, by), (bx + bw, by), (bx + bw, by + bh), (bx, by + bh), (bx, by)], float(rng.uniform(9, 60)), cat))
            x += block + street
        y += block + street
    return blocks


# ------------------------------------------------------------------ 调色板

ROOF_PALETTE: dict[str, list[Color]] = {
    "residential": [(168, 166, 160), (150, 148, 146), (182, 176, 166), (132, 134, 138), (196, 192, 184)],
    "commercial": [(176, 178, 182), (120, 126, 134), (200, 200, 198), (98, 104, 112)],
    "office": [(150, 156, 164), (186, 188, 192), (110, 118, 128)],
    "public": [(170, 162, 150), (150, 150, 150), (188, 184, 176)],
    "industrial": [(110, 130, 152), (140, 150, 160), (96, 118, 140)],
    "other": [(160, 158, 154), (140, 140, 142), (178, 174, 168)],
}
TERRACOTTA: list[Color] = [(178, 84, 58), (196, 98, 62), (164, 76, 54), (204, 112, 70), (186, 90, 48)]
CAR_COLORS: list[Color] = [(235, 236, 238), (238, 238, 240), (30, 30, 34), (40, 42, 46), (150, 154, 160), (172, 176, 182), (120, 20, 24), (28, 52, 110), (96, 100, 106)]


def _jitter(c: Color, rng: np.random.Generator, amt: int = 8) -> Color:
    return tuple(int(np.clip(v + rng.integers(-amt, amt + 1), 0, 255)) for v in c)  # type: ignore[return-value]


def rotated_rect(cx: float, cy: float, length: float, width: float, angle: float) -> list[tuple[float, float]]:
    c, s = math.cos(angle), math.sin(angle)
    hl, hw = length / 2, width / 2
    return [(cx + dx * c - dy * s, cy + dx * s + dy * c) for dx, dy in ((-hl, -hw), (hl, -hw), (hl, hw), (-hl, hw))]


class SceneRenderer:
    def __init__(
        self,
        size: tuple[int, int],
        mpp: float,
        rng: np.random.Generator,
        sun_azimuth: float = 135.0,
        sun_elevation: float = 58.0,
        roof_style: str = "normal",
    ) -> None:
        self.W, self.H = size
        self.mpp = mpp
        self.rng = rng
        az = math.radians(sun_azimuth)
        k = 1.0 / math.tan(math.radians(sun_elevation)) / mpp
        # 图像坐标 x 向东、y 向南；阴影方向与太阳方位相反
        self.shadow_vec = (-math.sin(az) * k, math.cos(az) * k)
        self.roof_style = roof_style
        self._corridor: Corridor | None = None

    # -------------------------------------------------------------- 主流程
    def render(
        self,
        buildings: list[BuildingShape],
        corridor: Corridor | None = None,
        road_lines: Iterable[tuple[list[tuple[float, float]], float]] = (),
        trees: float = 1.0,
        cars: int = 25,
    ) -> Scene:
        W, H, rng = self.W, self.H, self.rng
        n1 = value_noise(H, W, rng, cells=5)
        n2 = value_noise(H, W, rng, cells=40, octaves=2)
        ground = np.empty((H, W, 3), np.float32)
        base = np.array([150, 149, 145], np.float32)
        ground[:] = base
        ground += ((n1 - 0.5) * 26)[..., None] + ((n2 - 0.5) * 14)[..., None]

        self._corridor = corridor
        sidewalk = np.zeros((H, W), bool)
        if corridor is not None:
            buildings = [b for b in buildings if not self._intersects_corridor(b, corridor)]
        canvas = Image.fromarray(np.clip(ground, 0, 255).astype(np.uint8))
        draw = ImageDraw.Draw(canvas, "RGBA")
        road_img = Image.new("L", (W, H), 0)
        rd = ImageDraw.Draw(road_img)
        for pts, width_m in road_lines:
            wpx = max(3, int(width_m / self.mpp))
            draw.line(pts, fill=(176, 174, 168), width=wpx + int(6 / self.mpp), joint="curve")
        for pts, width_m in road_lines:
            wpx = max(3, int(width_m / self.mpp))
            draw.line(pts, fill=(72, 74, 78), width=wpx, joint="curve")
            rd.line(pts, fill=255, width=wpx, joint="curve")
            self._dashed(draw, pts, (225, 225, 220), max(1, int(0.15 / self.mpp)), 6 / self.mpp, 9 / self.mpp)
        if corridor is not None:
            self._draw_corridor(draw, rd, corridor)
        road = np.asarray(road_img) > 0
        if corridor is not None:
            sidewalk = self._corridor_band(corridor.road_m / 2 + corridor.sidewalk_m) & ~road

        # 建筑 ID 图（用于设备摆放 / 特效定位）
        id_img = Image.new("I", (W, H), 0)
        idd = ImageDraw.Draw(id_img)
        for i, b in enumerate(buildings):
            idd.polygon(b.poly, fill=i + 1)
        bids = np.asarray(id_img, dtype=np.int32)

        if trees > 0:
            self._trees(draw, (bids == 0) & ~road & ~sidewalk, trees, sidewalk if corridor else None)

        # 阴影：每栋建筑的轮廓沿阴影向量平移扫掠（棱柱投影），整体半透明压暗
        sh = Image.new("L", (W, H), 0)
        sd = ImageDraw.Draw(sh)
        for b in sorted(buildings, key=lambda b: b.height):
            dx, dy = self.shadow_vec[0] * b.height, self.shadow_vec[1] * b.height
            moved = [(x + dx, y + dy) for x, y in b.poly]
            sd.polygon(moved, fill=255)
            for (x0, y0), (x1, y1) in zip(b.poly, b.poly[1:]):
                sd.polygon([(x0, y0), (x1, y1), (x1 + dx, y1 + dy), (x0 + dx, y0 + dy)], fill=255)
        shadow = np.asarray(sh.filter(ImageFilter.GaussianBlur(1.2)), np.float32) / 255.0
        arr = np.asarray(canvas, np.float32) * (1 - 0.48 * shadow[..., None])
        canvas = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
        draw = ImageDraw.Draw(canvas, "RGBA")

        if cars:
            self._scatter_cars(draw, road, cars, corridor)

        for b in sorted(buildings, key=lambda b: b.height):
            self._roof(draw, b)
        img = np.asarray(canvas, np.float32)
        # 屋面材质噪声
        roof_noise = (value_noise(H, W, rng, cells=60, octaves=2) - 0.5) * 16
        img = np.where((bids > 0)[..., None], img + roof_noise[..., None], img)
        return Scene(np.clip(img, 0, 255), self.mpp, buildings, bids, road, sidewalk, corridor)

    # -------------------------------------------------------------- 街道
    def _corridor_band(self, half_m: float) -> np.ndarray:
        cx, cy = self.W / 2, self.H / 2
        yy, xx = np.mgrid[0 : self.H, 0 : self.W].astype(np.float32)
        return np.abs(self._corridor_dist(xx, yy, cx, cy)) <= half_m / self.mpp

    def _corridor_dist(self, x, y, cx, cy):  # 到街道中心线的有符号距离（像素）
        assert self._corridor is not None
        t = math.radians(self._corridor.angle)
        return -(x - cx) * math.sin(t) + (y - cy) * math.cos(t)

    def _intersects_corridor(self, b: BuildingShape, c: Corridor) -> bool:
        half = (c.road_m / 2 + c.sidewalk_m + 1.5) / self.mpp
        d = [self._corridor_dist(x, y, self.W / 2, self.H / 2) for x, y in b.poly]
        return min(d) <= half and max(d) >= -half

    def _draw_corridor(self, draw: ImageDraw.ImageDraw, rd: ImageDraw.ImageDraw, c: Corridor) -> None:
        t = math.radians(c.angle)
        ux, uy = math.cos(t), math.sin(t)
        nx, ny = -uy, ux
        cx, cy = self.W / 2, self.H / 2
        L = math.hypot(self.W, self.H)

        def band(o0: float, o1: float) -> list[tuple[float, float]]:
            a0, a1 = o0 / self.mpp, o1 / self.mpp
            return [
                (cx - ux * L + nx * a0, cy - uy * L + ny * a0),
                (cx + ux * L + nx * a0, cy + uy * L + ny * a0),
                (cx + ux * L + nx * a1, cy + uy * L + ny * a1),
                (cx - ux * L + nx * a1, cy - uy * L + ny * a1),
            ]

        half = c.road_m / 2
        draw.polygon(band(-half - c.sidewalk_m, half + c.sidewalk_m), fill=(184, 181, 174))
        # 人行道铺装砖缝
        for k in range(-int(L), int(L), max(3, int(1.2 / self.mpp))):
            for side in (-1, 1):
                o0, o1 = side * half, side * (half + c.sidewalk_m)
                p0 = (cx + ux * k + nx * o0 / self.mpp, cy + uy * k + ny * o0 / self.mpp)
                p1 = (cx + ux * k + nx * o1 / self.mpp, cy + uy * k + ny * o1 / self.mpp)
                draw.line([p0, p1], fill=(168, 165, 158), width=1)
        draw.polygon(band(-half, half), fill=(70, 72, 76))
        rd.polygon(band(-half, half), fill=255)
        # 路缘石
        for o in (-half, half):
            draw.line([(cx - ux * L + nx * o / self.mpp, cy - uy * L + ny * o / self.mpp), (cx + ux * L + nx * o / self.mpp, cy + uy * L + ny * o / self.mpp)], fill=(205, 203, 198), width=max(1, int(0.3 / self.mpp)))
        # 中央双黄线 / 隔离带
        m = c.median_m / 2 / self.mpp
        for o in (-m * 0.6, m * 0.6):
            draw.line([(cx - ux * L + nx * o, cy - uy * L + ny * o), (cx + ux * L + nx * o, cy + uy * L + ny * o)], fill=(222, 180, 40), width=max(1, int(0.15 / self.mpp)))
        # 车道虚线
        for side in (-1, 1):
            for k in range(1, c.lanes_per_dir):
                o = side * (c.median_m / 2 + k * c.lane_m) / self.mpp
                pts = [(cx - ux * L + nx * o, cy - uy * L + ny * o), (cx + ux * L + nx * o, cy + uy * L + ny * o)]
                self._dashed(draw, pts, (228, 228, 222), max(1, int(0.15 / self.mpp)), 6 / self.mpp, 9 / self.mpp)

    @staticmethod
    def _dashed(draw: ImageDraw.ImageDraw, pts: Sequence[tuple[float, float]], color: Color, width: int, dash: float, gap: float) -> None:
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            seg = math.hypot(x1 - x0, y1 - y0)
            if seg < 1e-6:
                continue
            ux, uy = (x1 - x0) / seg, (y1 - y0) / seg
            s = 0.0
            while s < seg:
                e = min(seg, s + dash)
                draw.line([(x0 + ux * s, y0 + uy * s), (x0 + ux * e, y0 + uy * e)], fill=color, width=width)
                s += dash + gap

    def lane_center(self, c: Corridor, direction: int, lane: int) -> float:
        """车道中心线到道路中心线的偏移（像素）。direction=±1，lane 从 0 开始（0 为最内侧）。"""
        return direction * (c.median_m / 2 + (lane + 0.5) * c.lane_m) / self.mpp

    # -------------------------------------------------------------- 植被
    def _trees(self, draw: ImageDraw.ImageDraw, free: np.ndarray, density: float, sidewalk: np.ndarray | None) -> None:
        rng = self.rng
        veg = value_noise(self.H, self.W, rng, cells=4, octaves=3)
        ys, xs = np.nonzero(free & (veg > 0.62))
        n = int(len(xs) * 0.0025 * density)
        idx = rng.choice(len(xs), size=min(n, len(xs)), replace=False) if len(xs) else []
        pos = [(float(xs[i]), float(ys[i])) for i in idx]
        if sidewalk is not None and sidewalk.any():
            # 行道树：沿人行道等距
            ys2, xs2 = np.nonzero(sidewalk)
            sel = rng.choice(len(xs2), size=min(30, len(xs2)), replace=False)
            pos += [(float(xs2[i]), float(ys2[i])) for i in sel]
        for x, y in pos:
            r = rng.uniform(2.2, 4.5) / self.mpp
            sx, sy = self.shadow_vec[0] * 6, self.shadow_vec[1] * 6
            draw.ellipse((x - r + sx, y - r + sy, x + r + sx, y + r + sy), fill=(0, 0, 0, 70))
            base = _jitter((70, 104, 58), rng, 12)
            draw.ellipse((x - r, y - r, x + r, y + r), fill=base)
            for _ in range(5):
                rr = r * rng.uniform(0.3, 0.6)
                ox, oy = rng.uniform(-r * 0.5, r * 0.5, size=2)
                tone = _jitter((base[0] + 18, base[1] + 22, base[2] + 10), rng, 8)
                draw.ellipse((x + ox - rr, y + oy - rr, x + ox + rr, y + oy + rr), fill=tone)

    # -------------------------------------------------------------- 屋顶
    def _roof(self, draw: ImageDraw.ImageDraw, b: BuildingShape) -> None:
        rng = self.rng
        if self.roof_style == "terracotta" and b.height < 30 and rng.random() < 0.7:
            color = _jitter(TERRACOTTA[int(rng.integers(len(TERRACOTTA)))], rng, 10)
        else:
            pal = ROOF_PALETTE.get(b.category, ROOF_PALETTE["other"])
            color = _jitter(pal[int(rng.integers(len(pal)))], rng, 10)
        draw.polygon(b.poly, fill=color)
        edge = tuple(min(255, v + 26) for v in color)
        draw.line(b.poly, fill=edge, width=max(2, int(0.6 / self.mpp)))
        draw.line(b.poly, fill=tuple(int(v * 0.55) for v in color), width=1)
        xs, ys = [p[0] for p in b.poly], [p[1] for p in b.poly]
        area = 0.5 * abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(b.poly, b.poly[1:])))
        if area < 900:
            return
        # 屋面设备：空调外机 / 水箱 / 楼梯间
        n = int(min(14, area / 1500))
        for _ in range(n):
            px, py = rng.uniform(min(xs), max(xs)), rng.uniform(min(ys), max(ys))
            if not _point_in_poly(px, py, b.poly):
                continue
            w, h = rng.uniform(1.5, 4.5) / self.mpp, rng.uniform(1.0, 3.0) / self.mpp
            if rng.random() < 0.25:
                draw.ellipse((px, py, px + h * 1.4, py + h * 1.4), fill=(212, 214, 216), outline=(120, 120, 124))
            else:
                draw.rectangle((px + 2, py + 2, px + w + 2, py + h + 2), fill=(0, 0, 0, 60))
                draw.rectangle((px, py, px + w, py + h), fill=_jitter((196, 198, 200), rng, 14), outline=(110, 112, 116))

    # -------------------------------------------------------------- 车辆
    def car(self, draw: ImageDraw.ImageDraw, cx: float, cy: float, angle: float, kind: str = "car", color: Color | None = None) -> None:
        rng = self.rng
        dims = {"car": (4.6, 1.85), "suv": (4.9, 1.95), "bus": (12.0, 2.55), "truck": (8.5, 2.4)}[kind]
        L, Wd = dims[0] / self.mpp, dims[1] / self.mpp
        color = color or (CAR_COLORS[int(rng.integers(len(CAR_COLORS)))] if kind in ("car", "suv") else _jitter((60, 130, 90) if kind == "bus" else (200, 200, 196), rng, 10))
        sx, sy = self.shadow_vec[0] * 1.6, self.shadow_vec[1] * 1.6
        draw.polygon(rotated_rect(cx + sx, cy + sy, L, Wd, angle), fill=(0, 0, 0, 90))
        draw.polygon(rotated_rect(cx, cy, L, Wd, angle), fill=color)
        c, s = math.cos(angle), math.sin(angle)
        if kind in ("car", "suv"):
            glass = (36, 44, 56)
            draw.polygon(rotated_rect(cx + c * L * 0.18, cy + s * L * 0.18, L * 0.16, Wd * 0.8, angle), fill=glass)
            draw.polygon(rotated_rect(cx - c * L * 0.3, cy - s * L * 0.3, L * 0.1, Wd * 0.76, angle), fill=glass)
            hl = tuple(min(255, v + 30) for v in color)
            draw.polygon(rotated_rect(cx - c * L * 0.06, cy - s * L * 0.06, L * 0.3, Wd * 0.62, angle), fill=hl)
        else:
            draw.polygon(rotated_rect(cx, cy, L * 0.92, Wd * 0.8, angle), fill=tuple(min(255, v + 18) for v in color))
            for k in range(3):  # 车顶空调 / 天窗
                off = (k - 1) * L * 0.28
                draw.polygon(rotated_rect(cx + c * off, cy + s * off, L * 0.06, Wd * 0.5, angle), fill=(150, 152, 156))

    def _scatter_cars(self, draw: ImageDraw.ImageDraw, road: np.ndarray, n: int, corridor: Corridor | None) -> None:
        rng = self.rng
        if corridor is not None:
            t = math.radians(corridor.angle)
            L = math.hypot(self.W, self.H) / 2
            for _ in range(n):
                d = 1 if rng.random() < 0.5 else -1
                lane = int(rng.integers(corridor.lanes_per_dir))
                off = self.lane_center(corridor, d, lane)
                along = rng.uniform(-L, L)
                cx = self.W / 2 + math.cos(t) * along - math.sin(t) * off
                cy = self.H / 2 + math.sin(t) * along + math.cos(t) * off
                self.car(draw, cx, cy, t + (0 if d > 0 else math.pi), "car" if rng.random() < 0.85 else "suv")
            return
        ys, xs = np.nonzero(road)
        if len(xs) == 0:
            return
        for i in rng.choice(len(xs), size=min(n, len(xs)), replace=False):
            self.car(draw, float(xs[i]), float(ys[i]), float(rng.uniform(0, math.pi)))


def _point_in_poly(x: float, y: float, poly: Sequence[tuple[float, float]]) -> bool:
    inside = False
    for (x0, y0), (x1, y1) in zip(poly, poly[1:]):
        if (y0 > y) != (y1 > y) and x < (x1 - x0) * (y - y0) / (y1 - y0 + 1e-12) + x0:
            inside = not inside
    return inside


# ------------------------------------------------------------------ 特效

def _gradient(I: np.ndarray, stops: Sequence[tuple[float, Color]]) -> np.ndarray:
    xs = np.array([s[0] for s in stops])
    cols = np.array([s[1] for s in stops], np.float32)
    return np.stack([np.interp(I, xs, cols[:, k]) for k in range(3)], axis=-1)


FLAME_STOPS = [
    (0.0, (110, 18, 6)),
    (0.18, (178, 34, 10)),
    (0.36, (232, 82, 18)),
    (0.55, (255, 140, 34)),
    (0.72, (255, 196, 70)),
    (0.86, (255, 236, 160)),
    (1.0, (255, 252, 228)),
]


def add_fire(scene: Scene, cx: float, cy: float, radius: float, rng: np.random.Generator, wind_deg: float = -40.0, smoke: float = 1.0, scorch: bool = True) -> None:
    """叠加火焰（湍流噪声调制的泪滴形强度场 + 黑体色阶）、辉光、烟羽与过火焦痕。"""
    img = scene.img
    H, W = img.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    t = math.radians(wind_deg)
    u = ((xx - cx) * math.cos(t) + (yy - cy) * math.sin(t)) / radius
    v = (-(xx - cx) * math.sin(t) + (yy - cy) * math.cos(t)) / radius

    if scorch:
        burn = np.clip(1.25 - np.hypot(u / 1.5, v / 1.25), 0, 1) * (0.6 + 0.4 * value_noise(H, W, rng, cells=30, octaves=2))
        img *= (1 - 0.55 * burn)[..., None]

    if smoke > 0:
        span = 9.0
        sigma = 0.75 + 0.42 * np.clip(u, 0, None)
        plume = np.exp(-(v**2) / (2 * sigma**2)) * np.clip(1 - u / span, 0, 1) ** 0.7 * np.clip(u + 1.0, 0, 1)
        sn = value_noise(H, W, rng, cells=14, octaves=4)
        alpha = np.clip(plume * (0.45 + 0.9 * sn) * 1.05 * smoke, 0, 0.92)
        alpha = np.asarray(Image.fromarray((alpha * 255).astype(np.uint8)).filter(ImageFilter.BoxBlur(3)), np.float32) / 255.0
        dist = np.clip(u / span, 0, 1)
        # 近火源为浓黑烟，向下风向迅速稀释为灰白烟
        tone = (218 - 140 * np.exp(-dist / 0.09) + 18 * (sn - 0.5))[..., None]
        smoke_rgb = np.concatenate([tone, tone, tone + 4], axis=-1)
        hazy = np.asarray(Image.fromarray(img.astype(np.uint8)).filter(ImageFilter.GaussianBlur(4)), np.float32)
        a = alpha[..., None]
        img[:] = (img * (1 - a) + hazy * a) * (1 - a) + smoke_rgb * a

    turb = value_noise(H, W, rng, cells=max(8, W / radius * 1.4), octaves=4)
    shape = 1 - np.hypot(u / np.where(u > 0, 1.55, 0.95), v / 0.85)
    F = shape + 0.62 * (turb - 0.5)
    for _ in range(int(rng.integers(2, 4))):
        a = rng.uniform(-1.0, 1.0)
        du, dv = rng.uniform(0.3, 1.1), a * 0.7
        F = np.maximum(F, 0.75 - np.hypot((u - du) / 0.45, (v - dv) / 0.32) + 0.5 * (turb - 0.5))
    I = np.clip(F / 0.85, 0, 1) ** 0.85
    alpha_f = np.clip(F * 5.0, 0, 1)
    flame = _gradient(I, FLAME_STOPS)
    glow = np.asarray(Image.fromarray((alpha_f * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(radius * 0.9)), np.float32) / 255.0
    img += glow[..., None] * np.array([110, 52, 12], np.float32) * 0.9
    img[:] = img * (1 - alpha_f[..., None]) + flame * alpha_f[..., None]
    np.clip(img, 0, 255, out=img)


def add_collapse(scene: Scene, building_index: int, rng: np.random.Generator, fraction: float = 0.7) -> None:
    """建筑局部坍塌：屋面替换为多尺度碎块瓦砾 + 扬尘。"""
    img = scene.img
    m = scene.building_ids == building_index + 1
    ys, xs = np.nonzero(m)
    if len(xs) == 0:
        return
    cx, cy = xs.mean(), ys.mean()
    H, W = m.shape
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = math.sqrt(m.sum() / math.pi) * 1.25
    blob = (np.hypot(xx - cx, yy - cy) / r + 0.5 * (value_noise(H, W, rng, cells=20) - 0.5)) < fraction
    region = ip_dilate(m, 9) & blob
    rubble = np.zeros((H, W, 3), np.float32)
    base = value_noise(H, W, rng, cells=90, octaves=3)
    rubble[:] = np.stack([96 + 110 * base, 88 + 100 * base, 78 + 92 * base], axis=-1)
    canvas = Image.fromarray(rubble.astype(np.uint8))
    d = ImageDraw.Draw(canvas)
    for _ in range(int(region.sum() / 30)):
        i = int(rng.integers(len(xs)))
        x, y = xs[i] + rng.normal(0, 4), ys[i] + rng.normal(0, 4)
        s = rng.uniform(2, 7)
        tone = int(rng.uniform(50, 210))
        d.polygon(rotated_rect(x, y, s * rng.uniform(1, 2.5), s, rng.uniform(0, math.pi)), fill=(tone, int(tone * 0.93), int(tone * 0.85)))
    rubble = np.asarray(canvas, np.float32)
    img[region] = rubble[region]
    dust = np.asarray(Image.fromarray((region * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(14)), np.float32) / 255.0
    img[:] = img * (1 - 0.35 * dust[..., None]) + np.array([196, 188, 172], np.float32) * 0.35 * dust[..., None]


def add_new_structure(scene: Scene, cx: float, cy: float, w: float, h: float, angle: float, rng: np.random.Generator) -> None:
    """新增构筑物：蓝色彩钢瓦临建（工地常见），带波纹与阴影。"""
    canvas = Image.fromarray(scene.img.astype(np.uint8))
    d = ImageDraw.Draw(canvas, "RGBA")
    sx, sy = 10, -8
    d.polygon(rotated_rect(cx + sx, cy + sy, w, h, angle), fill=(0, 0, 0, 110))
    d.polygon(rotated_rect(cx, cy, w, h, angle), fill=(52, 104, 176))
    c, s = math.cos(angle), math.sin(angle)
    for k in np.arange(-w / 2, w / 2, 4):
        p = rotated_rect(cx + c * k, cy + s * k, 1.2, h * 0.96, angle)
        d.polygon(p, fill=(84, 138, 206))
    d.polygon(rotated_rect(cx, cy, w, h, angle) + [rotated_rect(cx, cy, w, h, angle)[0]], outline=(30, 60, 110))
    scene.img = np.asarray(canvas, np.float32)


def add_flood(scene: Scene, rng: np.random.Generator, spread_m: float = 2.5) -> np.ndarray:
    """街道积水：浑浊泥水（黄褐）+ 细小波纹 + 天空 / 建筑反光斑块，水体覆盖路面并漫上人行道。返回水体掩膜。"""
    img = scene.img
    H, W = img.shape[:2]
    c = scene.corridor
    assert c is not None
    cx, cy, ct, st = scene.corridor_frame()
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    dist = np.abs(-(xx - cx) * st + (yy - cy) * ct) * scene.mpp
    edge = c.road_m / 2 + spread_m + 2.2 * (value_noise(H, W, rng, cells=10, octaves=3) - 0.5) * 2
    canopy = (img[..., 1] > img[..., 0] + 10) & (img[..., 1] > img[..., 2] + 6)  # 行道树树冠在水面之上
    water = (dist < edge) & (scene.building_ids == 0) & ~canopy
    alpha = np.asarray(Image.fromarray((water * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.5)), np.float32)[..., None] / 255.0
    lowf = value_noise(H, W, rng, cells=6, octaves=3)
    ripple = value_noise(H, W, rng, cells=160, octaves=2)
    mud = np.stack([116 + 30 * lowf, 102 + 24 * lowf, 70 + 14 * lowf], axis=-1) + ((ripple - 0.5) * 9)[..., None]
    refl = value_noise(H, W, rng, cells=4, octaves=4)
    rmask = np.clip((refl - 0.68) * 7, 0, 1)[..., None] * 0.85
    mud = mud * (1 - rmask) + np.array([168, 176, 186], np.float32) * rmask
    # 被淹路面上的车道线 / 车辆仍隐约可见（浑水透明度低）
    img[:] = img * (1 - alpha * 0.93) + mud * alpha * 0.93
    return water


def stall_cars_in_water(scene: Scene, rng: np.random.Generator, n: int = 5) -> None:
    """水中熄火车辆：仅车顶露出水面。"""
    c = scene.corridor
    assert c is not None
    canvas = Image.fromarray(scene.img.astype(np.uint8))
    d = ImageDraw.Draw(canvas, "RGBA")
    cx, cy, ct, st = scene.corridor_frame()
    L = math.hypot(*scene.size) / 2
    for _ in range(n):
        side = 1 if rng.random() < 0.5 else -1
        off = side * (c.median_m / 2 + (int(rng.integers(c.lanes_per_dir)) + 0.5) * c.lane_m) / scene.mpp
        a = rng.uniform(-L * 0.8, L * 0.8)
        x, y = cx + ct * a - st * off, cy + st * a + ct * off
        ang = math.atan2(st, ct) + rng.normal(0, 0.15)
        col = CAR_COLORS[int(rng.integers(len(CAR_COLORS)))]
        d.polygon(rotated_rect(x, y, 3.0 / scene.mpp, 1.5 / scene.mpp, ang), fill=col)
        d.polygon(rotated_rect(x + math.cos(ang) * 0.5 / scene.mpp, y + math.sin(ang) * 0.5 / scene.mpp, 0.5 / scene.mpp, 1.3 / scene.mpp, ang), fill=(36, 44, 56))
        # 车周波纹
        d.ellipse((x - 2.6 / scene.mpp, y - 1.6 / scene.mpp, x + 2.6 / scene.mpp, y + 1.6 / scene.mpp), outline=(150, 136, 104, 120), width=1)
    scene.img = np.asarray(canvas, np.float32)


def ip_dilate(mask: np.ndarray, k: int) -> np.ndarray:
    return np.asarray(Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(k))) > 0


# ------------------------------------------------------------------ 后处理

def grade(img: np.ndarray, mode: str) -> np.ndarray:
    if mode == "golden":
        out = img * np.array([1.10, 0.97, 0.80], np.float32) + np.array([14, 4, -6], np.float32)
    elif mode == "night":
        lum = img.mean(axis=-1, keepdims=True)
        out = (0.35 * img + 0.15 * lum) * np.array([0.55, 0.62, 0.85], np.float32)
    elif mode == "overcast":
        lum = img.mean(axis=-1, keepdims=True)
        out = 0.75 * img + 0.25 * lum + 6
    else:
        out = img
    return np.clip(out, 0, 255)


def add_street_lights(scene: Scene, rng: np.random.Generator, n: int = 40) -> None:
    ys, xs = np.nonzero(scene.road_mask | scene.sidewalk_mask) if (scene.road_mask | scene.sidewalk_mask).any() else np.nonzero(scene.building_ids == 0)
    if len(xs) == 0:
        return
    H, W = scene.road_mask.shape
    light = np.zeros((H, W), np.float32)
    for i in rng.choice(len(xs), size=min(n, len(xs)), replace=False):
        light[ys[i], xs[i]] = 1.0
    halo = np.asarray(Image.fromarray((light * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(9)), np.float32) / 255.0
    halo = halo / max(1e-6, halo.max())
    scene.img += halo[..., None] * np.array([90, 70, 30], np.float32)
    np.clip(scene.img, 0, 255, out=scene.img)


def finish(img: np.ndarray, rng: np.random.Generator, noise: float = 3.0, vignette: float = 0.18, blur: float = 0.55) -> Image.Image:
    H, W = img.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.hypot((xx - W / 2) / (W / 2), (yy - H / 2) / (H / 2)) / math.sqrt(2)
    out = img * (1 - vignette * r**2)[..., None] + rng.normal(0, noise, img.shape).astype(np.float32)
    im = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
    return im.filter(ImageFilter.GaussianBlur(blur)) if blur > 0 else im
