"""生成 CityEye 演示用示例数据（确定性随机种子，可重复生成）。

输出到 data/samples/：
    fire/      无人机俯视影像（3 正例 + 2 反例，其中 1 张为红瓦屋面 + 橙色车辆的易误报场景）
    traffic/   全天车速 CSV、事故异常 CSV、路面航拍（拥堵 / 畅通）
    building/  前后时相影像对（坍塌 + 新增临建 / 无变化）、沉降 CSV（稳定 / 关注 / 加速）
    flood/     暴雨积水 CSV、小雨 CSV、积水街道航拍、干燥街道航拍
    manifest.json   示例清单（字段同 docs/api.md Sample，另含 showcase / location）

所有影像均为"合成演示数据"：以 data/geo/buildings.geojson 中 OpenStreetMap 真实建筑轮廓为骨架
渲染俯视场景，再叠加程序化火焰 / 烟雾 / 积水 / 坍塌等效果；CSV 由带噪声的物理/经验模型生成。

用法：python data/scripts/generate_samples.py
"""
from __future__ import annotations

import csv
import json
import math
import re
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Callable

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "algorithm"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from aerial_render import (  # noqa: E402
    Corridor,
    Projector,
    Scene,
    SceneRenderer,
    add_collapse,
    add_fire,
    add_flood,
    add_new_structure,
    add_street_lights,
    finish,
    grade,
    procedural_buildings,
    project_buildings,
    stall_cars_in_water,
)
from cityeye_algo.imgproc import box_sum  # noqa: E402
from cityeye_algo.render import Bars, Chart, HLine, Line, render_chart  # noqa: E402

GEO = ROOT / "data" / "geo"
OUT = ROOT / "data" / "samples"
SIZE = (960, 640)
SEED = 20261022
GENERIC_NAME = re.compile(r"(住宅|建筑|商业|办公|公共|工业|写字楼|商场)\s*B\d{3,}$")  # 无名建筑的生成名称
SYNTH = "（合成演示数据：基于 OpenStreetMap 真实建筑轮廓渲染的俯视场景，叠加程序化效果）"
SYNTH_CSV = "（合成演示数据：由带噪声的经验模型生成）"


# ------------------------------------------------------------------ 地理数据

def load_geo() -> tuple[list[dict], list[dict]]:
    def feats(name: str) -> list[dict]:
        p = GEO / name
        return json.loads(p.read_text(encoding="utf-8")).get("features", []) if p.exists() else []

    return feats("buildings.geojson"), feats("roads.geojson")


BUILDINGS, ROADS = load_geo()


def building_by_name(name: str) -> dict | None:
    return next((f for f in BUILDINGS if f["properties"].get("name") == name), None)


def building_pick(pred: Callable[[dict], bool], key: Callable[[dict], float]) -> dict | None:
    cands = [f for f in BUILDINGS if pred(f["properties"])]
    return max(cands, key=lambda f: key(f["properties"])) if cands else None


def road_anchor(name: str, near: tuple[float, float] | None = None) -> tuple[float, float, float] | None:
    """返回指定名称道路上的一点及该处走向角（度，图像坐标系 x 向东、y 向南）。"""
    best = None
    for f in ROADS:
        rname = f["properties"].get("name", "")
        if rname != name and not rname.startswith(name + "（"):  # 兼容"解放大道（一段）"等分段命名
            continue
        pts = f["geometry"]["coordinates"]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            d = 0.0 if near is None else math.hypot((mx - near[0]) * 0.86, my - near[1])
            seg = math.hypot((x1 - x0) * 0.86, y1 - y0)
            score = d - seg * 0.2
            if best is None or score < best[0]:
                ang = math.degrees(math.atan2(-(y1 - y0), (x1 - x0) * 0.86))
                best = (score, mx, my, ang)
    return None if best is None else (best[1], best[2], best[3])


