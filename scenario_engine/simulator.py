"""明确的模拟空间分析提供方；不冒充专业预测算法。"""

from __future__ import annotations

import math
import random
from datetime import datetime

from .models import ImpactZone, PeopleState, ScenarioDraft, ScenarioFrame, ScenarioRun

LIMITATION = "模拟推演数据，仅用于界面和流程验证，不代表真实空间分析结果。"


def _time_frames(duration_min: int) -> list[int]:
    points = {0, duration_min}
    points.update(int(duration_min * r) for r in (0.2, 0.4, 0.6, 0.8))
    return sorted(points)


def _zone_polygon(lon: float, lat: float, radius: float, seed: int) -> list[tuple[float, float]]:
    rng = random.Random(seed)
    lon_scale = 111320 * math.cos(math.radians(lat))
    points: list[tuple[float, float]] = []
    for i in range(16):
        angle = math.tau * i / 16
        factor = radius * (0.88 + rng.random() * 0.16)
        points.append(
            (
                lon + math.cos(angle) * factor / lon_scale,
                lat + math.sin(angle) * factor / 110540,
            )
        )
    return points


def _separate_people(
    people: list[tuple[float, float, str]],
    min_distance_m: float = 1.4,
) -> tuple[list[tuple[float, float, str]], int]:
    """一次确定性最小间距修正，避免模拟人物完全重叠。"""
    adjusted = [[lon, lat, state] for lon, lat, state in people]
    collisions = 0
    min_sq = min_distance_m * min_distance_m
    for i in range(len(adjusted)):
        for j in range(i + 1, len(adjusted)):
            lat0 = math.radians(adjusted[i][1])
            dx = (adjusted[j][0] - adjusted[i][0]) * 111320 * math.cos(lat0)
            dy = (adjusted[j][1] - adjusted[i][1]) * 110540
            d2 = dx * dx + dy * dy
            if d2 >= min_sq:
                continue
            collisions += 1
            if d2 < 1e-6:
                angle = ((i * 37 + j * 17) % 360) * math.pi / 180
                ux, uy = math.cos(angle), math.sin(angle)
                distance = min_distance_m / 2
            else:
                distance = (min_distance_m - math.sqrt(d2)) / 2
                ux, uy = dx / math.sqrt(d2), dy / math.sqrt(d2)
            adjusted[i][0] -= ux * distance / (111320 * math.cos(lat0))
            adjusted[i][1] -= uy * distance / 110540
            adjusted[j][0] += ux * distance / (111320 * math.cos(lat0))
            adjusted[j][1] += uy * distance / 110540
    return [(float(lon), float(lat), str(state)) for lon, lat, state in adjusted], collisions


