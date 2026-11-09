"""用 Nominatim 补充七城区应急资源点，并与现有 OSM POI 合并去重。

Nominatim 查询按城区拆分以限制结果范围；每次请求间隔 1.1 秒。
只保留能明确归入七城区的医院、消防站、派出所和学校，不生成模拟点位。
"""
from __future__ import annotations

import argparse
import json
import math
import ssl
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "data" / "geo" / "pois.json"
SEARCH_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "CityEye-demo/1.0"
BBOX = (114.15, 30.45, 114.55, 30.72)
DISTRICTS = ("江岸区", "江汉区", "硚口区", "汉阳区", "武昌区", "洪山区", "青山区")
TERMS = {
    "hospital": ("医院",),
    "fire_station": ("消防站", "消防救援站", "消防"),
    "police": ("派出所",),
    "school": ("学校",),
}
VALID_NAME = {
    "hospital": ("医院", "急救中心", "卫生院", "医疗中心"),
    "fire_station": ("消防", "救援站"),
    "police": ("派出所", "公安局"),
    "school": ("学校", "小学", "中学", "大学", "学院", "幼儿园"),
}


def search(term: str, district: str, limit: int) -> list[dict[str, Any]]:
    query = urllib.parse.urlencode(
        {
            "format": "jsonv2",
            "limit": limit,
            "bounded": 1,
            "countrycodes": "cn",
            "viewbox": f"{BBOX[0]},{BBOX[3]},{BBOX[2]},{BBOX[1]}",
            "q": f"{district} {term}",
        }
    )
    request = urllib.request.Request(f"{SEARCH_URL}?{query}", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=45, context=ssl._create_unverified_context()) as response:
        return json.loads(response.read())


def district_in_text(item: dict[str, Any]) -> str | None:
    text = str(item.get("display_name", ""))
    return next((district for district in DISTRICTS if district in text), None)


def valid_name(name: str, kind: str) -> bool:
    invalid = ("宿舍", "家属区", "旧址", "公园", "人家", "科普")
    return bool(name) and name not in ("消防", "医院", "学校", "派出所") and any(
        token in name for token in VALID_NAME[kind]
    ) and not any(token in name for token in invalid)


def distance_m(a: dict[str, Any], b: dict[str, Any]) -> float:
    dx = (float(a["longitude"]) - float(b["longitude"])) * 95_800
    dy = (float(a["latitude"]) - float(b["latitude"])) * 110_540
    return math.hypot(dx, dy)


def merge(existing: list[dict[str, Any]], candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged = [dict(item) for item in existing if valid_name(str(item.get("name", "")), str(item.get("kind", "")))]
    for candidate in candidates:
        if any(item["kind"] == candidate["kind"] and distance_m(item, candidate) < 80 for item in merged):
            continue
        merged.append(candidate)
    for index, item in enumerate(sorted(merged, key=lambda row: (row["kind"], row["name"], row["longitude"])), 1):
        item["id"] = f"P{index:03d}"
    return sorted(merged, key=lambda row: (row["kind"], row["name"]))


def main() -> None:
    parser = argparse.ArgumentParser(description="补充七城区应急资源 POI")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--districts", nargs="+", choices=DISTRICTS, default=list(DISTRICTS))
    parser.add_argument("--kinds", nargs="+", choices=tuple(TERMS), default=list(TERMS))
    parser.add_argument("--merge-only", action="store_true", help="只清理和去重现有文件，不发起网络查询")
    args = parser.parse_args()
    existing = json.loads(args.output.read_text(encoding="utf-8")) if args.output.exists() else []
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()

    for district in (() if args.merge_only else args.districts):
        for kind in args.kinds:
            terms = TERMS[kind]
            for term in terms:
                try:
                    results = search(term, district, args.limit)
                except Exception as exc:  # noqa: BLE001 - 单个查询失败不应丢弃其它城区结果
                    print(f"跳过 {district} {term}: {exc}")
                    results = []
                for item in results:
                    lon, lat = float(item.get("lon", 0)), float(item.get("lat", 0))
                    owner = district_in_text(item)
                    name = str(item.get("name") or item.get("display_name", "").split(",", 1)[0]).strip()
                    key = f"{item.get('osm_type')}:{item.get('osm_id')}"
                    if owner != district or not (BBOX[0] <= lon <= BBOX[2] and BBOX[1] <= lat <= BBOX[3]):
                        continue
                    if not valid_name(name, kind) or key in seen:
                        continue
                    seen.add(key)
                    candidates.append(
                        {"name": name, "kind": kind, "longitude": round(lon, 6), "latitude": round(lat, 6)}
                    )
                time.sleep(1.1)

    pois = merge(existing, candidates)
    args.output.write_text(json.dumps(pois, ensure_ascii=False, indent=1), encoding="utf-8")
    counts = {kind: sum(item["kind"] == kind for item in pois) for kind in TERMS}
    print(f"应急资源点 {len(pois)}：{counts}")


if __name__ == "__main__":
    main()
