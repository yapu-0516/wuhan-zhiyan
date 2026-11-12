"""数据资产查询、上传和校验接口。"""
from __future__ import annotations

import csv
import math
from collections import Counter
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .. import timeutil
from ..context import AppContext, bad_request, get_ctx, not_found
from ..models import DataAsset, DataValidationRecord
from ..schemas import DataItemOut, DataStatsOut, DataValidationCreate, DataValidationDecision, DataValidationOut
from ..services.events import next_id
from ..services.uploads import human_size, save_uploads

router = APIRouter(prefix="/data", tags=["数据资产"])

DATA_TYPES = ("遥感影像", "无人机影像", "视频流", "三维模型", "传感器数据", "矢量数据")
EXT_TYPE = {
    ".tif": "遥感影像", ".tiff": "遥感影像", ".img": "遥感影像",
    ".jpg": "无人机影像", ".jpeg": "无人机影像", ".png": "无人机影像", ".webp": "无人机影像",
    ".mp4": "视频流", ".mov": "视频流", ".avi": "视频流", ".mkv": "视频流", ".flv": "视频流",
    ".glb": "三维模型", ".gltf": "三维模型", ".b3dm": "三维模型", ".obj": "三维模型", ".las": "三维模型", ".laz": "三维模型", ".ply": "三维模型",
    ".csv": "传感器数据", ".json": "传感器数据", ".xlsx": "传感器数据", ".txt": "传感器数据",
    ".geojson": "矢量数据", ".shp": "矢量数据", ".kml": "矢量数据", ".gpkg": "矢量数据", ".zip": "矢量数据",
}


def asset_to_dict(a: DataAsset) -> dict:
    return {
        "id": a.id, "name": a.name, "type": a.type, "time": timeutil.fmt_minute(a.time), "status": a.status,
        "source": a.source, "format": a.format, "size": human_size(a.size_bytes), "size_bytes": a.size_bytes,
        "records": a.records, "description": a.description, "url": a.url,
        "spatial_extent": a.spatial_extent or {},
        "time_start": timeutil.fmt_minute(a.time_start) if a.time_start else None,
        "time_end": timeutil.fmt_minute(a.time_end) if a.time_end else None,
        "crs": a.crs or "EPSG:4326",
        "quality_score": round(float(a.quality_score or 0), 1),
        "quality_notes": a.quality_notes or [],
        "version": a.version or "",
        "analysis_status": a.analysis_status or "unknown",
    }


def validation_to_dict(row: DataValidationRecord) -> dict:
    return {
        "id": row.id,
        "asset_id": row.asset_id,
        "decision": row.decision,
        "checks": row.checks or {},
        "quality_score": round(float(row.quality_score or 0), 1),
        "notes": row.notes or [],
        "operator": row.operator,
        "created_at": timeutil.fmt(row.created_at),
    }


def _validation_state(
    decision: DataValidationDecision, checks: dict[str, bool], *, automatic: bool = False
) -> tuple[str, float]:
    passed = sum(checks.values())
    if automatic:
        return "pending", round(passed / len(checks) * 100, 1)
    if decision == "pass":
        return "ready", 100.0
    if decision == "reject":
        return "unavailable", 0.0
    return "pending", round(55 + passed * 10, 1)


def _default_validation_notes(decision: DataValidationDecision) -> list[str]:
    if decision == "pass":
        return ["坐标、时相与字段校验通过"]
    if decision == "needs_repair":
        return ["校验未通过，仍需修复或补全"]
    return ["校验判定为不可用"]


def _store_validation(
    session: Session,
    asset: DataAsset,
    *,
    decision: DataValidationDecision,
    checks: dict[str, bool],
    analysis_status: str,
    quality_score: float,
    notes: list[str],
    operator: str,
    now: datetime,
) -> DataValidationRecord:
    row = DataValidationRecord(
        id=next_id(session, DataValidationRecord.id, "DV"),
        asset_id=asset.id,
        decision=decision,
        checks=checks,
        quality_score=quality_score,
        notes=notes,
        operator=operator,
        created_at=now,
    )
    session.add(row)
    asset.analysis_status = analysis_status
    asset.quality_score = quality_score
    asset.quality_notes = notes
    return row