def anchor(building: str | None = None, road: str | None = None, fallback: tuple[float, float] = (114.2905, 30.5895), default_angle: float = 0.0) -> tuple[float, float, float, str]:
    """解析示例点位：优先真实建筑 / 道路，缺失时用后备坐标。返回 (lon, lat, 走向角, 说明)。"""
    if road:
        r = road_anchor(road, fallback)
        if r:
            return r[0], r[1], r[2], road
    if building:
        b = building_by_name(building)
        if b:
            p = b["properties"]
            return p["longitude"], p["latitude"], default_angle, building
    return fallback[0], fallback[1], default_angle, road or building or ""


# ------------------------------------------------------------------ 场景

def road_width_m(props: dict) -> float:
    """按道路等级估计路面宽度（OSM lanes 标签缺失较多，仅在 ≥4 时采用）。"""
    lanes = props.get("lanes") or 0
    if lanes >= 4:
        return lanes * 3.3
    return {"trunk": 28.0, "primary": 24.0, "secondary": 16.0, "tertiary": 10.0}.get(props.get("highway", ""), 9.0)


def base_scene(lon: float, lat: float, rng: np.random.Generator, mpp: float = 0.3, corridor: Corridor | None = None, roof_style: str = "normal", cars: int = 22, trees: float = 1.0, rot: float = 0.0) -> Scene:
    proj = Projector(lon, lat, mpp, SIZE, rot)
    shapes = project_buildings(BUILDINGS, proj) if BUILDINGS else procedural_buildings(SIZE, mpp, rng)
    lines = []
    if corridor is None:
        for f in ROADS:
            pts = [proj(x, y) for x, y in f["geometry"]["coordinates"]]
            if any(-200 < x < SIZE[0] + 200 and -200 < y < SIZE[1] + 200 for x, y in pts):
                lines.append((pts, road_width_m(f["properties"])))
    renderer = SceneRenderer(SIZE, mpp, rng, roof_style=roof_style)
    scene = renderer.render(shapes, corridor=corridor, road_lines=lines, trees=trees, cars=cars)
    scene.meta["renderer"] = renderer
    return scene


def roof_point(scene: Scene, rng: np.random.Generator, near: tuple[float, float] | None = None, min_area: int = 2500) -> tuple[float, float]:
    """在画面内选一个足够大的屋顶上的点（靠近 near）。"""
    W, H = scene.size
    near = near or (W / 2, H / 2)
    best, best_d = None, 1e18
    ids, counts = np.unique(scene.building_ids[scene.building_ids > 0], return_counts=True)
    for i, c in zip(ids, counts):
        if c < min_area:
            continue
        ys, xs = np.nonzero(scene.building_ids == i)
        cx, cy = float(np.median(xs)), float(np.median(ys))
        if not (90 < cx < W - 90 and 90 < cy < H - 90):
            continue
        d = math.hypot(cx - near[0], cy - near[1]) + rng.uniform(0, 30)
        if d < best_d:
            best, best_d = (cx, cy), d
    return best or (W / 2, H / 2)


def save_jpg(im: Image.Image, rel: str) -> str:
    p = OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    im.save(p, "JPEG", quality=85, optimize=True)
    return rel


# ------------------------------------------------------------------ 火灾

