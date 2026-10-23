"""从 OpenStreetMap (Overpass API) 抓取武汉示范区的真实建筑 / 道路 / 行政区边界原始数据。

仅依赖标准库。结果缓存到 --out 目录（每个瓦片一个 JSON），再由 build_geo.py 加工成
前后端使用的 GeoJSON。OSM 数据遵循 ODbL 协议：© OpenStreetMap contributors。

用法：
    python data/scripts/fetch_osm.py --out data/raw/osm
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

# 示范区：汉口沿江片区（江汉路 — 汉口江滩 — 武汉天地，含长江水面）
BBOX = (30.570, 114.270, 30.612, 114.312)  # south, west, north, east
TILE = 0.014

MIRRORS = [
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
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
            with urllib.request.urlopen(req, timeout=180) as r:
                body = r.read()
            return json.loads(body)
        except Exception as e:  # noqa: BLE001 - 镜像不稳定，统一退避重试
            last = e
            print(f"  ! {url.split('/')[2]} 失败 ({e.__class__.__name__}: {str(e)[:80]})，{delay:.0f}s 后重试")
            time.sleep(delay)
            delay = min(delay * 1.5, 90)
    raise RuntimeError(f"Overpass 查询多次失败: {last}")


def tiles():
    s, w, n, e = BBOX
    lat = s
    while lat < n - 1e-9:
        lon = w
        while lon < e - 1e-9:
            yield (round(lat, 4), round(lon, 4), round(min(lat + TILE, n), 4), round(min(lon + TILE, e), 4))
            lon += TILE
        lat += TILE


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/raw/osm")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    jobs = []
    for t in tiles():
        bb = ",".join(map(str, t))
        jobs.append((f"buildings_{bb}", f'[out:json][timeout:120];(way["building"]({bb});relation["building"]({bb}););out geom tags;'))
        jobs.append((f"roads_{bb}", f'[out:json][timeout:120];way["highway"~"^(motorway|trunk|primary|secondary|tertiary)$"]({bb});out geom tags;'))
    s, w, n, e = BBOX
    bb = f"{s},{w},{n},{e}"
    jobs.append(("water", f'[out:json][timeout:120];(way["natural"="water"]({bb});relation["natural"="water"]({bb});way["waterway"="riverbank"]({bb}););out geom tags;'))
    # 行政区边界：按区分别取外环 way 几何（relation 的 out geom 在部分镜像上不返回成员）
    for dname in ("江汉区", "江岸区", "硚口区", "武昌区"):
        jobs.append((f"district_{dname}", f'[out:json][timeout:120];rel["boundary"="administrative"]["admin_level"="6"]["name"="{dname}"]({bb});way(r);out geom;'))
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
        f.write_text(json.dumps(d, ensure_ascii=False))
        print(f"✓ {name}: {len(d.get('elements', []))} elements", flush=True)
        time.sleep(4)
    if failed:
        print(f"以下任务失败，可重新运行脚本续传：{failed}")


if __name__ == "__main__":
    main()
