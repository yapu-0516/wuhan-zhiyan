"""情景会话编排：LLM 只生成受控动作，数值和帧由情景引擎产生。"""

from __future__ import annotations

import sys
import uuid
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select

from ..context import AppContext, not_found
from ..models import ScenarioRunRecord, ScenarioSession, ScenarioVersion

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from llm_module.scenario_agent import ScenarioAgentError, converse  # noqa: E402
from llm_module.scenario_report import generate_scenario_report  # noqa: E402
from scenario_engine.compare import compare_runs  # noqa: E402
from scenario_engine.models import (  # noqa: E402
    ScenarioComparison,
    ScenarioDraft,
    ScenarioParameters,
    ScenarioRun,
    ScenarioType,
    missing_fields,
)
from scenario_engine.simulator import MockScenarioProvider  # noqa: E402

_TYPE_TITLE = {"flood": "强降水与内涝情景", "traffic": "交通拥堵情景", "fire": "火灾应急情景"}
_CITY_LOCATIONS = {
    "江岸区": (114.309, 30.625),
    "江汉区": (114.271, 30.601),
    "硚口区": (114.216, 30.585),
    "汉阳区": (114.218, 30.553),
    "武昌区": (114.316, 30.553),
    "洪山区": (114.397, 30.506),
    "青山区": (114.405, 30.640),
    "光谷": (114.3975, 30.5068),
    "黄鹤楼": (114.305378, 30.545682),
    "武汉长江大桥": (114.283457, 30.551792),
    "武昌站": (114.3187, 30.5281),
}


def _new_id(prefix: str) -> str:
    return f"{prefix}{uuid.uuid4().hex[:10].upper()}"


def _now() -> datetime:
    return datetime.now()


def _timestamp() -> str:
    return _now().strftime("%Y-%m-%d %H:%M:%S")


def _apply_demo_defaults(
    scenario_type: ScenarioType,
    parameters: ScenarioParameters,
) -> tuple[ScenarioParameters, list[str]]:
    now = _now()
    updates: dict[str, Any] = {}
    assumptions: list[str] = []
    if not parameters.start_time:
        updates["start_time"] = now.strftime("%Y-%m-%d %H:%M")
        assumptions.append("未指定开始时间，采用当前时间")
    if not parameters.duration_min:
        updates["duration_min"] = 60
        assumptions.append("未指定持续时间，采用 60 分钟")
    if not parameters.population_profile:
        if now.weekday() >= 5:
            updates["population_profile"] = "weekend_day" if 8 <= now.hour < 20 else "weekend_night"
        else:
            updates["population_profile"] = "workday"
        assumptions.append("人口分布按当前日期自动选择")
    if parameters.response_delay_min is None:
        updates["response_delay_min"] = 3
        assumptions.append("响应延迟采用演示默认值 3 分钟")
    if parameters.closed_exit_count is None:
        updates["closed_exit_count"] = 0
    if parameters.variation_seed is None:
        raw = f"{scenario_type}:{parameters.location_name}:{now.isoformat()}"
        updates["variation_seed"] = int(hashlib.sha1(raw.encode("utf-8")).hexdigest()[:8], 16) % 2_147_483_648

    if scenario_type == "flood":
        if parameters.rainfall_mm_h is None:
            updates["rainfall_mm_h"] = 50
            assumptions.append("未指定降雨强度，采用中雨 50 mm/h")
        if parameters.people_count is None:
            updates["people_count"] = 300
            assumptions.append("未指定人口规模，采用 300 人演示人口")
    elif scenario_type == "traffic":
        if parameters.congestion_level is None:
            updates["congestion_level"] = "moderate"
            assumptions.append("未指定拥堵程度，采用中度拥堵")
        if not parameters.traffic_cause:
            updates["traffic_cause"] = "待核查"
            assumptions.append("拥堵原因未指定，标记为待核查")
        if parameters.people_count is None:
            updates["people_count"] = 120
    else:
        if parameters.fire_severity is None and parameters.danger_radius_m is None:
            updates["fire_severity"] = "medium"
            updates["danger_radius_m"] = 240
            assumptions.append("未指定火灾规模，采用中型火灾和 240 米演示半径")
        if parameters.people_count is None:
            updates["people_count"] = 240
            assumptions.append("未指定人数，采用 240 人演示人口")
    return parameters.model_copy(update=updates), assumptions


