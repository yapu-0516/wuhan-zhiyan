#!/usr/bin/env python3
"""把示范区的卫星瓦片拼接成本地单幅底图。

默认读取 data/geo/region.json 的范围，从 Esri World Imagery 下载 z17 瓦片，
裁切后写入 frontend/public/basemap/wuhan-satellite-z17.jpg。
单幅图片由前端 SingleTileImageryProvider 一次加载，避免大量在线瓦片请求超时。

用法：
    python scripts/download_satellite_basemap.py
    python scripts/download_satellite_basemap.py --zoom 16 --quality 86
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from PIL import Image

TILE_SIZE = 256
DEFAULT_TILE_URL = (
    "https://server.arcgisonline.com/ArcGIS/rest/services/"
    "World_Imagery/MapServer/tile/{z}/{y}/{x}"
)
DEFAULT_ATTRIBUTION = "Esri, Maxar, Earthstar Geographics"
DEFAULT_REGION = Path("data/geo/region.json")
DEFAULT_OUTPUT = Path("frontend/public/basemap/wuhan-satellite-z17.jpg")
USER_AGENT = "CityEye-Offline-Basemap/1.0 (+local demo cache)"


@dataclass(frozen=True)
class BBox:
    west: float
    south: float
    east: float
    north: float

    def validate(self) -> None:
        if not (-180 <= self.west < self.east <= 180):
            raise ValueError("经度范围无效：应为 -180 <= west < east <= 180")
        if not (-85.05112878 < self.south < self.north < 85.05112878):
            raise ValueError("纬度范围无效：应位于 Web Mercator 可表示范围内")


def lon_to_tile_x(lon: float, zoom: int) -> float:
    return (lon + 180.0) / 360.0 * (2**zoom)


def lat_to_tile_y(lat: float, zoom: int) -> float:
    lat_rad = math.radians(lat)
    return (
        1.0
        - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi
    ) / 2.0 * (2**zoom)


def tile_range(bounds: BBox, zoom: int) -> tuple[int, int, int, int]:
    """返回覆盖 bbox 的闭区间瓦片编号 x_min, x_max, y_min, y_max。"""
    bounds.validate()
    x_min = math.floor(lon_to_tile_x(bounds.west, zoom))
    x_max = math.ceil(lon_to_tile_x(bounds.east, zoom)) - 1
    y_min = math.floor(lat_to_tile_y(bounds.north, zoom))
    y_max = math.ceil(lat_to_tile_y(bounds.south, zoom)) - 1
    return x_min, x_max, y_min, y_max


def crop_window(
    bounds: BBox, zoom: int, x_min: int, y_min: int
) -> tuple[int, int, int, int]:
    """返回在拼接大图中的精确裁切框。"""
    west_x = lon_to_tile_x(bounds.west, zoom)
    east_x = lon_to_tile_x(bounds.east, zoom)
    north_y = lat_to_tile_y(bounds.north, zoom)
    south_y = lat_to_tile_y(bounds.south, zoom)
    return (
        round((west_x - x_min) * TILE_SIZE),
        round((north_y - y_min) * TILE_SIZE),
        round((east_x - x_min) * TILE_SIZE),
        round((south_y - y_min) * TILE_SIZE),
    )


def parse_bbox(value: str) -> BBox:
    try:
        parts = tuple(float(part.strip()) for part in value.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("bbox 必须是四个逗号分隔的数字") from exc
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("bbox 必须包含 west,south,east,north")
    return BBox(*parts)


def read_bbox(path: Path) -> BBox:
    payload = json.loads(path.read_text(encoding="utf-8"))
    bounds = payload.get("bbox")
    if not isinstance(bounds, list) or len(bounds) != 4:
        raise ValueError(f"{path} 缺少合法的 bbox 字段")
    return BBox(*(float(value) for value in bounds))


def tile_url(template: str, zoom: int, x: int, y: int) -> str:
    return (
        template.replace("{z}", str(zoom))
        .replace("{x}", str(x))
        .replace("{y}", str(y))
        .replace("{s}", "")
    )


def download_tile(
    template: str, zoom: int, x: int, y: int, retries: int = 4
) -> tuple[int, int, bytes]:
    url = tile_url(template, zoom, x, y)
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            request = Request(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "image/jpeg,image/png,image/*;q=0.8",
                },
            )
            with urlopen(request, timeout=30) as response:
                payload = response.read()
            if not payload:
                raise ValueError("瓦片响应为空")
            Image.open(BytesIO(payload)).verify()
            return x, y, payload
        except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
            last_error = exc
            if attempt + 1 < retries:
                time.sleep(0.7 * (2**attempt))
    raise RuntimeError(f"瓦片下载失败 {url}: {last_error}") from last_error


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="下载 CityEye 示范区卫星底图并拼接为本地单幅图片"
    )
    parser.add_argument(
        "--region-json",
        type=Path,
        default=DEFAULT_REGION,
        help=f"包含 bbox 的区域配置（默认 {DEFAULT_REGION}）",
    )
    parser.add_argument(
        "--bbox",
        type=parse_bbox,
        help="覆盖区域配置，格式 west,south,east,north",
    )
    parser.add_argument("--zoom", type=int, default=17, help="瓦片级别（默认 17）")
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"输出图片（默认 {DEFAULT_OUTPUT}）",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        help="下载清单路径（默认与图片同目录、同名 .json）",
    )
    parser.add_argument("--quality", type=int, default=88, help="JPEG 质量 1-95")
    parser.add_argument("--workers", type=int, default=8, help="并发下载数")
    parser.add_argument("--retries", type=int, default=4, help="单张瓦片重试次数")
    parser.add_argument("--tile-url", default=DEFAULT_TILE_URL, help="XYZ 瓦片模板")
    parser.add_argument(
        "--attribution",
        default=DEFAULT_ATTRIBUTION,
        help="图片版权署名",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not 1 <= args.quality <= 95:
        parser.error("--quality 必须在 1-95 之间")
    if not 1 <= args.workers <= 32:
        parser.error("--workers 必须在 1-32 之间")
    if not 1 <= args.retries <= 10:
        parser.error("--retries 必须在 1-10 之间")
    if not 1 <= args.zoom <= 19:
        parser.error("--zoom 必须在 1-19 之间")

    bounds = args.bbox or read_bbox(args.region_json)
    x_min, x_max, y_min, y_max = tile_range(bounds, args.zoom)
    columns = x_max - x_min + 1
    rows = y_max - y_min + 1
    total = columns * rows
    print(
        f"下载 {bounds.west:.6f},{bounds.south:.6f} → "
        f"{bounds.east:.6f},{bounds.north:.6f}，z{args.zoom}，"
        f"{columns}×{rows} = {total} 张瓦片"
    )

    tiles: dict[tuple[int, int], bytes] = {}
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [
            executor.submit(
                download_tile,
                args.tile_url,
                args.zoom,
                x,
                y,
                args.retries,
            )
            for y in range(y_min, y_max + 1)
            for x in range(x_min, x_max + 1)
        ]
        for index, future in enumerate(as_completed(futures), start=1):
            x, y, payload = future.result()
            tiles[(x, y)] = payload
            if index == total or index % max(1, total // 10) == 0:
                print(f"  已完成 {index}/{total}")

    mosaic = Image.new("RGB", (columns * TILE_SIZE, rows * TILE_SIZE), (20, 24, 28))
    for y in range(y_min, y_max + 1):
        for x in range(x_min, x_max + 1):
            with Image.open(BytesIO(tiles[(x, y)])) as tile:
                tile = tile.convert("RGB")
                if tile.size != (TILE_SIZE, TILE_SIZE):
                    tile = tile.resize((TILE_SIZE, TILE_SIZE), Image.Resampling.LANCZOS)
                mosaic.paste(tile, ((x - x_min) * TILE_SIZE, (y - y_min) * TILE_SIZE))

    cropped = mosaic.crop(crop_window(bounds, args.zoom, x_min, y_min))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    cropped.save(args.out, "JPEG", quality=args.quality, optimize=True, progressive=True)

    manifest_path = args.manifest or args.out.with_suffix(".json")
    manifest = {
        "bounds": [bounds.west, bounds.south, bounds.east, bounds.north],
        "zoom": args.zoom,
        "tile_size": TILE_SIZE,
        "tile_range": [x_min, x_max, y_min, y_max],
        "tile_count": total,
        "pixel_size": [cropped.width, cropped.height],
        "source": args.tile_url,
        "attribution": args.attribution,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    size_mb = args.out.stat().st_size / 1024 / 1024
    print(
        f"已生成 {args.out}（{cropped.width}×{cropped.height}，{size_mb:.1f} MB）"
    )
    print(f"下载清单 {manifest_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"错误：{exc}", file=sys.stderr)
        raise SystemExit(1) from exc