@router.get("", response_model=list[DataItemOut], summary="数据资产清单（按获取时间倒序）")
def list_data(
    type: str | None = None,
    status: str | None = None,
    analysis_status: str | None = None,
    q: str | None = None,
    time_from: str | None = None,
    time_to: str | None = None,
    longitude: float | None = Query(default=None, ge=-180, le=180),
    latitude: float | None = Query(default=None, ge=-90, le=90),
    radius_m: float = Query(default=1000, ge=50, le=20000),
    ctx: AppContext = Depends(get_ctx),
) -> list[dict]:
    stmt = select(DataAsset)
    if type:
        stmt = stmt.where(DataAsset.type == type)
    if status:
        stmt = stmt.where(DataAsset.status == status)
    if analysis_status:
        stmt = stmt.where(DataAsset.analysis_status == analysis_status)
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                DataAsset.name.ilike(pattern),
                DataAsset.description.ilike(pattern),
                DataAsset.source.ilike(pattern),
                DataAsset.id.ilike(pattern),
            )
        )
    with ctx.session() as s:
        rows = s.scalars(stmt.order_by(DataAsset.time.desc(), DataAsset.id.desc())).all()
    try:
        from_dt = datetime.fromisoformat(time_from) if time_from else None
        to_dt = datetime.fromisoformat(time_to) if time_to else None
    except ValueError as exc:
        raise bad_request("时间范围格式必须是 ISO 8601") from exc
    if (longitude is None) != (latitude is None):
        raise bad_request("longitude 与 latitude 需同时提供")
    lat_delta = radius_m / 110_540 if longitude is not None else None
    lon_delta = radius_m / max(1.0, 111_320 * math.cos(math.radians(latitude or 0))) if longitude is not None else None

    def matches(row: DataAsset) -> bool:
        if from_dt and row.time_end and row.time_end < from_dt:
            return False
        if to_dt and row.time_start and row.time_start > to_dt:
            return False
        if longitude is not None and latitude is not None:
            bbox = (row.spatial_extent or {}).get("bbox") or []
            if len(bbox) != 4:
                return False
            west, south, east, north = [float(item) for item in bbox]
            if (
                east < longitude - (lon_delta or 0)
                or west > longitude + (lon_delta or 0)
                or north < latitude - (lat_delta or 0)
                or south > latitude + (lat_delta or 0)
            ):
                return False
        return True

    return [asset_to_dict(row) for row in rows if matches(row)]


@router.get("/stats", response_model=DataStatsOut, summary="数据资产统计")
def data_stats(ctx: AppContext = Depends(get_ctx)) -> dict:
    with ctx.session() as s:
        rows = s.scalars(select(DataAsset)).all()
    c = Counter(a.type for a in rows)
    status_counts = Counter(a.analysis_status or "unknown" for a in rows)
    types = list(DATA_TYPES) + sorted(t for t in c if t not in DATA_TYPES)
    statuses = ("ready", "pending", "unavailable", "unknown")
    return {
        "total": len(rows),
        "total_size": human_size(sum(a.size_bytes for a in rows)),
        "by_type": [{"type": t, "count": c.get(t, 0)} for t in types],
        "analyzable": status_counts.get("ready", 0),
        "by_analysis_status": [{"type": s, "count": status_counts.get(s, 0)} for s in statuses],
    }


@router.post("/upload", response_model=list[DataItemOut], summary="上传数据文件并入库")
def upload_data(
    files: list[UploadFile] = File(..., description="1~N 个文件"),
    type: str | None = Form(default=None, description="数据类型，缺省按扩展名识别"),
    ctx: AppContext = Depends(get_ctx),
) -> list[dict]:
    if type and type not in DATA_TYPES:
        raise bad_request(f"不支持的数据类型：{type}（可选 {' / '.join(DATA_TYPES)}）")
    if not files:
        raise bad_request("请至少选择 1 个文件")
    if len(files) > 20:
        raise bad_request("单次最多上传 20 个文件")
    kinds = []
    for f in files:
        suffix = Path(f.filename or "").suffix.lower()
        kind = type or EXT_TYPE.get(suffix)
        if kind is None:
            raise bad_request(f"无法识别文件 {f.filename} 的数据类型，请指定 type 参数")
        kinds.append(kind)
    saved = save_uploads(files, ctx.uploads_dir / "data", int(ctx.settings.max_upload_mb * (1 << 20)))
    now = timeutil.now()
    out = []
    with ctx.session() as s:
        with ctx.id_lock:
            for (original, path, size), kind in zip(saved, kinds):
                a = DataAsset(
                    id=next_id(s, DataAsset.id, "D"), name=original, type=kind, time=now, status="已入库", source="用户上传",
                    format=(path.suffix.lstrip(".").upper() or "未知"), size_bytes=size, records=1,
                    description="通过数据资源页面上传，等待空间、时相与字段校验",
                    url=ctx.url_for(path), spatial_extent={}, time_start=now, time_end=now, crs="待校验",
                    quality_score=0.0, quality_notes=["等待坐标、时相与字段完整性校验"],
                    version="upload-1", analysis_status="pending", created_at=now,
                )
                s.add(a)
                s.flush()
                out.append(asset_to_dict(a))
            s.commit()
    return out


