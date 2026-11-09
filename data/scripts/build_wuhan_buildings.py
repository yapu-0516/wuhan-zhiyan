"""把武汉建筑轮廓生成全市概览与按区精细图层。

原始文件字段：OBJECTID / Floor / Shape_Leng / Shape_Area。OBJECTID 不唯一，
因此按源文件顺序生成稳定 ID，并按“楼层 × 3.2 米”生成用于三维拉伸的估算高度。
概览层只抽样约 1/8 建筑并保留高层；精细层按行政区拆分，前端一次只加载一个区。
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = REPO_ROOT / "data" / "datasets" / "raw" / "wuhan_buildings" / "wh_building.json"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "geo" / "buildings.geojson"
DEFAULT_TILES = REPO_ROOT / "data" / "datasets" / "derived" / "buildings" / "districts"
DEFAULT_BBOX = (114.15, 30.45, 114.55, 30.72)
DEFAULT_DISTRICTS_RAW = REPO_ROOT / "data" / "raw" / "osm"
CELL_DEG = 0.0045
DISTRICTS = {
    "江汉区": ("JH", 114.271, 30.601),
    "江岸区": ("JA", 114.309, 30.625),
    "硚口区": ("QK", 114.216, 30.585),
    "汉阳区": ("HY", 114.218, 30.553),
    "武昌区": ("WC", 114.316, 30.553),
    "洪山区": ("HS", 114.397, 30.506),
    "青山区": ("QS", 114.405, 30.640),
}
M_PER_DEG_LAT = 111_320.0


def polygons(geometry: dict[str, Any]) -> Iterable[list[list[float]]]:
    if geometry.get("type") == "Polygon":
        yield geometry.get("coordinates", [])
    elif geometry.get("type") == "MultiPolygon":
        yield from geometry.get("coordinates", [])


def centroid(parts: list[list[list[float]]]) -> tuple[float, float]:
    points = [point for part in parts for ring in part for point in ring]
    return sum(p[0] for p in points) / len(points), sum(p[1] for p in points) / len(points)


def bounds(parts: list[list[list[float]]]) -> tuple[float, float, float, float]:
    points = [point for part in parts for ring in part for point in ring]
    return min(p[0] for p in points), min(p[1] for p in points), max(p[0] for p in points), max(p[1] for p in points)


def load_district_segments(raw: Path) -> dict[str, list[tuple[float, float, float, float]]]:
    out: dict[str, list[tuple[float, float, float, float]]] = {}
    for name in DISTRICTS:
        path = raw / f"district_{name}.json"
        if not path.exists():
            continue
        segments = []
        for element in json.loads(path.read_text(encoding="utf-8")).get("elements", []):
            geometry = element.get("geometry") or []
            for start, end in zip(geometry, geometry[1:]):
                segments.append((start["lon"], start["lat"], end["lon"], end["lat"]))
        if segments:
            out[name] = segments
    return out


def point_in_segments(lon: float, lat: float, segments: list[tuple[float, float, float, float]]) -> bool:
    inside = False
    for x1, y1, x2, y2 in segments:
        if (y1 > lat) != (y2 > lat):
            if x1 + (lat - y1) * (x2 - x1) / (y2 - y1) > lon:
                inside = not inside
    return inside


def district_of(lon: float, lat: float, districts: dict[str, list[tuple[float, float, float, float]]]) -> str:
    for name, segments in districts.items():
        if point_in_segments(lon, lat, segments):
            return name
    m_per_deg_lon = M_PER_DEG_LAT * math.cos(math.radians(lat))
    return min(
        DISTRICTS,
        key=lambda name: math.hypot((lon - DISTRICTS[name][1]) * m_per_deg_lon, (lat - DISTRICTS[name][2]) * M_PER_DEG_LAT),
    )


def grid_of(lon: float, lat: float, district: str, origin: tuple[float, float]) -> str:
    row = max(1, math.floor((lat - origin[1]) / CELL_DEG) + 1)
    col = max(1, math.floor((lon - origin[0]) / CELL_DEG) + 1)
    return f"{DISTRICTS[district][0]}-{row:02d}-{col:02d}"


def compact_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="生成武汉中心城区概览与按区精细建筑图层")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--tiles-dir", type=Path, default=DEFAULT_TILES)
    parser.add_argument("--districts-raw", type=Path, default=DEFAULT_DISTRICTS_RAW)
    parser.add_argument("--bbox", nargs=4, type=float, default=DEFAULT_BBOX, metavar=("WEST", "SOUTH", "EAST", "NORTH"))
    parser.add_argument("--overview-stride", type=int, default=8, help="概览层抽样间隔；高层建筑始终保留")
    parser.add_argument("--detail-stride", type=int, default=1, help="分区精细层抽样间隔；1 表示保留全部建筑")
    args = parser.parse_args()
    if args.overview_stride < 1 or args.detail_stride < 1:
        parser.error("抽样间隔必须大于 0")

    west, south, east, north = args.bbox
    source = json.loads(args.source.read_text(encoding="utf-8-sig"))
    district_segments = load_district_segments(args.districts_raw)
    buckets: dict[str, list[dict[str, Any]]] = {name: [] for name in DISTRICTS}
    overview: list[dict[str, Any]] = []

    for index, raw in enumerate(source.get("features", []), 1):
        geometry = raw.get("geometry") or {}
        parts = list(polygons(geometry))
        if not parts:
            continue
        longitude, latitude = centroid(parts)
        if not (west <= longitude <= east and south <= latitude <= north):
            continue

        props = raw.get("properties") or {}
        floors = max(1, min(68, int(props.get("Floor") or 1)))
        area = round(float(props.get("Shape_Area") or 0), 2)
        district = district_of(longitude, latitude, district_segments)
        building_id = f"WHB{index:06d}"
        feature = {
            "type": "Feature",
            "id": building_id,
            "geometry": geometry,
            "properties": {
                "id": building_id,
                "name": f"建筑 {building_id}",
                "height": round(floors * 3.2, 1),
                "levels": floors,
                "height_source": "floor",
                "category": "other",
                "district": district,
                "grid": grid_of(longitude, latitude, district, (west, south)),
                "longitude": round(longitude, 7),
                "latitude": round(latitude, 7),
                "area_m2": area,
                "monitored": False,
                "risk_level": "normal",
            },
        }
        if index % args.detail_stride == 0:
            buckets[district].append(feature)
        if index % args.overview_stride == 0 or floors >= 20 or area >= 5000:
            overview.append(feature)

    compact_json(args.output, {"type": "FeatureCollection", "features": overview})
    manifest_districts = []
    for name, features in buckets.items():
        prefix, lon, lat = DISTRICTS[name]
        file_name = f"{prefix}.geojson"
        compact_json(args.tiles_dir / file_name, {"type": "FeatureCollection", "features": features})
        if features:
            all_bounds = [bounds(list(polygons(f["geometry"]))) for f in features]
            district_bbox = [
                min(b[0] for b in all_bounds),
                min(b[1] for b in all_bounds),
                max(b[2] for b in all_bounds),
                max(b[3] for b in all_bounds),
            ]
        else:
            district_bbox = [west, south, east, north]
        manifest_districts.append(
            {
                "name": name,
                "prefix": prefix,
                "center": [lon, lat],
                "bbox": district_bbox,
                "count": len(features),
                "url": f"/api/buildings/fine?district={name}",
            }
        )

    compact_json(
        args.tiles_dir / "manifest.json",
        {
            "bbox": [west, south, east, north],
            "overview_url": "/api/buildings",
            "overview_count": len(overview),
            "districts": manifest_districts,
            "source": "武汉建筑轮廓楼层数据；仅用于演示体量表达",
        },
    )
    print(
        f"概览 {len(overview)} 栋；分区 " +
        "，".join(f"{name} {len(features)}" for name, features in buckets.items()) +
        f"；输出 {args.output}"
    )


if __name__ == "__main__":
    main()
