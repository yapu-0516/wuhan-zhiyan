from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "data" / "scripts" / "fetch_city_pois.py"
SPEC = importlib.util.spec_from_file_location("fetch_city_pois", SCRIPT)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


def test_rejects_irrelevant_poi_names() -> None:
    assert module.valid_name("武汉市中心医院", "hospital")
    assert module.valid_name("水果湖消防救援站", "fire_station")
    assert not module.valid_name("中部战区总医院家属区", "hospital")
    assert not module.valid_name("消防科普主题公园", "fire_station")


def test_merge_drops_nearby_duplicate() -> None:
    existing = [{"name": "武汉市中心医院", "kind": "hospital", "longitude": 114.28, "latitude": 30.58}]
    candidates = [
        {"name": "武汉市中心医院", "kind": "hospital", "longitude": 114.2801, "latitude": 30.5801},
        {"name": "武汉市第六医院", "kind": "hospital", "longitude": 114.29, "latitude": 30.59},
    ]
    result = module.merge(existing, candidates)
    assert len(result) == 2
    assert [item["id"] for item in result] == ["P001", "P002"]
