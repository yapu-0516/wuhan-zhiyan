import pytest

import cityeye_algo as ca

from conftest import sample


def test_algorithms_metadata():
    algos = ca.algorithms()
    assert {a["type"] for a in algos} == set(ca.EVENT_TYPES)
    assert all({"type", "name", "version", "method"} == set(a) for a in algos)


@pytest.mark.parametrize(
    "etype,files,key",
    [
        ("fire", ["a.jpg"], "fire.image"),
        ("traffic", ["a.csv"], "traffic.series"),
        ("traffic", ["a.png"], "traffic.image"),
        ("building", ["a.csv"], "building.series"),
        ("building", ["a.jpg", "b.jpg"], "building.change"),
        ("flood", ["a.csv"], "flood.series"),
        ("flood", ["a.jpeg"], "flood.image"),
    ],
)
def test_select(etype, files, key):
    assert ca.select(etype, files).meta.key == key


@pytest.mark.parametrize(
    "etype,files,msg",
    [
        ("smoke", ["a.jpg"], "不支持的分析类型"),
        ("fire", ["a.csv"], "图片"),
        ("fire", ["a.txt"], "不支持的文件格式"),
        ("building", ["a.jpg"], "2 张图片"),
        ("flood", ["a.jpg", "b.csv"], "混合"),
        ("traffic", [], "至少"),
    ],
)
def test_select_errors(etype, files, msg):
    with pytest.raises(ca.InputError, match=msg):
        ca.select(etype, files)


def test_validate_checks_csv_header(tmp_path):
    p = tmp_path / "x.csv"
    p.write_text("time,level\n12:00,1\n")
    with pytest.raises(ca.InputError, match="water_level_cm"):
        ca.validate("flood", [p])


def test_batch_images_merge(tmp_path):
    files = [sample("fire/drone_normal_01.jpg"), sample("fire/drone_fire_02.jpg")]
    analyzer, r = ca.run("fire", files, tmp_path, "B")
    assert analyzer.meta.name == "FlameNet-Lite"
    assert r.detected and r.metrics["images"] == 2 and r.metrics["positive_images"] == 1
    assert all(d.image == 1 for d in r.detections)
    assert len(r.artifacts) == 2 and "第 2 张" in r.artifacts[0].name
    d = r.to_dict(lambda p: f"/files/{p.name}")
    assert d["artifacts"][0]["url"].startswith("/files/B_2")
