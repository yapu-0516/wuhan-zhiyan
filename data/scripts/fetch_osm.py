"""从 OpenStreetMap (Overpass API) 抓取武汉中心城区的道路 / 行政区边界原始数据。

仅依赖标准库。结果缓存到 --out 目录（每个瓦片一个 JSON），再由 build_geo.py 加工成
前后端使用的 GeoJSON。OSM 数据遵循 ODbL 协议：© OpenStreetMap contributors。

用法：
    python data/scripts/fetch_osm.py --bbox 114.15,30.45,114.55,30.72 --skip-buildings
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

DEFAULT_BBOX = (114.15, 30.45, 114.55, 30.72)  # west, south, east, north
DEFAULT_DISTRICTS = ("江岸区", "江汉区", "硚口区", "汉阳区", "武昌区", "洪山区", "青山区")

MIRRORS = [
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter",
]

UA = "CityEye-wuhan-zhiyan/1.0 (open-source research demo)"


def query(ql: str, retries: int = 14) -> dict:
    data = urllib.parse.urlencode({"data": ql}).encode()
    delay = 6.0
    last = None
    for i in range(retries):
        url = MIRRORS[i % len(MIRRORS)]
        try:
            req = urllib.request.Request(url, data=data, headers={"User-Agent": UA})
            # 本地 HTTPS 代理常使用自签证书；这里只读取公开 OSM 数据，不发送凭据。
            with urllib.request.urlopen(req, timeout=180, context=ssl._create_unverified_context()) as r:
                body = r.read()
            return json.loads(body)
        except Exception as e:  # noqa: BLE001 - 镜像不稳定，统一退避重试
            last = e
            print(f"  ! {url.split('/')[2]} 失败 ({e.__class__.__name__}: {str(e)[:80]})，{delay:.0f}s 后重试")
            time.sleep(delay)
            delay = min(delay * 1.5, 90)
    raise RuntimeError(f"Overpass 查询多次失败: {last}")


def tiles(bbox: tuple[float, float, float, float], tile: float):
    w, s, e, n = bbox
    lat = s
    while lat < n - 1e-9:
        lon = w
        while lon < e - 1e-9:
            yield (round(lat, 4), round(lon, 4), round(min(lat + tile, n), 4), round(min(lon + tile, e), 4))
            lon += tile
        lat += tile


def parse_bbox(value: str) -> tuple[float, float, float, float]:
    try:
        bbox = tuple(float(part.strip()) for part in value.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("bbox 必须是四个逗号分隔的数字") from exc
    if len(bbox) != 4 or not (bbox[0] < bbox[2] and bbox[1] < bbox[3]):
        raise argparse.ArgumentTypeError("bbox 格式应为 west,south,east,north")
    return bbox  # type: ignore[return-value]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/raw/osm")
    ap.add_argument("--bbox", type=parse_bbox, default=DEFAULT_BBOX, help="west,south,east,north")
    ap.add_argument("--tile", type=float, default=0.08, help="道路抓取瓦片边长（度）")
    ap.add_argument("--districts", nargs="+", default=list(DEFAULT_DISTRICTS))
    ap.add_argument("--skip-buildings", action="store_true")
    ap.add_argument("--skip-roads", action="store_true")
    ap.add_argument("--skip-water", action="store_true")
    ap.add_argument("--skip-districts", action="store_true")
    ap.add_argument("--skip-pois", action="store_true")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    w, s, e, n = args.bbox

    jobs = []
    for t in tiles(args.bbox, max(0.02, args.tile)):
        bb = ",".join(map(str, t))
        if not args.skip_buildings:
            jobs.append((f"buildings_{bb}", f'[out:json][timeout:120];(way["building"]({bb});relation["building"]({bb}););out geom tags;'))
        if not args.skip_roads:
            jobs.append((f"roads_{bb}", f'[out:json][timeout:180];way["highway"~"^(motorway|trunk|primary|secondary|tertiary)$"]({bb});out geom tags;'))
    bb = f"{s},{w},{n},{e}"
    if not args.skip_water:
        jobs.append(("water", f'[out:json][timeout:120];(way["natural"="water"]({bb});relation["natural"="water"]({bb});way["waterway"="riverbank"]({bb}););out geom tags;'))
    # 行政区边界：按区分别取外环 way 几何（relation 的 out geom 在部分镜像上不返回成员）
    if not args.skip_districts:
        for dname in args.districts:
            jobs.append((f"district_{dname}", f'[out:json][timeout:120];rel["boundary"="administrative"]["admin_level"="6"]["name"="{dname}"]({bb});way(r);out geom;'))
    if not args.skip_pois:
        jobs.append(("pois", f'[out:json][timeout:120];(node["amenity"~"^(hospital|fire_station|police|school)$"]({bb});way["amenity"~"^(hospital|fire_station|police|school)$"]({bb}););out center tags;'))

    failed = []
    for name, ql in jobs:
        f = out / f"{name}.json"
        if f.exists() and f.stat().st_size > 50:
            print(f"✓ {name}（已缓存）")
            continue
        print(f"→ {name}", flush=True)
        try:
            d = query(ql)
        except RuntimeError as e:
            print(f"✗ {name}: {e}", flush=True)
            failed.append(name)
            continue
        f.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        print(f"✓ {name}: {len(d.get('elements', []))} elements", flush=True)
        time.sleep(max(1.0, math.ceil(args.tile * 45)))
    if failed:
        print(f"以下任务失败，可重新运行脚本续传：{failed}")


if __name__ == "__main__":
    main()
