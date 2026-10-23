import numpy as np
import pytest

from cityeye_algo.fire import FireDetector

from conftest import city_background, paint_flame, sample, save


@pytest.fixture
def det() -> FireDetector:
    return FireDetector()


def test_procedural_flame_detected(det, rng, tmp_path):
    img = city_background(rng)
    paint_flame(img, 360, 240, 40, rng)
    r = det.analyze([save(img, tmp_path / "f.jpg")], tmp_path, "t")
    assert r.detected and r.confidence > 0.6
    flame = [d for d in r.detections if d.label == "flame"]
    x, y, w, h = flame[0].bbox
    assert x <= 360 <= x + w and y <= 240 <= y + h
    assert r.metrics["flame_area_ratio"] > 0.002
    assert (tmp_path / "t_annotated.jpg").exists()


def test_red_roofs_and_orange_car_not_detected(det, rng, tmp_path):
    """红瓦屋面 + 橙色车辆：颜色满足火焰色彩规则，但无焰心、纹理均匀，必须不报警。"""
    img = city_background(rng)
    # 亮橙色彩钢屋面 / 红瓦：能通过 YCbCr+RGB 色彩规则，用于检验区域级校验
    for x, y, c in ((60, 60, (240, 140, 70)), (300, 200, (236, 128, 62)), (500, 80, (244, 150, 76))):
        img[y : y + 90, x : x + 140] = np.array(c) + rng.normal(0, 3, (90, 140, 3))
    img[400:418, 600:648] = (236, 120, 28)  # 橙色车辆
    img[404:408, 610:620] = (255, 235, 210)  # 车身高光
    r = det.analyze([save(img, tmp_path / "n.jpg")], tmp_path, "n")
    assert not r.detected
    assert r.confidence == 0.0
    assert r.metrics["rejected_candidates"] >= 3


def test_plain_city_not_detected(det, rng, tmp_path):
    r = det.analyze([save(city_background(rng), tmp_path / "c.jpg")], tmp_path, "c")
    assert not r.detected and r.metrics["flame_regions"] == 0


@pytest.mark.parametrize("name", ["fire/drone_fire_01.jpg", "fire/drone_fire_02.jpg", "fire/drone_fire_03_night.jpg"])
def test_samples_positive(det, tmp_path, name):
    r = det.analyze([sample(name)], tmp_path, "s")
    assert r.detected and r.confidence >= 0.7


@pytest.mark.parametrize("name", ["fire/drone_normal_01.jpg", "fire/drone_sunset_roofs.jpg"])
def test_samples_negative(det, tmp_path, name):
    r = det.analyze([sample(name)], tmp_path, "s")
    assert not r.detected


def test_smoke_scored_on_sample_with_plume(det, tmp_path):
    r = det.analyze([sample("fire/drone_fire_01.jpg")], tmp_path, "s")
    assert r.metrics["smoke_score"] >= 0.35