class ScenarioService:
    def __init__(self, ctx: AppContext) -> None:
        self.ctx = ctx
        self.provider = MockScenarioProvider()

    def create_session(self) -> dict[str, Any]:
        now = _now()
        row = ScenarioSession(
            id=_new_id("SC"),
            state="initial",
            parameters={},
            messages=[],
            current_version_id=None,
            last_comparison=None,
            created_at=now,
            updated_at=now,
        )
        with self.ctx.session() as s:
            s.add(row)
            s.commit()
        return self.get_session(row.id)

    def get_row(self, session_id: str) -> ScenarioSession:
        with self.ctx.session() as s:
            row = s.get(ScenarioSession, session_id)
            if row is None:
                raise not_found(f"情景会话 {session_id} 不存在")
            return row

    def get_session(self, session_id: str) -> dict[str, Any]:
        with self.ctx.session() as s:
            row = s.get(ScenarioSession, session_id)
            if row is None:
                raise not_found(f"情景会话 {session_id} 不存在")
            runs = s.scalars(
                select(ScenarioRunRecord)
                .where(ScenarioRunRecord.session_id == session_id)
                .order_by(ScenarioRunRecord.created_at.desc())
            ).all()
            latest = runs[0].payload if runs else None
            variant_runs = [
                row.payload
                for row in runs
                if row.payload.get("variant_label")
            ][:3]
            variant_order = {"常规响应": 0, "不利响应": 1, "提前干预": 2}
            variant_runs.sort(key=lambda item: variant_order.get(item.get("variant_label"), 9))
            return {
                "session_id": row.id,
                "title": row.title,
                "scenario_type": row.scenario_type,
                "state": row.state,
                "parameters": row.parameters,
                "messages": row.messages,
                "current_version_id": row.current_version_id,
                "run_ids": [r.id for r in runs],
                "latest_run": latest,
                "variant_runs": variant_runs,
                "last_comparison": row.last_comparison,
            }

    def message(self, session_id: str, text: str, *, auto_run: bool = False) -> dict[str, Any]:
        row = self.get_row(session_id)
        current_type: ScenarioType | None = row.scenario_type if row.scenario_type in ("flood", "traffic", "fire") else None
        current_params = ScenarioParameters.model_validate(row.parameters or {})
        history = list(row.messages or [])
        with self.ctx.session() as s:
            available_runs = s.scalars(
                select(ScenarioRunRecord.id)
                .where(ScenarioRunRecord.session_id == session_id)
                .order_by(ScenarioRunRecord.created_at.desc())
            ).all()
        decision = converse(
            text,
            history=history,
            current_type=current_type,
            current_parameters=current_params.model_dump(mode="json"),
            available_run_ids=list(available_runs),
        )

        scenario_type = decision.scenario_type or current_type
        patch = decision.parameters.model_dump(exclude_unset=True)
        merged = ScenarioParameters.model_validate(
            {**current_params.model_dump(mode="json"), **patch}
        )
        reply = decision.reply.strip()
        action = decision.action

        resolved_location = None
        if scenario_type and merged.location_name and (merged.longitude is None or merged.latitude is None):
            resolved_location = self._resolve_location(merged.location_name)
            if resolved_location:
                merged = merged.model_copy(update={"longitude": resolved_location[0], "latitude": resolved_location[1]})

        demo_assumptions: list[str] = []
        if auto_run and scenario_type and action != "compare":
            merged, demo_assumptions = _apply_demo_defaults(scenario_type, merged)
            if demo_assumptions:
                reply = f"已完成情景理解。演示模式自动补全：{'；'.join(demo_assumptions)}。".strip()

        missing = missing_fields(scenario_type, merged) if scenario_type else ["情景类型"]
        if merged.location_name and not resolved_location and (merged.longitude is None or merged.latitude is None):
            missing.append("可识别的中心城区地点或经纬度")

        if auto_run and scenario_type and not missing and action != "compare":
            action = "run"
        elif action == "clarify" or (action in ("update", "run") and missing):
            action = "clarify"
            if missing:
                reply = f"{reply}\n\n还需要补充：{'、'.join(dict.fromkeys(missing))}。".strip()

        version_id = row.current_version_id
        title = decision.title or row.title or (_TYPE_TITLE.get(scenario_type or "", "未命名情景"))
        if scenario_type and (patch or row.scenario_type != scenario_type):
            version_id = self._save_version(row, scenario_type, title, merged)
            with self.ctx.session() as s:
                db = s.get(ScenarioSession, session_id)
                assert db is not None
                db.scenario_type = scenario_type
                db.title = title
                db.parameters = merged.model_dump(mode="json")
                db.current_version_id = version_id
                db.state = "ready" if not missing else "clarifying"
                db.updated_at = _now()
                s.commit()

        latest_run = None
        variant_runs: list[dict[str, Any]] = []
        comparison = None
        if action == "run" and scenario_type and version_id and not missing:
            if auto_run:
                variant_runs = self._run_variants(
                    session_id,
                    version_id,
                    scenario_type,
                    title,
                    merged,
                    explicit_fields=set(patch),
                )
                latest_run = next(
                    (item for item in variant_runs if item["variant_label"] == "常规响应"),
                    variant_runs[-1],
                )
                reply = f"{reply}\n\n已生成常规、不利和干预三种可能结果。默认展示：{latest_run['summary']}".strip()
            else:
                latest_run = self._run(session_id, version_id, scenario_type, title, merged)
                reply = f"{reply}\n\n推演完成：{latest_run['summary']}".strip()
        elif action == "compare":
            comparison = self._compare(session_id, decision.compare_run_ids)
            if comparison is None:
                reply = "目前至少需要两个已完成推演才能比较。请先运行两个情景版本。"

        user_message = {"role": "user", "content": text, "timestamp": _timestamp()}
        assistant_message = {"role": "assistant", "content": reply, "timestamp": _timestamp(), "action": action}
        with self.ctx.session() as s:
            db = s.get(ScenarioSession, session_id)
            assert db is not None
            db.messages = [*(db.messages or []), user_message, assistant_message]
            db.updated_at = _now()
            if latest_run:
                db.state = "completed"
            elif comparison:
                db.state = "compared"
                db.last_comparison = comparison
            s.commit()
        result = self.get_session(session_id)
        result["assistant_reply"] = reply
        result["action"] = action
        if latest_run:
            result["latest_run"] = latest_run
        if variant_runs:
            result["variant_runs"] = variant_runs
        if comparison:
            result["last_comparison"] = comparison
        return result

    def run_current(self, session_id: str) -> dict[str, Any]:
        row = self.get_row(session_id)
        if not row.scenario_type or not row.current_version_id:
            raise ScenarioAgentError("当前情景参数尚未准备好")
        params = ScenarioParameters.model_validate(row.parameters or {})
        missing = missing_fields(row.scenario_type, params)
        if missing:
            raise ScenarioAgentError(f"缺少参数：{'、'.join(missing)}")
        run = self._run(session_id, row.current_version_id, row.scenario_type, row.title, params)
        with self.ctx.session() as s:
            db = s.get(ScenarioSession, session_id)
            assert db is not None
            db.state = "completed"
            db.updated_at = _now()
            s.commit()
        return run

    def run_current_variants(self, session_id: str) -> dict[str, Any]:
        row = self.get_row(session_id)
        if not row.scenario_type or not row.current_version_id:
            raise ScenarioAgentError("当前情景参数尚未准备好")
        params = ScenarioParameters.model_validate(row.parameters or {})
        missing = missing_fields(row.scenario_type, params)
        if missing:
            raise ScenarioAgentError(f"缺少参数：{'、'.join(missing)}")
        variants = self._run_variants(
            session_id,
            row.current_version_id,
            row.scenario_type,
            row.title,
            params,
        )
        latest_run = next(
            (item for item in variants if item["variant_label"] == "常规响应"),
            variants[-1],
        )
        with self.ctx.session() as s:
            db = s.get(ScenarioSession, session_id)
            assert db is not None
            db.state = "completed"
            db.updated_at = _now()
            s.commit()
        return {"latest_run": latest_run, "variant_runs": variants}

    def compare(self, session_id: str, left_run_id: str, right_run_id: str) -> dict[str, Any]:
        comparison = self._compare(session_id, [left_run_id, right_run_id], exact=True)
        if comparison is None:
            raise ScenarioAgentError("比较失败：运行结果不存在或不属于该会话")
        with self.ctx.session() as s:
            db = s.get(ScenarioSession, session_id)
            assert db is not None
            db.last_comparison = comparison
            db.state = "compared"
            s.commit()
        return comparison

    def get_run(self, run_id: str) -> dict[str, Any]:
        with self.ctx.session() as s:
            row = s.get(ScenarioRunRecord, run_id)
            if row is None:
                raise not_found(f"推演结果 {run_id} 不存在")
            return row.payload

    def report(self, run_id: str) -> dict[str, Any]:
        with self.ctx.session() as s:
            row = s.get(ScenarioRunRecord, run_id)
            if row is None:
                raise not_found(f"推演结果 {run_id} 不存在")
            version = s.get(ScenarioVersion, row.version_id)
            session = s.get(ScenarioSession, row.session_id)
            if version is None or session is None:
                raise not_found("推演版本或会话不存在")
            payload = {
                "scenario_type": row.scenario_type,
                "data_classification": row.data_classification,
                "provider": row.provider,
                "parameters": version.parameters,
                "frames": [
                    {
                        "offset_min": frame.get("offset_min"),
                        "risk_level": frame.get("risk_level"),
                        "zones": frame.get("zones", []),
                        "metrics": frame.get("metrics", {}),
                        "affected_building_ids": frame.get("affected_building_ids", []),
                        "affected_road_ids": frame.get("affected_road_ids", []),
                        "data_classification": frame.get("data_classification"),
                        "limitations": frame.get("limitations", []),
                    }
                    for frame in row.payload.get("frames", [])
                ],
                "comparison": session.last_comparison,
            }
            result = generate_scenario_report(payload)
            stored = dict(row.payload)
            stored["report"] = result.model_dump(mode="json")
            row.payload = stored
            s.commit()
            return stored["report"]

    def _save_version(
        self,
        session: ScenarioSession,
        scenario_type: ScenarioType,
        title: str,
        params: ScenarioParameters,
    ) -> str:
        with self.ctx.session() as s:
            existing = s.scalars(
                select(ScenarioVersion).where(ScenarioVersion.session_id == session.id)
            ).all()
            version = ScenarioVersion(
                id=_new_id("SV"),
                session_id=session.id,
                version_no=len(existing) + 1,
                scenario_type=scenario_type,
                title=title,
                parameters=params.model_dump(mode="json"),
                created_at=_now(),
            )
            s.add(version)
            s.commit()
            return version.id

    def _run(
        self,
        session_id: str,
        version_id: str,
        scenario_type: ScenarioType,
        title: str,
        params: ScenarioParameters,
        variant_label: str = "默认方案",
    ) -> dict[str, Any]:
        draft = ScenarioDraft(
            scenario_type=scenario_type,
            title=title,
            parameters=params,
            data_classification="simulated",
        )
        run = self.provider.run(draft, _new_id("SR"), version_id).model_copy(
            update={"variant_label": variant_label}
        )
        with self.ctx.session() as s:
            s.add(
                ScenarioRunRecord(
                    id=run.run_id,
                    session_id=session_id,
                    version_id=version_id,
                    scenario_type=scenario_type,
                    provider=run.provider,
                    data_classification=run.data_classification,
                    status=run.status,
                    payload=run.model_dump(mode="json"),
                    created_at=_now(),
                )
            )
            s.commit()
        return run.model_dump(mode="json")

    def _run_variants(
        self,
        session_id: str,
        version_id: str,
        scenario_type: ScenarioType,
        title: str,
        params: ScenarioParameters,
        explicit_fields: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        explicit_fields = explicit_fields or set()
        seed = params.variation_seed or 0
        adverse_updates: dict[str, Any] = {
            "response_delay_min": min(60, (params.response_delay_min or 3) + 3),
            "closed_exit_count": min(4, (params.closed_exit_count or 0) + 1),
            "people_count": min(5000, int((params.people_count or 200) * 1.15)),
            "variation_seed": seed + 1,
        }
        intervention_updates: dict[str, Any] = {
            "response_delay_min": max(0, (params.response_delay_min or 3) - 2),
            "closed_exit_count": max(0, (params.closed_exit_count or 0) - 1),
            "variation_seed": seed + 2,
        }
        if scenario_type == "flood" and "rainfall_mm_h" not in explicit_fields:
            adverse_updates["rainfall_mm_h"] = min(300, (params.rainfall_mm_h or 50) * 1.3)
            intervention_updates["rainfall_mm_h"] = max(0, (params.rainfall_mm_h or 50) * 0.8)
        elif scenario_type == "traffic" and "congestion_level" not in explicit_fields:
            adverse_updates["congestion_level"] = "severe"
            intervention_updates["congestion_level"] = "light"
        elif (
            scenario_type == "fire"
            and "danger_radius_m" not in explicit_fields
            and "fire_severity" not in explicit_fields
        ):
            adverse_updates["danger_radius_m"] = min(3000, (params.danger_radius_m or 240) * 1.2)
            intervention_updates["danger_radius_m"] = max(10, (params.danger_radius_m or 240) * 0.9)
        adverse = params.model_copy(
            update=adverse_updates
        )
        intervention = params.model_copy(
            update=intervention_updates
        )
        runs: dict[str, dict[str, Any]] = {}
        for label, variant in (
            ("不利响应", adverse),
            ("提前干预", intervention),
            ("常规响应", params),
        ):
            result = self._run(session_id, version_id, scenario_type, f"{title} · {label}", variant, label)
            runs[label] = result
        return [runs["常规响应"], runs["不利响应"], runs["提前干预"]]

    def _compare(
        self,
        session_id: str,
        run_ids: list[str],
        *,
        exact: bool = False,
    ) -> dict[str, Any] | None:
        ids = list(dict.fromkeys(run_ids))
        if not exact and len(ids) < 2:
            with self.ctx.session() as s:
                ids = list(
                    s.scalars(
                        select(ScenarioRunRecord.id)
                        .where(ScenarioRunRecord.session_id == session_id)
                        .order_by(ScenarioRunRecord.created_at.desc())
                        .limit(2)
                    ).all()
                )
        if len(ids) < 2:
            return None
        with self.ctx.session() as s:
            rows = s.scalars(
                select(ScenarioRunRecord).where(
                    ScenarioRunRecord.session_id == session_id,
                    ScenarioRunRecord.id.in_(ids[:2]),
                )
            ).all()
            by_id = {r.id: r for r in rows}
            if exact:
                left_row, right_row = by_id.get(ids[0]), by_id.get(ids[1])
            else:
                ordered = sorted(rows, key=lambda row: row.created_at)
                left_row, right_row = ordered[0] if ordered else None, ordered[1] if len(ordered) > 1 else None
            if left_row is None or right_row is None:
                return None
            left_run = ScenarioRun.model_validate(left_row.payload)
            right_run = ScenarioRun.model_validate(right_row.payload)
            left_version = s.get(ScenarioVersion, left_row.version_id)
            right_version = s.get(ScenarioVersion, right_row.version_id)
            if left_version is None or right_version is None:
                return None
            result: ScenarioComparison = compare_runs(
                left_run,
                right_run,
                ScenarioParameters.model_validate(left_version.parameters),
                ScenarioParameters.model_validate(right_version.parameters),
            )
            return result.model_dump(mode="json")

    def _resolve_location(self, name: str) -> tuple[float, float] | None:
        needle = name.strip().lower()
        for key, point in _CITY_LOCATIONS.items():
            if key.lower() in needle:
                return point
        for road in self.ctx.geo.roads:
            if needle in {road.name.lower(), road.base_name.lower()}:
                return self.ctx.geo.point_on_road(road, 0.5)
        for poi in self.ctx.geo.pois:
            if needle in poi["name"].lower():
                return float(poi["longitude"]), float(poi["latitude"])
        for building in self.ctx.geo.buildings.values():
            if needle == str(building.get("name", "")).lower():
                return float(building["longitude"]), float(building["latitude"])
        return None
