from __future__ import annotations

import shutil
from dataclasses import replace


def test_building_spatial_properties_can_be_maintained(client, ctx, tmp_path):
    buildings = client.get("/api/buildings").json()
    building_id = buildings["features"][0]["properties"]["id"]
    original_settings = ctx.settings
    temp_geo = tmp_path / "geo"
    shutil.copytree(original_settings.geo_dir, temp_geo)
    ctx.settings = replace(original_settings, geo_dir=temp_geo)
    ctx.reload_geo()
    try:
        current = client.get(f"/api/spatial/building/{building_id}")
        assert current.status_code == 200
        updated = client.patch(
            f"/api/spatial/building/{building_id}",
            json={"properties": {"name": "维护测试建筑", "category": "public"}},
        )
        assert updated.status_code == 200
        assert updated.json()["properties"]["name"] == "维护测试建筑"
        again = client.get(f"/api/spatial/building/{building_id}")
        assert again.json()["properties"]["category"] == "public"
    finally:
        ctx.settings = original_settings
        ctx.reload_geo()
