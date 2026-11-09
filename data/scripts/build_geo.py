"""把 fetch_osm.py 抓取的 OSM 原始数据加工为城市智眼使用的 GeoJSON。

输出（data/geo/）：
    buildings.geojson  真实建筑轮廓 + 高度（OSM 实测 / 楼层推算 / 规则估算，height_source 标明来源）
    roads.geojson      主干路网（同名道路合并为连续路段）
    pois.json          应急资源点位（医院 / 消防站 / 派出所 / 学校）
    region.json        中心城区元信息：中心、范围、网格化管理编码规则、行政区前缀

高度说明：OSM 中武汉建筑多数缺少 height / building:levels 标签。缺失时按"占地面积 + 建筑类别 +
确定性随机"估算，仅用于三维可视化体量表达，并在属性 height_source=estimated 中如实标注。

用法：
    python data/scripts/build_geo.py --raw data/raw/osm --out data/geo
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

BBOX = (30.450, 114.150, 30.720, 114.550)  # south, west, north, east
REGION_NAME = "武汉中心城区"
CELL_DEG = 0.0045  # 网格边长约 430m × 500m
DISTRICT_PREFIX = {"江汉区": "JH", "江岸区": "JA", "硚口区": "QK", "汉阳区": "HY", "武昌区": "WC", "洪山区": "HS", "青山区": "QS"}
DISTRICT_CENTERS = {
    "江岸区": (114.309, 30.625),
    "江汉区": (114.271, 30.601),
    "硚口区": (114.216, 30.585),
    "汉阳区": (114.218, 30.553),
    "武昌区": (114.316, 30.553),
    "洪山区": (114.397, 30.506),
    "青山区": (114.405, 30.640),
}

M_PER_DEG_LAT = 111_320.0
M_PER_DEG_LON = 111_320.0 * math.cos(math.radians((BBOX[0] + BBOX[2]) / 2))

CATEGORY_CN = {
    "residential": "住宅",
    "commercial": "商业",
    "office": "办公",
    "public": "公共建筑",
    "industrial": "工业仓储",
    "other": "建筑",
}

RESIDENTIAL = {"residential", "apartments", "house", "dormitory", "detached", "terrace", "appartment", "semidetached_house"}
COMMERCIAL = {"commercial", "retail", "hotel", "supermarket", "mall", "kiosk", "shop"}
OFFICE = {"office", "government"}
PUBLIC = {
    "hospital", "school", "public", "church", "train_station", "stadium", "university", "civic", "kindergarten",
    "museum", "college", "temple", "transportation", "sports_hall", "library", "fire_station", "police",
}
INDUSTRIAL = {"industrial", "warehouse", "factory", "garage", "garages", "shed", "service"}


def h01(*parts: object) -> float:
    """确定性 [0,1) 伪随机数（同一输入永远同一输出，保证数据可复现）。"""
    s = "|".join(map(str, parts)).encode()
    return int(hashlib.md5(s).hexdigest()[:8], 16) / 0xFFFFFFFF


def ring_area_m2(ring: list[list[float]]) -> float:
    a = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
        a += (x1 * M_PER_DEG_LON) * (y2 * M_PER_DEG_LAT) - (x2 * M_PER_DEG_LON) * (y1 * M_PER_DEG_LAT)
    return abs(a) / 2


def ring_centroid(ring: list[list[float]]) -> tuple[float, float]:
    pts = ring[:-1]
    return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)


def dist_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot((a[0] - b[0]) * M_PER_DEG_LON, (a[1] - b[1]) * M_PER_DEG_LAT)


def in_bbox(lon: float, lat: float, pad: float = 0.0) -> bool:
    s, w, n, e = BBOX
    return s - pad <= lat <= n + pad and w - pad <= lon <= e + pad


def read_json(path: Path) -> dict:
    data = path.read_bytes()
    try:
        return json.loads(data.decode("utf-8"))
    except UnicodeDecodeError:
        return json.loads(data.decode("gbk"))


# ---------------------------------------------------------------- 行政区
def load_district_segments(raw: Path) -> dict[str, list[tuple[float, float, float, float]]]:
    """行政区边界：收集各区边界 way 的线段，射线法判断点所属（无需拼环，奇偶规则对无序线段集同样成立）。"""
    out: dict[str, list] = {}
    for f in sorted(raw.glob("district_*.json")):
        name = f.stem.split("_", 1)[1]
        segs = []
        for el in read_json(f).get("elements", []):
            g = el.get("geometry") or []
            for p, q in zip(g, g[1:]):
                segs.append((p["lon"], p["lat"], q["lon"], q["lat"]))
        if segs:
            out[name] = segs
    return out


def point_in_segments(lon: float, lat: float, segs) -> bool:
    inside = False
    for x1, y1, x2, y2 in segs:
        if (y1 > lat) != (y2 > lat):
            xi = x1 + (lat - y1) * (x2 - x1) / (y2 - y1)
            if xi > lon:
                inside = not inside
    return inside


def district_of(lon: float, lat: float, districts) -> str:
    for name, segs in districts.items():
        if point_in_segments(lon, lat, segs):
            return name
    return min(DISTRICT_CENTERS, key=lambda name: dist_m((lon, lat), DISTRICT_CENTERS[name]))


def grid_of(lon: float, lat: float, district: str) -> str:
    s, w, _, _ = BBOX
    row = int((lat - s) / CELL_DEG) + 1
    col = int((lon - w) / CELL_DEG) + 1
    return f"{DISTRICT_PREFIX.get(district, 'WH')}-{row:02d}-{col:02d}"


# ---------------------------------------------------------------- 道路
def smooth(a, b, c, max_turn: float = 100.0) -> bool:
    """a→b→c 的转角是否小于 max_turn 度（用于拒绝 U 形拼接）。"""
    v1 = ((b[0] - a[0]) * M_PER_DEG_LON, (b[1] - a[1]) * M_PER_DEG_LAT)
    v2 = ((c[0] - b[0]) * M_PER_DEG_LON, (c[1] - b[1]) * M_PER_DEG_LAT)
    n1, n2 = math.hypot(*v1), math.hypot(*v2)
    if n1 < 1e-6 or n2 < 1e-6:
        return True
    cos = max(-1.0, min(1.0, (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2)))
    return math.degrees(math.acos(cos)) <= max_turn


def clip_chain(chain: list[list[float]], pad: float = 0.0015) -> list[list[float]]:
    """保留落在示范区（含少量外扩）内的最长连续片段。"""
    best: list[list[float]] = []
    cur: list[list[float]] = []
    for p in chain:
        if in_bbox(p[0], p[1], pad):
            cur.append(p)
        else:
            if len(cur) > len(best):
                best = cur
            cur = []
    return cur if len(cur) > len(best) else best


SPEED_LIMIT = {"motorway": 80, "trunk": 60, "primary": 50, "secondary": 40, "tertiary": 30}


def build_roads(raw: Path) -> list[dict]:
    ways_by_id: dict[int, dict] = {}
    for f in sorted(raw.glob("roads*.json")):
        for e in read_json(f).get("elements", []):
            if e["type"] == "way":
                ways_by_id[e["id"]] = e
    ways = list(ways_by_id.values())
    groups: dict[str, list[dict]] = defaultdict(list)
    for w in ways:
        t = w.get("tags", {})
        hw = t.get("highway", "")
        if hw.endswith("_link") or t.get("tunnel") in ("yes", "building_passage") or t.get("layer", "0").startswith("-"):
            continue  # 过江隧道等地下道路不参与地面路况渲染
        name = t.get("name:zh-Hans") or t.get("name:zh") or t.get("name") or t.get("ref")
        if not name:
            continue
        coords = [[round(p["lon"], 6), round(p["lat"], 6)] for p in w.get("geometry", [])]
        if len(coords) >= 2:
            groups[name].append({"coords": coords, "tags": t, "hw": hw})

    feats = []
    for name, parts in groups.items():
        # 端点贪心拼接为连续链
        chains: list[list[list[float]]] = []
        pool = [p["coords"] for p in parts]
        while pool:
            chain = pool.pop(0)
            changed = True
            while changed:
                changed = False
                for i, c in enumerate(pool):
                    if dist_m(tuple(chain[-1]), tuple(c[0])) < 3 and smooth(chain[-2], chain[-1], c[1]):
                        chain = chain + c[1:]
                    elif dist_m(tuple(chain[-1]), tuple(c[-1])) < 3 and smooth(chain[-2], chain[-1], c[-2]):
                        chain = chain + c[::-1][1:]
                    elif dist_m(tuple(chain[0]), tuple(c[-1])) < 3 and smooth(c[-2], chain[0], chain[1]):
                        chain = c + chain[1:]
                    elif dist_m(tuple(chain[0]), tuple(c[0])) < 3 and smooth(c[1], chain[0], chain[1]):
                        chain = c[::-1] + chain[1:]
                    else:
                        continue
                    pool.pop(i)
                    changed = True
                    break
            chains.append(chain)

        def length(c):
            return sum(dist_m(tuple(a), tuple(b)) for a, b in zip(c, c[1:]))

        chains = [clip_chain(c) for c in chains]
        chains = [c for c in chains if len(c) >= 2 and length(c) >= 250]
        chains.sort(key=length, reverse=True)
        # 双向分离式道路：两条长度相近的链视为上/下行
        kept: list[list[list[float]]] = []
        for c in chains:
            mid = c[len(c) // 2]
            if any(min(dist_m(tuple(mid), tuple(p)) for p in k) < 45 for k in kept):
                continue  # 与已保留链平行重叠（另一侧车道），可视化上合并
            kept.append(c)
        rank = list(SPEED_LIMIT)
        hw = min((p["hw"] for p in parts), key=lambda h: rank.index(h) if h in rank else len(rank))
        tags = parts[0]["tags"]
        maxspeed = str(tags.get("maxspeed", "")).split()
        speed_limit = int(maxspeed[0]) if maxspeed and maxspeed[0].isdigit() else SPEED_LIMIT.get(hw, 40)
        for i, c in enumerate(kept[:3]):
            feats.append({
                "name": name if len(kept) == 1 else f"{name}（{'一二三'[i]}段）",
                "highway": hw,
                "coords": c,
                "length_m": round(length(c), 1),
                "speed_limit": speed_limit,
                "lanes": int(tags["lanes"]) if str(tags.get("lanes", "")).isdigit() else None,
                "osm_name": name,
            })
    order = {k: i for i, k in enumerate(SPEED_LIMIT)}
    feats.sort(key=lambda r: (order.get(r["highway"], 9), -r["length_m"]))
    return feats


# ---------------------------------------------------------------- 建筑
def classify(tags: dict) -> str:
    b = (tags.get("building") or "yes").lower()
    if b in RESIDENTIAL:
        return "residential"
    if b in COMMERCIAL or "shop" in tags:
        return "commercial"
    if b in OFFICE or "office" in tags:
        return "office"
    if b in PUBLIC or tags.get("amenity") in PUBLIC or "tourism" in tags or "museum" in tags or "historic" in tags:
        return "public"
    if b in INDUSTRIAL:
        return "industrial"
    return "other"


def estimate_height(osm_id: int, area: float, cat: str, tags: dict) -> tuple[float, int | None, str]:
    h = str(tags.get("height", "")).replace("m", "").strip()
    try:
        if h:
            v = float(h)
            if 2 < v < 700:
                return round(v, 1), int(tags["building:levels"]) if str(tags.get("building:levels", "")).isdigit() else None, "osm"
    except ValueError:
        pass
    lv = str(tags.get("building:levels", "")).strip()
    if lv.isdigit() and 0 < int(lv) < 150:
        return round(int(lv) * 3.2, 1), int(lv), "levels"

    r = h01("h", osm_id)
    r2 = h01("t", osm_id)
    if area < 120:
        floors = 2 + int(r * 3)
    elif area < 400:
        floors = 3 + int(r * 5)
    elif area < 1500:
        floors = 5 + int(r * 10)
        if r2 < 0.22 and cat in ("residential", "office", "commercial", "other"):
            floors = 18 + int(r * 22)  # 汉口高层住宅 / 写字楼
    elif area < 5000:
        floors = 4 + int(r * 6)
        if r2 < 0.18:
            floors = 20 + int(r * 30)  # 商业综合体塔楼
    else:
        floors = 3 + int(r * 4)  # 大型商场 / 场馆裙房
    if "historic" in tags or tags.get("building") in ("church", "temple"):
        floors = min(floors, 4)
    return round(floors * 3.2, 1), None, "estimated"


def build_buildings(raw: Path, districts, roads: list[dict]) -> list[dict]:
    seen = set()
    items = []
    for f in sorted(raw.glob("buildings_*.json")):
        for el in read_json(f).get("elements", []):
            key = (el["type"], el["id"])
            if key in seen:
                continue
            seen.add(key)
            tags = el.get("tags", {})
            rings = []
            if el["type"] == "way":
                g = el.get("geometry") or []
                rings.append([[p["lon"], p["lat"]] for p in g])
            else:
                for m in el.get("members", []):
                    if m.get("role") == "outer" and m.get("geometry"):
                        rings.append([[p["lon"], p["lat"]] for p in m["geometry"]])
            for ri, ring in enumerate(rings):
                if len(ring) < 4:
                    continue
                if ring[0] != ring[-1]:
                    if dist_m(tuple(ring[0]), tuple(ring[-1])) > 2:
                        continue
                    ring.append(ring[0])
                ring = [[round(x, 6), round(y, 6)] for x, y in ring]
                area = ring_area_m2(ring)
                if area < 25:
                    continue
                cx, cy = ring_centroid(ring)
                if not in_bbox(cx, cy):
                    continue
                items.append({"osm_id": el["id"] * 10 + ri if ri else el["id"], "tags": tags, "ring": ring, "area": area, "c": (cx, cy)})

    # 道路采样点，用于为无名建筑生成"所在道路"描述
    road_pts = []
    for r in roads:
        for p in r["coords"][:: max(1, len(r["coords"]) // 40)]:
            road_pts.append((p[0], p[1], r["osm_name"]))

    items.sort(key=lambda b: (-round(b["c"][1], 3), b["c"][0]))
    feats = []
    for i, b in enumerate(items, 1):
        bid = f"B{i:04d}"
        tags = b["tags"]
        cat = classify(tags)
        height, levels, src = estimate_height(b["osm_id"], b["area"], cat, tags)
        lon, lat = b["c"]
        district = district_of(lon, lat, districts)
        name = tags.get("name:zh-Hans") or tags.get("name:zh") or tags.get("name") or ""
        if not name:
            near = min(road_pts, key=lambda p: dist_m((lon, lat), (p[0], p[1]))) if road_pts else None
            if near and dist_m((lon, lat), (near[0], near[1])) < 160:
                name = f"{near[2]} · {CATEGORY_CN[cat]} {bid}"
            else:
                name = f"{CATEGORY_CN[cat]} {bid}"
        feats.append({
            "type": "Feature",
            "id": bid,
            "geometry": {"type": "Polygon", "coordinates": [b["ring"]]},
            "properties": {
                "id": bid,
                "osm_id": b["osm_id"],
                "name": name,
                "height": height,
                "levels": levels,
                "height_source": src,
                "category": cat,
                "district": district,
                "grid": grid_of(lon, lat, district),
                "longitude": round(lon, 6),
                "latitude": round(lat, 6),
                "area_m2": round(b["area"], 1),
            },
        })
    return feats


def build_pois(raw: Path) -> list[dict]:
    f = raw / "pois.json"
    if not f.exists():
        return []
    out = []
    seen = set()
    for el in read_json(f)["elements"]:
        t = el.get("tags", {})
        name = t.get("name:zh") or t.get("name")
        kind = t.get("amenity")
        if not name or kind not in ("hospital", "fire_station", "police", "school") or name in seen:
            continue
        lat = el.get("lat") or el.get("center", {}).get("lat")
        lon = el.get("lon") or el.get("center", {}).get("lon")
        if lat is None or not in_bbox(lon, lat, 0.004):
            continue
        seen.add(name)
        out.append({"name": name, "kind": kind, "longitude": round(lon, 6), "latitude": round(lat, 6)})
    out.sort(key=lambda p: (p["kind"], p["name"]))
    for i, p in enumerate(out, 1):
        p["id"] = f"P{i:03d}"
    return [{"id": p["id"], **{k: v for k, v in p.items() if k != "id"}} for p in out]


def main() -> None:
    global BBOX, REGION_NAME, M_PER_DEG_LAT, M_PER_DEG_LON
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default="data/raw/osm")
    ap.add_argument("--out", default="data/geo")
    ap.add_argument("--bbox", nargs=4, type=float, default=(114.15, 30.45, 114.55, 30.72), metavar=("W", "S", "E", "N"))
    ap.add_argument("--region-name", default="武汉中心城区")
    ap.add_argument("--skip-buildings", action="store_true", help="保留 out/buildings.geojson，仅重建路网 / 边界 / POI")
    args = ap.parse_args()
    raw, out = Path(args.raw), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    west, south, east, north = args.bbox
    BBOX = (south, west, north, east)
    REGION_NAME = args.region_name
    M_PER_DEG_LON = 111_320.0 * math.cos(math.radians((south + north) / 2))

    districts = load_district_segments(raw)
    roads = build_roads(raw)
    building_file = out / "buildings.geojson"
    if args.skip_buildings:
        buildings = json.loads(building_file.read_text(encoding="utf-8")).get("features", []) if building_file.exists() else []
    else:
        buildings = build_buildings(raw, districts, roads)
        (building_file).write_text(
            json.dumps({"type": "FeatureCollection", "features": buildings}, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )

    road_feats = []
    for i, r in enumerate(roads, 1):
        rid = f"R{i:03d}"
        road_feats.append({
            "type": "Feature",
            "id": rid,
            "geometry": {"type": "LineString", "coordinates": r["coords"]},
            "properties": {
                "id": rid, "name": r["name"], "highway": r["highway"], "length_m": r["length_m"],
                "speed_limit": r["speed_limit"], "lanes": r["lanes"],
            },
        })
    pois = build_pois(raw)
    poi_file = out / "pois.json"
    if not pois and poi_file.exists():
        pois = read_json(poi_file)

    s, w, n, e = BBOX
    region = {
        "name": REGION_NAME,
        "city": "武汉",
        "center": [round((w + e) / 2 - 0.0005, 4), round((s + n) / 2 - 0.0015, 4)],
        "bbox": [w, s, e, n],
        "grid": {"origin": [w, s], "cell_deg": CELL_DEG, "rows": math.ceil((n - s) / CELL_DEG), "cols": math.ceil((e - w) / CELL_DEG)},
        "district_prefix": DISTRICT_PREFIX,
        "districts": sorted({b["properties"]["district"] for b in buildings}),
        "source": "© OpenStreetMap contributors (ODbL)",
        "stats": {"buildings": len(buildings), "roads": len(road_feats), "pois": len(pois)},
    }

    dump = lambda obj: json.dumps(obj, ensure_ascii=False, separators=(",", ":"))  # noqa: E731
    (out / "roads.geojson").write_text(dump({"type": "FeatureCollection", "features": road_feats}), encoding="utf-8")
    if pois or not poi_file.exists():
        poi_file.write_text(json.dumps(pois, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "region.json").write_text(json.dumps(region, ensure_ascii=False, indent=2), encoding="utf-8")

    srcs = defaultdict(int)
    for b in buildings:
        srcs[b["properties"]["height_source"]] += 1
    print(f"buildings={len(buildings)} {dict(srcs)} roads={len(road_feats)} pois={len(pois)} districts={region['districts']}")


if __name__ == "__main__":
    main()
