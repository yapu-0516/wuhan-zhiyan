from scenario_engine.compare import compare_runs
from scenario_engine.models import ScenarioDraft, ScenarioParameters, missing_fields
from scenario_engine.simulator import MockScenarioProvider


def test_flood_missing_information() -> None:
    missing = missing_fields("flood", ScenarioParameters(location_name="江汉路"))
    assert missing == ["开始时间", "持续时间", "降雨强度"]


def test_chinese_parameter_values_are_normalized() -> None:
    params = ScenarioParameters(
        congestion_level="严重",
        fire_severity="中型",
        duration_min="30分钟",
        rainfall_mm_h="80毫米/小时",
        danger_radius_m="200米",
        people_count="100人",
    )
    assert params.congestion_level == "severe"
    assert params.fire_severity == "medium"
    assert params.duration_min == 30
    assert params.rainfall_mm_h == 80
    assert params.danger_radius_m == 200
    assert params.people_count == 100


def test_flood_frames_are_marked_simulated() -> None:
    params = ScenarioParameters(
        location_name="江汉路",
        longitude=114.29,
        latitude=30.58,
        start_time="2026-10-31 14:00",
        duration_min=60,
        rainfall_mm_h=80,
    )
    run = MockScenarioProvider().run(
        ScenarioDraft(scenario_type="flood", title="暴雨", parameters=params),
        "SR001",
        "SV001",
    )
    assert len(run.frames) >= 4
    assert run.data_classification == "simulated"
    assert all(frame.data_classification == "simulated" for frame in run.frames)
    assert len(run.frames[0].zones[0].polygon or []) == 16


def test_fire_people_progress_and_compare() -> None:
    base = ScenarioParameters(
        location_name="江汉路",
        longitude=114.29,
        latitude=30.58,
        start_time="2026-10-31 14:00",
        duration_min=30,
        danger_radius_m=200,
        people_count=100,
    )
    provider = MockScenarioProvider()
    left = provider.run(
        ScenarioDraft(scenario_type="fire", title="火灾 A", parameters=base),
        "SR001",
        "SV001",
    )
    changed = base.model_copy(update={"duration_min": 60})
    right = provider.run(
        ScenarioDraft(scenario_type="fire", title="火灾 B", parameters=changed),
        "SR002",
        "SV002",
    )
    assert len(left.frames[-1].people) == 100
    assert left.frames[-1].people[0].state == "safe"
    assert left.frames[0].metrics["queued"] == 99
    assert left.frames[0].metrics["capacity_per_min"]
    comparison = compare_runs(left, right, base, changed)
    assert any(item["field"] == "duration_min" for item in comparison.parameter_changes)


def test_traffic_frames_use_requested_level() -> None:
    params = ScenarioParameters(
        location_name="中山大道",
        longitude=114.2867,
        latitude=30.5837,
        start_time="2026-10-31 17:30",
        duration_min=60,
        congestion_level="severe",
        traffic_cause="交通事故",
    )
    run = MockScenarioProvider().run(
        ScenarioDraft(scenario_type="traffic", title="严重拥堵", parameters=params),
        "SR003",
        "SV003",
    )
    assert run.frames
    assert max(frame.metrics["tpi"] for frame in run.frames) >= 8
    assert run.data_classification == "simulated"


def test_building_frames_use_settlement_rate_and_explicit_limits() -> None:
    params = ScenarioParameters(
        location_name="江汉区",
        longitude=114.271,
        latitude=30.601,
        start_time="2026-11-11 10:00",
        duration_min=60,
        settlement_rate_mm_month=4.5,
        people_count=80,
        available_resource_count=4,
    )
    run = MockScenarioProvider().run(
        ScenarioDraft(scenario_type="building", title="建筑异常", parameters=params),
        "SR004",
        "SV004",
    )
    assert run.frames
    assert run.frames[0].metrics["settlement_rate_mm_month"] == 4.5
    assert run.frames[0].risk_level == "high"
    assert "未执行结构安全鉴定" in "；".join(run.frames[0].limitations)
