"""地理数据仓库：加载 data/geo 下的 OpenStreetMap 建筑 / 道路 / POI 与区域配置，提供空间查询。

- 建筑 / 道路编号（B0001 / R001）在数据重新生成时可能变化，系统中所有引用都在启动时从文件派生，不写死；
- 任意点所属行政区 = 最近建筑的行政区；网格编号 = {区前缀}-{行:02d}-{列:02d}（1 起算，自区域西南角）；
- 距离计算使用以区域中心为原点的等距圆柱投影（示范区范围约 4 km，误差可忽略）。
"""
from __future__ import annotations

import json
import logging
import math
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

log = logging.getLogger("cityeye.geo")

DEFAULT_REGION: dict[str, Any] = {
    "name": "汉口沿江示范区",
    "city": "武汉",
    "center": [114.2905, 30.5895],
    "bbox": [114.270, 30.570, 114.312, 30.612],
    "grid": {"origin": [114.270, 30.570], "cell_deg": 0.0045, "rows": 10, "cols": 10},
    "district_prefix": {"江汉区": "JH", "江岸区": "JA", "硚口区": "QK", "汉阳区": "HY", "武昌区": "WC"},
    "districts": ["江岸区", "江汉区"],
}
ODBL = "建筑 / 道路 / POI 数据 © OpenStreetMap contributors（ODbL 1.0）"
GENERIC_NAME = re.compile(r"(住宅|建筑|商业|办公|公共|工业|写字楼|商场)\s*B\d{3,}$")
SEGMENT_SUFFIX = re.compile(r"（[一二三四五六七八九十\d]+段）$")
CATEGORY_CN = {
    "residential": "住宅楼",
    "commercial": "商业楼宇",
    "office": "办公楼",
    "public": "公共建筑",
    "industrial": "厂房仓库",
    "other": "建筑",
}


def base_road_name(name: str) -> str:
    """去掉"（一段）"等分段后缀，用于地址描述。"""
    return SEGMENT_SUFFIX.sub("", name or "")


def is_generic_name(name: str) -> bool:
    return not name or bool(GENERIC_NAME.search(name))


@dataclass
class Road:
    id: str
    name: str
    highway: str
    length_m: float
    speed_limit: float
    lanes: int | None
    coords: np.ndarray  # (n, 2) lon/lat
    geometry: dict[str, Any]

    @property
    def base_name(self) -> str:
        return base_road_name(self.name)