def fire_samples(rng_for: Callable[[str], np.random.Generator]) -> list[dict]:
    out = []

    rng = rng_for("fire-01")
    lon, lat, _, loc = anchor(building="万达商业广场", fallback=(114.2857, 30.5796))
    sc = base_scene(lon, lat, rng)
    x, y = roof_point(sc, rng)
    add_fire(sc, x, y, 40, rng, wind_deg=-35, smoke=1.0)
    out.append(dict(id="fire-01", type="fire", name="无人机巡检 · 商业综合体屋顶明火", kind="image",
                    description="江汉路步行街商圈无人机俯拍，商业综合体屋面可见明火与浓烟，烟羽向西北飘散。" + SYNTH,
                    files=[save_jpg(finish(sc.img, rng), "fire/drone_fire_01.jpg")], lon=lon, lat=lat, location=loc, showcase=True))

    rng = rng_for("fire-02")
    lon, lat, _, loc = anchor(building="华港苑2栋", fallback=(114.2762, 30.5966))
    sc = base_scene(lon, lat, rng, mpp=0.28)
    x1, y1 = roof_point(sc, rng, (SIZE[0] * 0.38, SIZE[1] * 0.55), min_area=1500)
    x2, y2 = roof_point(sc, rng, (SIZE[0] * 0.70, SIZE[1] * 0.35), min_area=1500)
    add_fire(sc, x1, y1, 30, rng, wind_deg=-50, smoke=0.9)
    add_fire(sc, x2, y2, 22, rng, wind_deg=-50, smoke=0.6)
    out.append(dict(id="fire-02", type="fire", name="无人机巡检 · 居民小区多点火情", kind="image",
                    description="华港苑小区上空巡检，两栋住宅楼顶出现火点并伴随烟雾。" + SYNTH,
                    files=[save_jpg(finish(sc.img, rng), "fire/drone_fire_02.jpg")], lon=lon, lat=lat, location=loc, showcase=True))

    rng = rng_for("fire-03")
    lon, lat, _, loc = anchor(building="武铁物流", fallback=(114.2959, 30.5931))
    sc = base_scene(lon, lat, rng, cars=10)
    sc.img = grade(sc.img, "night")
    add_street_lights(sc, rng, 45)
    x, y = roof_point(sc, rng)
    add_fire(sc, x, y, 34, rng, wind_deg=-20, smoke=0.55)
    out.append(dict(id="fire-03", type="fire", name="夜间巡检 · 仓储屋面火情", kind="image",
                    description="夜间无人机巡检，物流仓储屋面出现高亮火焰区域，周边路灯为干扰光源。" + SYNTH,
                    files=[save_jpg(finish(sc.img, rng, noise=4.5), "fire/drone_fire_03_night.jpg")], lon=lon, lat=lat, location=loc, showcase=True))

    rng = rng_for("fire-04")
    lon, lat, _, loc = anchor(building="汉口汇丰银行大楼旧址", fallback=(114.2941, 30.5836))
    sc = base_scene(lon, lat, rng)
    out.append(dict(id="fire-04", type="fire", name="常规巡检 · 沿江历史街区（无火情）", kind="image",
                    description="沿江大道历史建筑群日常巡检影像，无火情，用于验证算法不误报。" + SYNTH,
                    files=[save_jpg(finish(sc.img, rng), "fire/drone_normal_01.jpg")], lon=lon, lat=lat, location=loc, showcase=False))

    rng = rng_for("fire-05")
    lon, lat, _, loc = anchor(building="八七会议会址", fallback=(114.2945, 30.5890))
    sc = base_scene(lon, lat, rng, roof_style="terracotta", cars=8)
    r: SceneRenderer = sc.meta["renderer"]
    from PIL import ImageDraw

    canvas = Image.fromarray(sc.img.astype(np.uint8))
    d = ImageDraw.Draw(canvas, "RGBA")
    free = np.argwhere(sc.building_ids == 0)
    for k in range(9):  # 橙色 / 落日色车辆与一辆橙色大巴
        yx = free[int(rng.integers(len(free)))]
        r.car(d, float(yx[1]), float(yx[0]), float(rng.uniform(0, math.pi)), "bus" if k == 0 else "car",
              color=[(236, 120, 28), (226, 96, 22), (244, 150, 40), (210, 70, 30)][k % 4])
    sc.img = np.asarray(canvas, np.float32)
    sc.img = grade(sc.img, "golden")
    out.append(dict(id="fire-05", type="fire", name="黄昏巡检 · 红瓦屋面与橙色车辆（易误报）", kind="image",
                    description="一元路历史街区黄昏时段影像：大量红瓦坡屋面、橙色车辆与暖色光照，色彩接近火焰但无火情，用于验证误报抑制。" + SYNTH,
                    files=[save_jpg(finish(sc.img, rng), "fire/drone_sunset_roofs.jpg")], lon=lon, lat=lat, location=loc, showcase=False))
    return out


# ------------------------------------------------------------------ 交通

def write_csv(rel: str, header: list[str], rows: list[list[Any]]) -> str:
    p = OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    return rel


def ar_noise(n: int, rng: np.random.Generator, phi: float = 0.8, sigma: float = 1.0) -> np.ndarray:
    e = rng.normal(0, sigma, n)
    out = np.zeros(n)
    for i in range(1, n):
        out[i] = phi * out[i - 1] + e[i]
    return out


