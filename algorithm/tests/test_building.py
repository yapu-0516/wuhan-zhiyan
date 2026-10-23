from datetime import date, timedelta

import numpy as np
import pytest

from cityeye_algo.building import ChangeDetector, SettlementAnalyzer, assess_settlement

from conftest import city_background, sample, save

DAYS = [date(2026, 4, 1) + timedelta(days=i) for i in range(180)]
T = np.arange(180.0)


def test_flat_series_is_normal(rng):
    rep = assess_settlement(DAYS, rng.normal(0, 0.2, 180))
    assert rep.risk_level == "normal"
    assert abs(rep.rate_mm_per_month) < 1.0


def test_steady_settlement_is_watch(rng):
    rep = assess_settlement(DAYS, -3.0 / 30.44 * T + rng.normal(0, 0.2, 180))
    assert rep.risk_level == "watch"
    assert rep.rate_mm_per_month == pytest.approx(-3.0, abs=0.6)
    assert "关注阈值" in rep.analysis


def test_accelerating_settlement_is_warning(rng):
    y = -1.0 / 30.44 * T - 0.0009 * np.clip(T - 90, 0, None) ** 2 + rng.normal(0, 0.2, 180)
    rep = assess_settlement(DAYS, y)
    assert rep.risk_level == "warning"
    assert rep.acceleration < -0.5


def test_fast_settlement_is_warning(rng):
    rep = assess_settlement(DAYS, -5.0 / 30.44 * T + rng.normal(0, 0.2, 180))
    assert rep.risk_level == "warning"


def test_outlier_flagged_but_trend_robust(rng):
    y = rng.normal(0, 0.15, 180)
    y[100] = -6.0
    rep = assess_settlement(DAYS, y)
    assert 100 in rep.anomalies
    assert rep.risk_level == "normal"  # Theil–Sen 对单点粗差稳健


def test_settlement_csv(tmp_path):
    r = SettlementAnalyzer().analyze([sample("building/settlement_accelerating.csv")], tmp_path, "s")
    assert r.detected and r.level == "warning"
    assert len(r.series) == 180 and {"t", "v", "trend", "anomaly"} <= set(r.series[0])
    stable = SettlementAnalyzer().analyze([sample("building/settlement_stable.csv")], tmp_path, "t")
    assert not stable.detected and stable.level == "normal"


def test_change_detection_finds_new_structure(rng, tmp_path):
    before = city_background(rng)
    after = before * 1.08 + 6 + rng.normal(0, 3, before.shape)  # 成像亮度差异 + 噪声
    after[300:360, 420:540] = (52, 104, 176)  # 新增蓝色彩钢瓦
    r = ChangeDetector().analyze([save(before, tmp_path / "b.jpg"), save(after, tmp_path / "a.jpg")], tmp_path, "c")
    assert r.detected
    x, y, w, h = r.detections[0].bbox
    assert x <= 480 <= x + w and y <= 330 <= y + h
    assert 0.01 < r.metrics["change_ratio"] < 0.05


def test_change_detection_ignores_illumination(rng, tmp_path):
    before = city_background(rng)
    after = before * 0.9 + 10 + rng.normal(0, 3, before.shape)
    r = ChangeDetector().analyze([save(before, tmp_path / "b.jpg"), save(after, tmp_path / "a.jpg")], tmp_path, "c")
    assert not r.detected and r.metrics["change_ratio"] == 0


def test_change_samples(tmp_path):
    det = ChangeDetector()
    pos = det.analyze([sample("building/change_01_before.jpg"), sample("building/change_01_after.jpg")], tmp_path, "p")
    neg = det.analyze([sample("building/nochange_02_before.jpg"), sample("building/nochange_02_after.jpg")], tmp_path, "n")
    assert pos.detected and pos.metrics["changed_regions"] >= 2
    assert not neg.detected