class GeoRepository:
    def __init__(self, geo_dir: Path) -> None:
        self.geo_dir = geo_dir
        self.region: dict[str, Any] = {**DEFAULT_REGION, **self._load_json("region.json", {})}
        lon0, lat0 = self.region["center"]
        self._kx = 111_320.0 * math.cos(math.radians(lat0))
        self._ky = 110_540.0
        self._lon0, self._lat0 = lon0, lat0

        self.building_features: list[dict[str, Any]] = self._load_json("buildings.geojson", {}).get("features", [])
        self.buildings: dict[str, dict[str, Any]] = {f["properties"]["id"]: f["properties"] for f in self.building_features}
        if self.building_features:
            ll = np.array([[p["longitude"], p["latitude"]] for p in self.buildings.values()], dtype=np.float64)
            self._b_ids = list(self.buildings.keys())
            self._b_xy = self._xy(ll[:, 0], ll[:, 1])
        else:
            self._b_ids, self._b_xy = [], np.zeros((0, 2))

        self.roads: list[Road] = []
        for f in self._load_json("roads.geojson", {}).get("features", []):
            g = f.get("geometry") or {}
            if g.get("type") != "LineString" or len(g.get("coordinates", [])) < 2:
                continue
            p = f["properties"]
            self.roads.append(
                Road(
                    id=p["id"],
                    name=p.get("name") or p["id"],
                    highway=p.get("highway", "tertiary"),
                    length_m=float(p.get("length_m") or 0.0),
                    speed_limit=float(p.get("speed_limit") or 40),
                    lanes=p.get("lanes"),
                    coords=np.asarray(g["coordinates"], dtype=np.float64),
                    geometry=g,
                )
            )
        self.road_by_id = {r.id: r for r in self.roads}
        segs, owner = [], []
        for i, r in enumerate(self.roads):
            xy = self._xy(r.coords[:, 0], r.coords[:, 1])
            segs.append(np.hstack([xy[:-1], xy[1:]]))
            owner += [i] * (len(xy) - 1)
        self._segs = np.vstack(segs) if segs else np.zeros((0, 4))
        self._seg_owner = np.asarray(owner, dtype=np.int64)
        self.pois: list[dict[str, Any]] = self._load_json("pois.json", [])
        self.monitoring: dict[str, str] = {}  # building_id → risk_level（由沉降评估写入）
        log.info("地理数据：%d 栋建筑，%d 条道路，%d 个 POI", len(self.buildings), len(self.roads), len(self.pois))

    # ------------------------------------------------------------------ 基础
    def _load_json(self, name: str, default: Any) -> Any:
        p = self.geo_dir / name
        if not p.exists():
            log.warning("缺少地理数据文件 %s，使用空数据", p)
            return default
        return json.loads(p.read_text(encoding="utf-8"))

    def _xy(self, lon: Any, lat: Any) -> np.ndarray:
        return np.column_stack([(np.asarray(lon) - self._lon0) * self._kx, (np.asarray(lat) - self._lat0) * self._ky])

    def lonlat(self, x: float, y: float) -> tuple[float, float]:
        return self._lon0 + x / self._kx, self._lat0 + y / self._ky

    def in_region(self, lon: float, lat: float, margin_deg: float = 0.03) -> bool:
        w, s, e, n = self.region["bbox"]
        return w - margin_deg <= lon <= e + margin_deg and s - margin_deg <= lat <= n + margin_deg

    # ------------------------------------------------------------------ 建筑
    def nearest_building(self, lon: float, lat: float, max_m: float | None = None) -> tuple[dict[str, Any], float] | None:
        if not self._b_ids:
            return None
        p = self._xy([lon], [lat])[0]
        d = np.hypot(self._b_xy[:, 0] - p[0], self._b_xy[:, 1] - p[1])
        i = int(np.argmin(d))
        if max_m is not None and d[i] > max_m:
            return None
        return self.buildings[self._b_ids[i]], float(d[i])

    def nearest_named_building(self, lon: float, lat: float, max_m: float) -> dict[str, Any] | None:
        if not self._b_ids:
            return None
        p = self._xy([lon], [lat])[0]
        d = np.hypot(self._b_xy[:, 0] - p[0], self._b_xy[:, 1] - p[1])
        for i in np.argsort(d)[:30]:
            if d[i] > max_m:
                break
            b = self.buildings[self._b_ids[i]]
            if not is_generic_name(b.get("name", "")):
                return b
        return None

    def building_label(self, b: dict[str, Any]) -> str:
        """事件命名用的建筑称谓：具名建筑用其名称，无名建筑用"道路 + 类别"。"""
        name = b.get("name", "")
        if not is_generic_name(name):
            return name
        cat = CATEGORY_CN.get(b.get("category", "other"), "建筑")
        roads = self.nearest_roads(b["longitude"], b["latitude"], within_m=150, k=1)
        return f"{roads[0][0].base_name}沿线{cat}" if roads else f"{b.get('district', '')}{cat}"

    # ------------------------------------------------------------------ 行政区 / 网格 / 地址
    def district_of(self, lon: float, lat: float) -> str:
        nb = self.nearest_building(lon, lat)
        if nb:
            return nb[0].get("district") or self.region["districts"][0]
        return self.region.get("districts", ["江岸区"])[0]

    def grid_of(self, lon: float, lat: float, district: str | None = None) -> str:
        g = self.region["grid"]
        district = district or self.district_of(lon, lat)
        prefix = self.region["district_prefix"].get(district, "XX")
        row = int(np.clip(math.floor((lat - g["origin"][1]) / g["cell_deg"]), 0, g["rows"] - 1)) + 1
        col = int(np.clip(math.floor((lon - g["origin"][0]) / g["cell_deg"]), 0, g["cols"] - 1)) + 1
        return f"{prefix}-{row:02d}-{col:02d}"

    def nearest_roads(self, lon: float, lat: float, within_m: float = 150.0, k: int = 2) -> list[tuple[Road, float]]:
        """按距离返回 within_m 内最近的 k 条道路（同名分段只保留一条）。"""
        if len(self._segs) == 0:
            return []
        p = self._xy([lon], [lat])[0]
        a, b = self._segs[:, :2], self._segs[:, 2:]
        ab = b - a
        t = np.clip(((p - a) * ab).sum(1) / np.maximum((ab**2).sum(1), 1e-9), 0, 1)
        proj = a + ab * t[:, None]
        d = np.hypot(proj[:, 0] - p[0], proj[:, 1] - p[1])
        best: dict[int, float] = {}
        for seg in np.argsort(d):
            if d[seg] > within_m:
                break
            ri = int(self._seg_owner[seg])
            best.setdefault(ri, float(d[seg]))
            if len(best) >= 8:
                break
        out: list[tuple[Road, float]] = []
        seen: set[str] = set()
        for ri, dist in sorted(best.items(), key=lambda kv: kv[1]):
            r = self.roads[ri]
            if r.base_name in seen:
                continue
            seen.add(r.base_name)
            out.append((r, dist))
            if len(out) >= k:
                break
        return out

    def address_of(self, lon: float, lat: float) -> str:
        roads = self.nearest_roads(lon, lat, within_m=160, k=2)
        named = self.nearest_named_building(lon, lat, 90)
        if len(roads) == 2 and roads[1][1] < 70:
            return f"{roads[0][0].base_name} · {roads[1][0].base_name}交汇处"
        if roads:
            return f"{roads[0][0].base_name} · {named['name']}附近" if named else f"{roads[0][0].base_name}沿线"
        if named:
            return f"{named['name']}附近"
        district = self.district_of(lon, lat)
        return f"{district}{self.grid_of(lon, lat, district)}网格"

    def locate(self, lon: float, lat: float) -> tuple[str, str, str]:
        """返回 (行政区, 地址, 网格)。"""
        district = self.district_of(lon, lat)
        return district, self.address_of(lon, lat), self.grid_of(lon, lat, district)

    # ------------------------------------------------------------------ 道路采样
    def point_on_road(self, road: Road, frac: float) -> tuple[float, float]:
        """沿道路折线长度比例 frac ∈ [0,1] 处的点。"""
        xy = self._xy(road.coords[:, 0], road.coords[:, 1])
        seg = np.hypot(*(xy[1:] - xy[:-1]).T)
        cum = np.concatenate([[0], np.cumsum(seg)])
        target = float(np.clip(frac, 0, 1)) * cum[-1]
        i = int(np.clip(np.searchsorted(cum, target) - 1, 0, len(seg) - 1))
        t = (target - cum[i]) / max(seg[i], 1e-9)
        x, y = xy[i] + (xy[i + 1] - xy[i]) * t
        return self.lonlat(float(x), float(y))

    def random_point_on_road(self, rng: random.Random, road: Road) -> tuple[float, float]:
        """道路上的随机点（限定在示范区内）。"""
        for _ in range(12):
            lon, lat = self.point_on_road(road, rng.uniform(0.1, 0.9))
            if self.in_region(lon, lat, margin_deg=0.0):
                return lon, lat
        return self.point_on_road(road, 0.5)

    def roads_named(self, *prefixes: str) -> list[Road]:
        return [r for r in self.roads if any(r.base_name == p or r.name.startswith(p) for p in prefixes)]

    # ------------------------------------------------------------------ GeoJSON 输出
    def buildings_geojson(self) -> dict[str, Any]:
        feats = []
        for f in self.building_features:
            p = dict(f["properties"])
            p.pop("osm_id", None)
            risk = self.monitoring.get(p["id"])
            p["monitored"] = risk is not None
            p["risk_level"] = risk or "normal"
            feats.append({"type": "Feature", "id": p["id"], "geometry": f["geometry"], "properties": p})
        return {"type": "FeatureCollection", "features": feats}

    def building_props(self, building_id: str) -> dict[str, Any] | None:
        p = self.buildings.get(building_id)
        if p is None:
            return None
        out = {k: v for k, v in p.items() if k != "osm_id"}
        risk = self.monitoring.get(building_id)
        out["monitored"] = risk is not None
        out["risk_level"] = risk or "normal"
        return out