def diurnal_congestion(h: np.ndarray) -> np.ndarray:
    """城市主干路典型日内拥堵强度曲线（0~1）：早高峰 8:15、晚高峰 17:55、午间小高峰。"""
    return np.clip(
        0.06
        + 0.70 * np.exp(-(((h - 8.25) / 0.85) ** 2))
        + 0.76 * np.exp(-(((h - 17.9) / 1.05) ** 2))
        + 0.22 * np.exp(-(((h - 12.6) / 1.5) ** 2))
        - 0.05 * np.exp(-(((h - 3.5) / 2.0) ** 2)),
        0,
        1,
    )


def preview_chart(rel: str, title: str, labels: list[str], lines: list[Line], **kw: Any) -> str:
    render_chart(Chart(title=title, x_labels=labels, lines=lines, size=(640, 300), **kw), OUT / rel)
    return rel


def traffic_samples(rng_for: Callable[[str], np.random.Generator]) -> list[dict]:
    out = []
    rng = rng_for("traffic-01")
    lon, lat, _, loc = anchor(road="解放大道", fallback=(114.2785, 30.5885))
    ff = 56.0
    h = np.arange(0, 24, 5 / 60)
    c = diurnal_congestion(h)
    speed = np.clip(ff * (1 - 0.9 * c) * (1 + 0.05 * ar_noise(len(h), rng, 0.85, 0.6)), 6, 68)
    r = speed / ff
    flow = np.clip(430 * 4 * r * (1 - r) * (0.35 + 0.65 * np.clip(c * 3, 0, 1)) + rng.normal(0, 12, len(h)), 20, None)
    labels = [f"{int(x):02d}:{int(round((x % 1) * 60)):02d}" for x in h]
    f = write_csv("traffic/jiefang_ave_speed_24h.csv", ["time", "speed", "flow"], [[t, f"{s:.1f}", int(q)] for t, s, q in zip(labels, speed, flow)])
    thumb = preview_chart("traffic/jiefang_ave_speed_24h_preview.png", "Jiefang Ave  speed (km/h)  5-min", labels, [Line(speed.round(1).tolist(), (79, 195, 247), "speed")])
    out.append(dict(id="traffic-01", type="traffic", name="解放大道 · 全天 5 分钟车速", kind="csv",
                    description="解放大道某检测断面 24 小时车速与流量（5 分钟粒度），含早晚高峰。" + SYNTH_CSV,
                    files=[f], thumbnail=thumb, lon=lon, lat=lat, location=loc, showcase=True))

    rng = rng_for("traffic-02")
    lon, lat, _, loc = anchor(road="沿江大道", fallback=(114.2975, 30.5880))
    ff = 48.0
    mins = np.arange(12 * 60, 17 * 60 + 1, 2)
    h = mins / 60
    base = ff * (1 - 0.8 * diurnal_congestion(h))
    inc = np.where((mins >= 14 * 60 + 22) & (mins < 15 * 60 + 8), 1.0, 0.0)
    inc = np.convolve(inc, np.ones(5) / 5, mode="same")
    speed = np.clip(base * (1 - 0.78 * inc) * (1 + 0.05 * ar_noise(len(h), rng, 0.8, 0.6)), 4, 60)
    labels = [f"{m // 60:02d}:{m % 60:02d}" for m in mins]
    f = write_csv("traffic/yanjiang_ave_incident.csv", ["time", "speed"], [[t, f"{s:.1f}"] for t, s in zip(labels, speed)])
    thumb = preview_chart("traffic/yanjiang_ave_incident_preview.png", "Yanjiang Ave  speed (km/h)  2-min", labels, [Line(speed.round(1).tolist(), (255, 159, 67), "speed")])
    out.append(dict(id="traffic-02", type="traffic", name="沿江大道 · 交通事故异常拥堵", kind="csv",
                    description="沿江大道午后 2 分钟粒度车速，14:20 前后发生追尾事故导致车速骤降约 50 分钟。" + SYNTH_CSV,
                    files=[f], thumbnail=thumb, lon=lon, lat=lat, location=loc, showcase=True))

    for sid, road, fb, jam, fname, title, desc, show in (
        ("traffic-03", "中山大道", (114.2868, 30.5838), True, "traffic/zhongshan_ave_peak.jpg", "无人机航拍 · 中山大道晚高峰排队",
         "中山大道路段俯拍，双向车道车辆密集排队。", True),
        ("traffic-04", "京汉大道", (114.2880, 30.5905), False, "traffic/jinghan_ave_offpeak.jpg", "无人机航拍 · 京汉大道平峰畅通",
         "京汉大道平峰时段俯拍，车辆稀疏、通行顺畅。", False),
    ):
        rng = rng_for(sid)
        lon, lat, ang, loc = anchor(road=road, fallback=fb, default_angle=-28.0 if jam else 18.0)
        ang = ((ang + 90) % 180) - 90
        ang = float(np.clip(ang, -12, 12)) if abs(ang) < 45 else 0.0  # 航拍航向与道路对齐，保留少量偏角
        cor = Corridor(angle=ang, lanes_per_dir=3, sidewalk_m=4.5)
        sc = base_scene(lon, lat, rng, mpp=0.2, corridor=cor, cars=0, trees=0.6)
        _place_traffic(sc, rng, jam)
        out.append(dict(id=sid, type="traffic", name=title, kind="image", description=desc + SYNTH,
                        files=[save_jpg(finish(sc.img, rng), fname)], lon=lon, lat=lat, location=loc, showcase=show))
    return out