def _evacuation_people(
    lon: float,
    lat: float,
    radius: float,
    count: int,
    duration: int,
    times: list[int],
    response_delay_min: int,
    closed_exit_count: int,
    available_resource_count: int,
    seed: int,
) -> dict[int, tuple[list[PeopleState], dict[str, int | float]]]:
    if count <= 0:
        return {
            minute: (
                [],
                {
                    "people": 0,
                    "evacuated": 0,
                    "queued": 0,
                    "response_delay_min": response_delay_min,
                    "closed_exit_count": closed_exit_count,
                },
            )
            for minute in times
        }

    rng = random.Random(seed)
    lon_scale = 111320 * math.cos(math.radians(lat))
    starts: list[tuple[float, float]] = []
    for _ in range(count):
        angle = rng.random() * math.tau
        distance = math.sqrt(rng.random()) * radius * 0.9
        starts.append(
            (
                lon + math.cos(angle) * distance / lon_scale,
                lat + math.sin(angle) * distance / 110540,
            )
        )
    targets = [
        (
            lon + math.cos(math.tau * i / count) * radius * 1.8 / lon_scale,
            lat + math.sin(math.tau * i / count) * radius * 1.8 / 110540,
        )
        for i in range(count)
    ]
    lanes = max(1, min(10, math.ceil(math.sqrt(count) / 4) - closed_exit_count + available_resource_count // 2))
    capacity_per_min = lanes * 12
    frames: dict[int, tuple[list[PeopleState], dict[str, int | float]]] = {}
    for minute in times:
        raw_people: list[tuple[float, float, str]] = []
        queued = 0
        for i, (start_lon, start_lat) in enumerate(starts):
            depart_min = response_delay_min + i / capacity_per_min
            if minute < depart_min:
                raw_people.append((start_lon, start_lat, "queued"))
                queued += 1
                continue
            safe_lon, safe_lat = targets[i]
            distance_m = math.hypot((safe_lon - start_lon) * lon_scale, (safe_lat - start_lat) * 110540)
            travel_min = distance_m / 1.2 / 60
            progress = max(0.0, min(1.0, (minute - depart_min) / max(0.1, travel_min)))
            lane = (i % lanes) - (lanes - 1) / 2
            lane_offset = lane * 1.5 / 110540
            plon = start_lon + (safe_lon - start_lon) * progress
            plat = start_lat + (safe_lat - start_lat) * progress + lane_offset * math.sin(progress * math.pi)
            raw_people.append((plon, plat, "safe" if progress >= 1 else "moving"))
        separated, collisions = _separate_people(raw_people)
        people = [
            PeopleState(id=f"P{i + 1:04d}", longitude=plon, latitude=plat, state=state)  # type: ignore[arg-type]
            for i, (plon, plat, state) in enumerate(separated)
        ]
        frames[minute] = (
            people,
            {
                "people": count,
                "evacuated": sum(person.state == "safe" for person in people),
                "queued": queued,
                "corridor_lanes": lanes,
                "capacity_per_min": capacity_per_min,
                "collision_adjustments": collisions,
                "response_delay_min": response_delay_min,
                "closed_exit_count": closed_exit_count,
                "available_resource_count": available_resource_count,
                "danger_radius_m": radius,
            },
        )
    return frames


def _ambient_people(lon: float, lat: float, radius: float, count: int, seed: int) -> list[PeopleState]:
    rng = random.Random(seed)
    lon_scale = 111320 * math.cos(math.radians(lat))
    people: list[PeopleState] = []
    for i in range(count):
        angle = rng.random() * math.tau
        distance = math.sqrt(rng.random()) * radius
        people.append(
            PeopleState(
                id=f"P{i + 1:04d}",
                longitude=lon + math.cos(angle) * distance / lon_scale,
                latitude=lat + math.sin(angle) * distance / 110540,
                state="idle",
            )
        )
    return people


class MockScenarioProvider:
    name = "mock"

    def run(self, draft: ScenarioDraft, run_id: str, version_id: str) -> ScenarioRun:
        p = draft.parameters
        lon = float(p.longitude if p.longitude is not None else 114.35)
        lat = float(p.latitude if p.latitude is not None else 30.585)
        duration = p.duration_min or 60
        frames: list[ScenarioFrame] = []

        if draft.scenario_type == "flood":
            peak_depth = min(80.0, (p.rainfall_mm_h or 0) * min(duration, 90) / 140)
            times = _time_frames(duration)
            max_radius = max(60, 80 + peak_depth * 10)
            people_count = min(1000, p.people_count or 300)
            evacuation = _evacuation_people(
                lon,
                lat,
                max_radius,
                people_count,
                duration,
                times,
                p.response_delay_min or 0,
                p.closed_exit_count or 0,
                p.available_resource_count or 0,
                p.variation_seed or 0,
            )
            for minute in times:
                fraction = min(1.0, minute / max(1, duration * 0.7))
                depth = round(peak_depth * min(1.0, fraction * 1.15), 1)
                risk = "critical" if depth >= 40 else "high" if depth >= 27 else "medium" if depth >= 15 else "low"
                frame_people, evacuation_metrics = evacuation[minute]
                frames.append(
                    ScenarioFrame(
                        offset_min=minute,
                        risk_level=risk,
                        zones=[
                            ImpactZone(
                                id="flood-zone",
                                risk_level=risk,
                                longitude=lon,
                                latitude=lat,
                                radius_m=max(60, 80 + depth * 10),
                                polygon=_zone_polygon(lon, lat, max(60, 80 + depth * 10), minute),
                                data_classification="simulated",
                            )
                        ],
                        metrics={
                            "water_depth_cm": depth,
                            "rainfall_mm_h": p.rainfall_mm_h,
                            **evacuation_metrics,
                        },
                        people=frame_people,
                        data_classification="simulated",
                        limitations=[LIMITATION],
                    )
                )
            summary = "模拟展示低洼点积水范围和风险随时间变化。"

        elif draft.scenario_type == "traffic":
            base_tpi = {"light": 4.8, "moderate": 6.8, "severe": 8.8}[p.congestion_level or "moderate"]
            times = _time_frames(duration)
            people = _ambient_people(
                lon,
                lat,
                160 + base_tpi * 20,
                min(500, p.people_count or 120),
                p.variation_seed or 0,
            )
            for minute in times:
                fraction = minute / max(1, duration)
                tpi = round(base_tpi + math.sin(fraction * math.pi) * 0.5, 1)
                risk = "high" if tpi >= 8 else "medium" if tpi >= 6 else "low"
                frames.append(
                    ScenarioFrame(
                        offset_min=minute,
                        risk_level=risk,
                        zones=[
                            ImpactZone(
                                id="traffic-zone",
                                risk_level=risk,
                                longitude=lon,
                                latitude=lat,
                                radius_m=120 + tpi * 20,
                                polygon=_zone_polygon(lon, lat, 120 + tpi * 20, int(tpi * 10)),
                                data_classification="simulated",
                            )
                        ],
                        people=people,
                        metrics={"tpi": tpi, "duration_min": duration},
                        data_classification="simulated",
                        limitations=[LIMITATION, "未执行路网最短路、道路封闭或真实交通流计算。"],
                    )
                )
            summary = "模拟展示拥堵程度和持续时间的阶段变化。"

        elif draft.scenario_type == "fire":
            radius = p.danger_radius_m or {"small": 120, "medium": 240, "large": 420}[p.fire_severity or "medium"]
            times = _time_frames(duration)
            count = min(500, p.people_count or 240)
            evacuation = _evacuation_people(
                lon,
                lat,
                radius,
                count,
                duration,
                times,
                p.response_delay_min or 0,
                p.closed_exit_count or 0,
                p.available_resource_count or 0,
                p.variation_seed or 0,
            )
            for minute in times:
                frame_people, evacuation_metrics = evacuation[minute]
                frames.append(
                    ScenarioFrame(
                        offset_min=minute,
                        risk_level="high",
                        zones=[
                            ImpactZone(
                                id="fire-danger",
                                risk_level="high",
                                longitude=lon,
                                latitude=lat,
                                radius_m=radius,
                                polygon=_zone_polygon(lon, lat, radius, count),
                                data_classification="simulated",
                            )
                        ],
                        metrics=evacuation_metrics,
                        people=frame_people,
                        data_classification="simulated",
                        limitations=[LIMITATION, "疏散路径为直线模拟，未使用专业路网规划。"],
                    )
                )
            summary = "模拟展示危险区、人员位置和疏散进度。"

        else:
            rate = max(0.1, p.settlement_rate_mm_month or 2.0)
            radius = max(30.0, min(500.0, 40 + rate * 25))
            times = _time_frames(duration)
            count = min(500, p.people_count or 120)
            evacuation = _evacuation_people(
                lon,
                lat,
                radius,
                count,
                duration,
                times,
                p.response_delay_min or 0,
                p.closed_exit_count or 0,
                p.available_resource_count or 0,
                p.variation_seed or 0,
            )
            for minute in times:
                frame_people, evacuation_metrics = evacuation[minute]
                risk = "critical" if rate >= 8 else "high" if rate >= 4 else "medium" if rate >= 1 else "low"
                frames.append(
                    ScenarioFrame(
                        offset_min=minute,
                        risk_level=risk,
                        zones=[
                            ImpactZone(
                                id="building-risk-zone",
                                risk_level=risk,
                                longitude=lon,
                                latitude=lat,
                                radius_m=radius,
                                polygon=_zone_polygon(lon, lat, radius, int(rate * 100)),
                                data_classification="simulated",
                            )
                        ],
                        metrics={
                            "settlement_rate_mm_month": rate,
                            "inspection_progress": round(min(1.0, minute / max(1, duration * 0.7)), 2),
                            "affected_building_id": p.affected_building_id,
                            **evacuation_metrics,
                        },
                        people=frame_people,
                        data_classification="simulated",
                        limitations=[LIMITATION, "未执行结构安全鉴定或专业沉降预测。"],
                    )
                )
            summary = "模拟展示建筑异常风险范围、人员位置和警戒核查进度。"

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return ScenarioRun(
            run_id=run_id,
            version_id=version_id,
            scenario_type=draft.scenario_type,
            provider=self.name,
            model_version="demo-1.0",
            data_classification="simulated",
            frames=frames,
            summary=summary,
            assumptions=["时间帧由推演引擎生成", "场景参数来自用户输入"],
            limitations=[LIMITATION],
            generated_at=now,
        )
