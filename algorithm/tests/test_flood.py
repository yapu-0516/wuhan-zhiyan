from datetime import datetime, timedelta

import numpy as np
import pytest

from cityeye_algo.flood import FloodThresholds, WaterLevelAnalyzer, WaterSegmenter

from conftest import sample

TIMES = [datetime(2026, 7, 5, 12, 0) + timedelta(minutes=5 * i) for i in range(60)]


def test_threshold_levels():
    th = FloodThresholds()
    assert [th.level(x) for x in (5, 15, 26.9, 27, 45)] == ["none", "minor", "minor", "moderate", "severe"]


def _storm(rng, scale: float):
    rain = np.zeros(60)
    rain[10:25] = np.hanning(15) * 6 * scale
    level = np.zeros(60)
    for i in range(1, 60):
        level[i] = max(0.0, 0.92 * level[i - 1] + 1.6 * (rain[i - 4] if i >= 4 else 0))
    return rain, level + rng.normal(0, 0.2, 60).clip(0)


def test_rainstorm_detected_with_lag(rng, tmp_path):
    rain, level = _storm(rng, 1.0)
    r = WaterLevelAnalyzer().analyze_series(TIMES, level, tmp_path / "c.png", rain=rain)
    assert r.detected and r.level in ("moderate", "severe")
    assert r.metrics["response_lag_min"] == pytest.approx(20, abs=10)
    assert r.metrics["forecast_model"] == "ARX 降雨-径流模型"
    assert r.series[-1]["kind"] == "forecast"


def test_light_rain_not_detected(rng, tmp_path):
    rain, level = _storm(rng, 0.15)
    r = WaterLevelAnalyzer().analyze_series(TIMES, level, None, rain=rain)
    assert not r.detected and r.level == "none"


def test_rising_series_forecast_without_rain(tmp_path):
    level = np.concatenate([np.zeros(30), np.linspace(0, 14, 30)])  # 快速上涨、尚未超阈值 → 预测越过 15 cm 即预警
    r = WaterLevelAnalyzer().analyze_series(TIMES, level, None)
    assert r.metrics["forecast_model"] == "阻尼 Holt 平滑"
    assert r.metrics["forecast_peak_cm"] > 14
    assert r.detected


def test_csv_samples(tmp_path):
    a = WaterLevelAnalyzer()
    storm = a.analyze([sample("flood/jinghan_ave_rainstorm.csv")], tmp_path, "s")
    light = a.analyze([sample("flood/light_rain_normal.csv")], tmp_path, "l")
    assert storm.detected and storm.metrics["max_level_cm"] >= 27
    assert not light.detected


def test_water_segmentation_samples(tmp_path):
    seg = WaterSegmenter()
    wet = seg.analyze([sample("flood/street_waterlogging.jpg")], tmp_path, "w")
    dry = seg.analyze([sample("flood/street_dry.jpg")], tmp_path, "d")
    assert wet.detected and wet.metrics["water_area_ratio"] > 0.1
    assert not dry.detected and dry.metrics["water_area_ratio"] < 0.04