def _place_traffic(sc: Scene, rng: np.random.Generator, jam: bool) -> None:
    from PIL import ImageDraw

    r: SceneRenderer = sc.meta["renderer"]
    cor = sc.corridor
    assert cor is not None
    canvas = Image.fromarray(sc.img.astype(np.uint8))
    d = ImageDraw.Draw(canvas, "RGBA")
    cx, cy, ct, st = sc.corridor_frame()
    L = math.hypot(*sc.size) / 2
    ang = math.atan2(st, ct)
    for direction in (1, -1):
        for lane in range(cor.lanes_per_dir):
            off = r.lane_center(cor, direction, lane)
            dense = jam and (direction == 1 or lane < 2)
            pos = -L
            while pos < L:
                if dense:
                    kind = "bus" if rng.random() < 0.06 else ("suv" if rng.random() < 0.2 else "car")
                    length = {"car": 4.6, "suv": 4.9, "bus": 12.0}[kind] / sc.mpp
                    gap = rng.uniform(1.2, 3.2) / sc.mpp
                else:
                    kind, length = "car", 4.6 / sc.mpp
                    gap = rng.uniform(25, 70) / sc.mpp
                pos += gap + length / 2
                x, y = cx + ct * pos - st * off, cy + st * pos + ct * off
                r.car(d, x, y, ang + (0 if direction > 0 else math.pi) + rng.normal(0, 0.02), kind)
                pos += length / 2
    sc.img = np.asarray(canvas, np.float32)


# ------------------------------------------------------------------ 建筑

