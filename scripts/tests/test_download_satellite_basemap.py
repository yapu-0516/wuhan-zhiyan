from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "download_satellite_basemap.py"
SPEC = importlib.util.spec_from_file_location("download_satellite_basemap", SCRIPT)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


def test_wuhan_bbox_tile_count() -> None:
    bounds = module.BBox(114.27, 30.57, 114.312, 30.612)
    x_min, x_max, y_min, y_max = module.tile_range(bounds, 17)
    assert (x_min, x_max, y_min, y_max) == (107140, 107155, 53818, 53836)
    assert (x_max - x_min + 1) * (y_max - y_min + 1) == 304


def test_crop_matches_requested_pixel_size() -> None:
    bounds = module.BBox(114.27, 30.57, 114.312, 30.612)
    zoom = 17
    x_min, _, y_min, _ = module.tile_range(bounds, zoom)
    left, top, right, bottom = module.crop_window(bounds, zoom, x_min, y_min)
    assert (right - left, bottom - top) == (3915, 4547)


def test_tile_url_replaces_xyz() -> None:
    url = module.tile_url(
        "https://tiles.example/{z}/{y}/{x}/tile.jpg?sat={s}",
        16,
        123,
        456,
    )
    assert url == "https://tiles.example/16/456/123/tile.jpg?sat="
