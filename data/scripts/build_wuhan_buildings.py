"""把武汉建筑轮廓 GeoJSON 裁剪为 Demo 所用的派生图层。

原始文件字段：OBJECTID / Floor / Shape_Leng / Shape_Area。OBJECTID 不唯一，
因此这里重新生成稳定 ID，并按“楼层 × 3.2 米”生成用于三维拉伸的估算高度。
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = REPO_ROOT / "data" / "datasets" / "raw" / "wuhan_buildings" / "wh_building.json"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "datasets" / "derived" / "buildings" / "wuhan_demo_buildings.geojson"
DEFAULT_BBOX = (114.27, 30.57, 114.312, 30.612)


def polygons(geometry: dict[str, Any]) -> Iterable[list[list[float]]]:
    if geometry.get("type") == "Polygon":
        yield geometry.get("coordinates", [])
    elif geometry.get("type") == "MultiPolygon":
        yield from geometry.get("coordinates", [])


def main() -> None:
    parser = argparse.ArgumentParser(description="裁剪武汉建筑轮廓并生成 Demo 派生数据")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--bbox", nargs=4, type=float, default=DEFAULT_BBOX, metavar=("WEST", "SOUTH", "EAST", "NORTH"))
    args = parser.parse_args()

    west, south, east, north = args.bbox
    source = json.loads(args.source.read_text(encoding="utf-8-sig"))
    features: list[dict[str, Any]] = []

    for raw in source.get("features", []):
        geometry = raw.get("geometry") or {}
        parts = list(polygons(geometry))
        points = [point for part in parts for ring in part for point in ring]
        if not points:
            continue
        longitude = sum(point[0] for point in points) / len(points)
        latitude = sum(point[1] for point in points) / len(points)
        if not (west <= longitude <= east and south <= latitude <= north):
            continue

        props = raw.get("properties") or {}
        floors = max(1, min(68, int(props.get("Floor") or 1)))
        building_id = f"WHB{len(features) + 1:06d}"
        features.append(
            {
                "type": "Feature",
                "id": building_id,
                "geometry": geometry,
                "properties": {
                    "id": building_id,
                    "name": f"精细建筑 {building_id[3:]}",
                    "height": round(floors * 3.2, 1),
                    "levels": floors,
                    "height_source": "floor",
                    "category": "other",
                    "district": "",
                    "grid": "",
                    "longitude": round(longitude, 7),
                    "latitude": round(latitude, 7),
                    "area_m2": round(float(props.get("Shape_Area") or 0), 2),
                    "monitored": False,
                    "risk_level": "normal",
                },
            }
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = {"type": "FeatureCollection", "features": features}
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"生成 {len(features)} 栋建筑：{args.output}")


if __name__ == "__main__":
    main()
