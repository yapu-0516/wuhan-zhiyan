from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "data" / "scripts" / "build_wuhan_buildings.py"
SPEC = importlib.util.spec_from_file_location("build_wuhan_buildings", SCRIPT)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


def test_polygon_helpers_accept_multipart_buildings() -> None:
    geometry = {
        "type": "MultiPolygon",
        "coordinates": [
            [[[114.30, 30.55], [114.31, 30.55], [114.31, 30.54], [114.30, 30.55]]],
            [[[114.32, 30.56], [114.33, 30.56], [114.33, 30.55], [114.32, 30.56]]],
        ],
    }
    longitude, latitude = module.centroid(list(module.polygons(geometry)))
    assert 114.30 < longitude < 114.33
    assert 30.54 < latitude < 30.56
    assert module.bounds(list(module.polygons(geometry))) == (114.30, 30.54, 114.33, 30.56)


def test_district_fallback_uses_nearest_centroid() -> None:
    assert module.district_of(114.397, 30.506, {}) == "洪山区"
