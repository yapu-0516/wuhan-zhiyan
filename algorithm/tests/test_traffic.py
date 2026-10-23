from datetime import datetime, timedelta

import numpy as np
import pytest

from cityeye_algo.base import InputError
from cityeye_algo.traffic import TrafficSeriesAnalyzer, VehicleOccupancyAnalyzer, network_tpi, speed_to_tpi, tpi_level

from conftest import sample


def test_tpi_mapping_monotonic_and_bands():
    v = np.linspace(0, 60, 61)
    tpi = speed_to_tpi(v, 60)
    assert np.all(np.diff(tpi) <= 0)
    assert tpi[0] == 10 and tpi[-1] == 0
    assert tpi_level(float(speed_to_tpi(55, 60))) == "smooth"
    assert tpi_level(float(speed_to_tpi(42, 60))) == "basic"  # r=0.70
    assert tpi_level(float(speed_to_tpi(33, 60))) == "light"  # r=0.55
    assert tpi_level(float(speed_to_tpi(24, 60))) == "moderate"  # r=0.40
    assert tpi_level(float(speed_to_tpi(12, 60))) == "heavy"  # r=0.20
    assert network_tpi([2, 8], [100, 300]) == pytest.approx(6.5)


def _series(minutes: int, step: int = 5):
    t0 = datetime(2026, 10, 22, 6, 0)
    return [t0 + timedelta(minutes=i * step) for i in range(minutes // step)]


def test_free_flow_series_not_congested(tmp_path, rng):
    times = _series(240)
    speeds = 52 + rng.normal(0, 1.5, len(times))
    r = TrafficSeriesAnalyzer().analyze_series(times, speeds, tmp_path / "c.png", free_flow_kmh=55)
    assert not r.detected and r.confidence == 0
    assert r.metrics["congestion_periods"] == 0
    assert any(p["kind"] == "forecast" for p in r.series)


def test_sustained_jam_detected_with_peak(tmp_path, rng):
    times = _series(300)
    speeds = 50 + rng.normal(0, 1.0, len(times))
    speeds[24:36] = 10 + rng.normal(0, 0.5, 12)  # 08:00-09:00 严重拥堵
    r = TrafficSeriesAnalyzer().analyze_series(times, speeds, tmp_path / "c.png", free_flow_kmh=55)
    assert r.detected and r.level == "heavy"
    assert r.metrics["congestion_periods"] == 1
    assert 50 <= r.metrics["congested_minutes"] <= 75
    assert (tmp_path / "c.png").exists()


def test_short_dip_below_min_duration_ignored(tmp_path, rng):
    times = _series(240)
    speeds = 50 + rng.normal(0, 1.0, len(times))
    speeds[20] = 8  # 单点异常（5 分钟）
    r = TrafficSeriesAnalyzer().analyze_series(times, speeds, None, free_flow_kmh=55)
    assert not r.detected


def test_csv_missing_column(tmp_path):
    p = tmp_path / "bad.csv"
    p.write_text("time,flow\n08:00,10\n08:05,11\n08:10,12\n")
    with pytest.raises(InputError, match="speed"):
        TrafficSeriesAnalyzer().analyze([p], tmp_path, "x")


def test_sample_csv_has_two_peaks(tmp_path):
    r = TrafficSeriesAnalyzer().analyze([sample("traffic/jiefang_ave_speed_24h.csv")], tmp_path, "s")
    assert r.detected and r.metrics["congestion_periods"] == 2
    assert r.metrics["am_peak_time"].startswith("08") and r.metrics["pm_peak_time"].startswith(("17", "18"))


def test_vehicle_occupancy_samples(tmp_path):
    jam = VehicleOccupancyAnalyzer().analyze([sample("traffic/zhongshan_ave_peak.jpg")], tmp_path, "j")
    free = VehicleOccupancyAnalyzer().analyze([sample("traffic/jinghan_ave_offpeak.jpg")], tmp_path, "f")
    assert jam.detected and jam.level in ("moderate", "heavy")
    assert not free.detected and free.level in ("smooth", "basic")
    assert jam.metrics["occupancy"] > 3 * free.metrics["occupancy"]
    assert jam.metrics["vehicles"] > 3 * free.metrics["vehicles"]