def building_samples(rng_for: Callable[[str], np.random.Generator]) -> list[dict]:
    out = []
    # 变化检测：选取低层居民楼（通用名称，避免对具名建筑作安全暗示）
    rng = rng_for("building-01")
    tgt = building_pick(lambda p: p["category"] in ("residential", "other") and p["height"] < 30 and 300 < p["area_m2"] < 2000 and bool(GENERIC_NAME.search(p["name"])),
                        key=lambda p: -math.hypot(p["longitude"] - 114.2925, p["latitude"] - 30.5905))
    lon, lat = (tgt["properties"]["longitude"], tgt["properties"]["latitude"]) if tgt else (114.2905, 30.5905)
    loc = "江岸区老城区居民楼"
    sc = base_scene(lon, lat, rng, cars=14)
    before = sc.copy()
    # 坍塌目标：画面中心附近的建筑
    W, H = sc.size
    idx = int(sc.building_ids[H // 2, W // 2]) - 1
    if idx < 0:
        ids, counts = np.unique(sc.building_ids[sc.building_ids > 0], return_counts=True)
        idx = int(ids[np.argmax(counts)]) - 1
    add_collapse(sc, idx, rng)
    # 新增临建：放在一块 61×61 像素完全空闲（无建筑 / 道路）的地面上，尽量靠近画面右下
    free = ((sc.building_ids == 0) & ~sc.road_mask).astype(np.float32)
    ok = np.argwhere(box_sum(free, 61) > 61 * 61 - 0.5)
    ok = ok[(ok[:, 1] > 60) & (ok[:, 1] < W - 60) & (ok[:, 0] > 40) & (ok[:, 0] < H - 40)]
    spot = ok[np.argmin(np.hypot(ok[:, 1] - W * 0.75, ok[:, 0] - H * 0.7))] if len(ok) else np.array([H * 0.7, W * 0.75])
    add_new_structure(sc, float(spot[1]), float(spot[0]), 96, 40, 0.12, rng)
    # 后时相：不同成像条件（亮度 / 对比度 / 噪声）+ 车辆位置变化
    r_after = rng_for("building-01-after")
    after = grade(sc.img * 1.06 + 4, "overcast")
    f1 = save_jpg(finish(before.img, rng), "building/change_01_before.jpg")
    f2 = save_jpg(finish(after, r_after, noise=3.5, vignette=0.12), "building/change_01_after.jpg")
    thumb = _pair_preview(f1, f2, "building/change_01_preview.jpg")
    out.append(dict(id="building-01", type="building", name="卫星 / 无人机前后时相 · 结构坍塌与违建", kind="image_pair",
                    description="同一街区两期影像：一栋低层建筑局部坍塌，空地新增蓝色彩钢瓦临建；两期成像亮度不同。" + SYNTH,
                    files=[f1, f2], thumbnail=thumb, lon=lon, lat=lat, location=loc, showcase=True))

    rng = rng_for("building-02")
    lon2, lat2, _, loc2 = anchor(building="江汉饭店", fallback=(114.2958, 30.5936))
    sc = base_scene(lon2, lat2, rng, cars=0)
    f1 = save_jpg(finish(sc.img, rng), "building/nochange_02_before.jpg")
    r2 = rng_for("building-02-after")
    f2 = save_jpg(finish(np.clip(sc.img * 0.93 + 6, 0, 255), r2, noise=3.5, vignette=0.1), "building/nochange_02_after.jpg")
    thumb = _pair_preview(f1, f2, "building/nochange_02_preview.jpg")
    out.append(dict(id="building-02", type="building", name="前后时相 · 无变化对照", kind="image_pair",
                    description="同一街区两期影像，仅成像亮度与噪声不同，无结构变化，用于验证变化检测不误报。" + SYNTH,
                    files=[f1, f2], thumbnail=thumb, lon=lon2, lat=lat2, location=loc2, showcase=False))

    # 沉降时序
    start = date(2026, 4, 20)
    days = [start + timedelta(days=i) for i in range(180)]
    t = np.arange(180, dtype=float)
    profiles = [
        ("building-03", "settlement_stable.csv", "高层住宅沉降监测 · 稳定", "近半年沉降速率约 0.3 mm/月，随季节温度小幅波动。",
         -0.3 / 30.44 * t + 0.5 * np.sin(2 * np.pi * t / 365), 0.22, False, "新鸿基花园"),
        ("building-04", "settlement_watch.csv", "高层建筑沉降监测 · 持续沉降", "沉降速率稳定在约 2.8 mm/月，超过关注阈值，含 1 个异常测点。",
         -2.8 / 30.44 * t, 0.28, False, None),
        ("building-05", "settlement_accelerating.csv", "高层建筑沉降监测 · 加速沉降", "前期速率约 1 mm/月，近 80 天持续加速，末段速率接近 5 mm/月。",
         -1.0 / 30.44 * t - 0.0008 * np.clip(t - 100, 0, None) ** 2.0, 0.25, True, None),
    ]
    tall_generic = sorted((f for f in BUILDINGS if GENERIC_NAME.search(f["properties"]["name"]) and f["properties"]["height"] >= 30),
                          key=lambda f: -f["properties"]["height"])
    for sid, fname, title, desc, curve, sigma, show, bname in profiles:
        rng = rng_for(sid)
        y = curve + rng.normal(0, sigma, 180)
        if sid == "building-04":
            y[121] -= 3.2  # 单点粗差（测量异常）
        if bname and building_by_name(bname):
            p = building_by_name(bname)["properties"]  # type: ignore[index]
            lon, lat, loc = p["longitude"], p["latitude"], bname
        else:
            # 风险类示例放在无名（通用名称）建筑上，避免对具名建筑作安全暗示
            p = tall_generic[0 if sid == "building-05" else 1]["properties"] if len(tall_generic) > 1 else None
            lon, lat = (p["longitude"], p["latitude"]) if p else (114.2920, 30.5799)
            loc = f"{p['name'].split(' · ')[0]}沿线高层建筑" if p and " · " in p["name"] else "高层建筑"  # 不暴露会变化的建筑编号
        rows = [[d.isoformat(), f"{v:.2f}"] for d, v in zip(days, y)]
        f = write_csv(f"building/{fname}", ["date", "displacement_mm"], rows)
        thumb = preview_chart(f"building/{fname.replace('.csv', '_preview.png')}", "settlement displacement (mm)", [d.strftime("%m-%d") for d in days],
                              [Line(np.round(y, 2).tolist(), (155, 143, 255), "displacement")], hlines=[HLine(0.0, (120, 150, 190), "0")])
        out.append(dict(id=sid, type="building", name=title, kind="csv", description=desc + SYNTH_CSV,
                        files=[f], thumbnail=thumb, lon=lon, lat=lat, location=loc, showcase=show or sid == "building-04"))
    return out


def _pair_preview(f1: str, f2: str, rel: str) -> str:
    a = Image.open(OUT / f1).resize((480, 320))
    b = Image.open(OUT / f2).resize((480, 320))
    canvas = Image.new("RGB", (968, 320), (8, 16, 32))
    canvas.paste(a, (0, 0))
    canvas.paste(b, (488, 0))
    return save_jpg(canvas, rel)


# ------------------------------------------------------------------ 内涝

def storm_series(rng: np.random.Generator, peak_mm5: float, total_steps: int = 64, lag: int = 5) -> tuple[np.ndarray, np.ndarray]:
    """芝加哥雨型降雨（5 分钟，雨峰系数 r=0.4）+ 带排水能力上限的线性水库汇流模型。

    返回 (降雨 mm/5min, 积水深度 cm)。汇流滞后 lag 步；排水量 = min(k·水位, 管网能力)。
    """
    k = np.arange(total_steps)
    peak_at, r = 26, 0.4
    tb = np.where(k < peak_at, (peak_at - k) / r, (k - peak_at) / (1 - r))
    rain = peak_mm5 / (1 + 0.09 * tb) ** 1.6
    rain = np.where((k < 6) | (k > 52), 0.0, rain)
    rain = np.clip(rain * (1 + rng.normal(0, 0.08, total_steps)), 0, None)
    rain[rain < 0.05] = 0.0
    level = np.zeros(total_steps)
    for i in range(1, total_steps):
        inflow = 1.1 * (rain[i - lag] if i >= lag else 0.0)
        drain = min(0.07 * level[i - 1] + 0.35, 1.6) if level[i - 1] > 0 else 0.0
        level[i] = max(0.0, level[i - 1] + inflow - drain)
    level = np.clip(level + rng.normal(0, 0.3, total_steps) * (level > 0.5), 0, None)
    return rain, level


def flood_samples(rng_for: Callable[[str], np.random.Generator]) -> list[dict]:
    out = []
    for sid, peak, fname, title, desc, show, road, fb in (
        ("flood-01", 7.2, "jinghan_ave_rainstorm.csv", "京汉大道低洼点 · 暴雨积水监测", "短历时强降雨（峰值雨强约 86 mm/h）下，低洼路段积水监测点 5 分钟水位与雨量。", True, "京汉大道", (114.2870, 30.5905)),
        ("flood-04", 1.0, "light_rain_normal.csv", "积水监测点 · 小雨（未超阈值）", "小雨过程水位小幅上涨后回落，未超过影响通行阈值。", False, "胜利街", (114.2950, 30.5895)),
    ):
        rng = rng_for(sid)
        rain, level = storm_series(rng, peak)
        mins = [12 * 60 + 5 * i for i in range(len(rain))]
        labels = [f"{m // 60:02d}:{m % 60:02d}" for m in mins]
        f = write_csv(f"flood/{fname}", ["time", "water_level_cm", "rainfall_mm"], [[t, f"{l:.1f}", f"{r:.2f}"] for t, l, r in zip(labels, level, rain)])
        thumb = preview_chart(f"flood/{fname.replace('.csv', '_preview.png')}", "water level (cm) / rainfall (mm per 5 min)", labels,
                              [Line(level.round(1).tolist(), (63, 169, 255), "level")], bars=[Bars(rain.tolist(), (120, 200, 255, 110), "rain")],
                              hlines=[HLine(15, (240, 192, 80), "15 cm"), HLine(27, (255, 138, 61), "27 cm"), HLine(40, (255, 77, 79), "40 cm")], y_range=(0, 50))
        lon, lat, _, loc = anchor(road=road, fallback=fb)
        out.append(dict(id=sid, type="flood", name=title, kind="csv", description=desc + SYNTH_CSV,
                        files=[f], thumbnail=thumb, lon=lon, lat=lat, location=loc, showcase=show))

    for sid, road, fb, wet, fname, title, desc, show in (
        ("flood-02", "建设大道", (114.2780, 30.5960), True, "flood/street_waterlogging.jpg", "无人机航拍 · 主干道严重积水（“看海”）",
         "暴雨后主干道俯拍：路面被浑浊积水覆盖并漫上人行道，多辆车辆熄火被困。", True),
        ("flood-03", "建设大道", (114.2780, 30.5960), False, "flood/street_dry.jpg", "无人机航拍 · 雨后路面正常",
         "同一街道雨后影像，路面无成片积水，用于验证分割不误报。", False),
    ):
        rng = rng_for(sid)
        lon, lat, ang, loc = anchor(road=road, fallback=fb, default_angle=-22.0)
        ang = ((ang + 90) % 180) - 90
        cor = Corridor(angle=ang, lanes_per_dir=3, sidewalk_m=4.0)
        sc = base_scene(lon, lat, rng, mpp=0.2, corridor=cor, cars=10 if not wet else 0, trees=0.8)
        if wet:
            add_flood(sc, rng, spread_m=5.5)
            stall_cars_in_water(sc, rng, 5)
            sc.img = grade(sc.img, "overcast")
        out.append(dict(id=sid, type="flood", name=title, kind="image", description=desc + SYNTH,
                        files=[save_jpg(finish(sc.img, rng), fname)], lon=lon, lat=lat, location=loc, showcase=show))
    return out


# ------------------------------------------------------------------ 主程序

def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    def rng_for(key: str) -> np.random.Generator:
        return np.random.default_rng([SEED, sum(ord(c) * (i + 1) for i, c in enumerate(key))])

    samples = fire_samples(rng_for) + traffic_samples(rng_for) + building_samples(rng_for) + flood_samples(rng_for)
    manifest = []
    for s in samples:
        files = [f"/files/samples/{f}" for f in s["files"]]
        manifest.append({
            "id": s["id"],
            "type": s["type"],
            "name": s["name"],
            "description": s["description"],
            "kind": s["kind"],
            "thumbnail_url": f"/files/samples/{s.get('thumbnail', s['files'][0])}",
            "files": files,
            "longitude": round(float(s["lon"]), 6),
            "latitude": round(float(s["lat"]), 6),
            "location": s["location"],
            "showcase": bool(s["showcase"]),
        })
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    total = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())
    print(f"生成 {len(manifest)} 个示例，共 {total / 1e6:.2f} MB → {OUT}")
    print("geo:", f"{len(BUILDINGS)} buildings, {len(ROADS)} roads")


if __name__ == "__main__":
    main()
