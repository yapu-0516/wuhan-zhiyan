"""数据资产接口（docs/api.md §5）。"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import select

from .. import timeutil
from ..context import AppContext, bad_request, get_ctx
from ..models import DataAsset
from ..schemas import DataItemOut, DataStatsOut
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
    }


@router.get("", response_model=list[DataItemOut], summary="数据资产清单（按获取时间倒序）")
def list_data(ctx: AppContext = Depends(get_ctx)) -> list[dict]:
    with ctx.session() as s:
        return [asset_to_dict(a) for a in s.scalars(select(DataAsset).order_by(DataAsset.time.desc(), DataAsset.id.desc()))]


@router.get("/stats", response_model=DataStatsOut, summary="数据资产统计")
def data_stats(ctx: AppContext = Depends(get_ctx)) -> dict:
    with ctx.session() as s:
        rows = s.scalars(select(DataAsset)).all()
    c = Counter(a.type for a in rows)
    types = list(DATA_TYPES) + sorted(t for t in c if t not in DATA_TYPES)
    return {
        "total": len(rows),
        "total_size": human_size(sum(a.size_bytes for a in rows)),
        "by_type": [{"type": t, "count": c.get(t, 0)} for t in types],
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
                    description="通过数据管理页面上传", url=ctx.url_for(path), created_at=now,
                )
                s.add(a)
                s.flush()
                out.append(asset_to_dict(a))
            s.commit()
    return out