@router.get(
    "/{asset_id}/validations",
    response_model=list[DataValidationOut],
    summary="数据资源校验历史",
)
def list_data_validations(
    asset_id: str, ctx: AppContext = Depends(get_ctx)
) -> list[dict]:
    with ctx.session() as s:
        if s.get(DataAsset, asset_id) is None:
            raise not_found(f"数据资源 {asset_id} 不存在")
        rows = s.scalars(
            select(DataValidationRecord)
            .where(DataValidationRecord.asset_id == asset_id)
            .order_by(DataValidationRecord.created_at.desc(), DataValidationRecord.id.desc())
        ).all()
        return [validation_to_dict(row) for row in rows]


@router.post(
    "/{asset_id}/validations",
    response_model=DataValidationOut,
    status_code=201,
    summary="登记数据资源校验并更新可分析状态",
)
def validate_data_asset(
    asset_id: str,
    body: DataValidationCreate,
    ctx: AppContext = Depends(get_ctx),
) -> dict:
    checks = {
        "coordinate": body.coordinate_check,
        "time": body.time_check,
        "fields": body.fields_check,
    }
    passed = sum(checks.values())
    if body.decision == "pass" and passed != 3:
        raise bad_request("校验通过前必须完成坐标、时相和字段三项检查")
    analysis_status, quality_score = _validation_state(body.decision, checks)
    now = timeutil.now()
    with ctx.session() as s:
        asset = s.get(DataAsset, asset_id)
        if asset is None:
            raise not_found(f"数据资源 {asset_id} 不存在")
        with ctx.id_lock:
            row = _store_validation(
                s,
                asset,
                decision=body.decision,
                checks=checks,
                analysis_status=analysis_status,
                quality_score=quality_score,
                notes=body.notes or _default_validation_notes(body.decision),
                operator=body.operator.strip() or "数据管理员",
                now=now,
            )
            s.commit()
        return validation_to_dict(row)


@router.post(
    "/{asset_id}/auto-check",
    response_model=DataValidationOut,
    status_code=201,
    summary="自动预检数据资源并生成待确认校验记录",
)
def auto_check_data_asset(asset_id: str, ctx: AppContext = Depends(get_ctx)) -> dict:
    with ctx.session() as s:
        asset = s.get(DataAsset, asset_id)
        if asset is None:
            raise not_found(f"数据资源 {asset_id} 不存在")
        path = ctx.path_for(asset.url) if asset.url else None
        bbox = (asset.spatial_extent or {}).get("bbox") or []
        checks = {
            "coordinate": len(bbox) == 4,
            "time": bool(asset.time_start or asset.time_end),
            "fields": path is not None and path.exists() and path.stat().st_size > 0,
        }
        notes: list[str] = []
        if checks["coordinate"]:
            notes.append("已登记空间范围")
        else:
            notes.append("缺少空间范围")
        if checks["time"]:
            notes.append("已登记时相范围")
        else:
            notes.append("缺少时相范围")
        if checks["fields"]:
            notes.append("文件存在且非空")
        else:
            notes.append("当前没有可读取的本地原始文件")
        if path and path.suffix.lower() == ".csv" and path.exists():
            try:
                with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as source:
                    reader = csv.reader(source)
                    header = next(reader, [])
                    rows = list(reader)[:1000]
                normalized = [item.strip().lower() for item in header]
                checks["fields"] = bool(header) and bool(rows)
                checks["coordinate"] = checks["coordinate"] or (
                    any("lon" in item or "经度" in item for item in normalized)
                    and any("lat" in item or "纬度" in item for item in normalized)
                )
                checks["time"] = checks["time"] or any(
                    any(token in item for token in ("time", "date", "时间", "日期"))
                    for item in normalized
                )
                duplicates = len(rows) - len({tuple(row) for row in rows})
                if duplicates:
                    notes.append(f"检测到 {duplicates} 条完全重复记录")
                    checks["fields"] = False
                else:
                    notes.append("未检测到完全重复记录")
            except Exception as exc:  # noqa: BLE001
                checks["fields"] = False
                notes.append(f"CSV 解析失败：{exc}")
        decision: DataValidationDecision = "needs_repair"
        analysis_status, quality_score = _validation_state(decision, checks, automatic=True)
        now = timeutil.now()
        with ctx.id_lock:
            row = _store_validation(
                s,
                asset,
                decision=decision,
                checks=checks,
                analysis_status=analysis_status,
                quality_score=quality_score,
                notes=notes,
                operator="系统自动预检",
                now=now,
            )
            s.commit()
        return validation_to_dict(row)
