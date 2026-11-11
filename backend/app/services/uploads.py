"""上传文件落盘：安全文件名、大小限制、失败回滚。"""
from __future__ import annotations

import mimetypes
import re
import uuid
from pathlib import Path

from fastapi import UploadFile

from ..context import bad_request

_SAFE = re.compile(r"[^\w一-鿿.\-]+")
CHUNK = 1 << 20
ATTACHMENT_SUFFIXES = {
    ".jpg": "image",
    ".jpeg": "image",
    ".png": "image",
    ".webp": "image",
    ".gif": "image",
    ".mp4": "video",
    ".webm": "video",
    ".mov": "video",
    ".m4v": "video",
    ".mp3": "audio",
    ".wav": "audio",
    ".ogg": "audio",
    ".m4a": "audio",
    ".aac": "audio",
    ".flac": "audio",
    ".pdf": "document",
    ".txt": "document",
    ".csv": "document",
    ".json": "document",
    ".doc": "document",
    ".docx": "document",
    ".xls": "document",
    ".xlsx": "document",
    ".ppt": "document",
    ".pptx": "document",
    ".zip": "archive",
    ".7z": "archive",
    ".rar": "archive",
}


def safe_name(name: str) -> str:
    base = Path(name or "file").name
    stem, suffix = Path(base).stem, Path(base).suffix.lower()
    stem = _SAFE.sub("_", stem).strip("._") or "file"
    return f"{uuid.uuid4().hex[:8]}_{stem[:60]}{suffix}"


def attachment_metadata(name: str) -> dict[str, str]:
    """按白名单后缀分类附件，不信任客户端 MIME 声明。"""
    suffix = Path(name).suffix.lower()
    return {
        "kind": ATTACHMENT_SUFFIXES.get(suffix, "other"),
        "mime_type": mimetypes.guess_type(name)[0] or "application/octet-stream",
    }


def save_uploads(
    files: list[UploadFile],
    dest: Path,
    max_bytes: int,
    max_total_bytes: int | None = None,
) -> list[tuple[str, Path, int]]:
    """保存上传文件，返回 [(原始文件名, 磁盘路径, 字节数)]；任一文件超限、总量超限或为空则整体回滚。"""
    dest.mkdir(parents=True, exist_ok=True)
    saved: list[tuple[str, Path, int]] = []
    total_bytes = 0
    try:
        for f in files:
            original = Path(f.filename or "file").name
            path = dest / safe_name(original)
            size = 0
            with open(path, "wb") as out:
                while chunk := f.file.read(CHUNK):
                    size += len(chunk)
                    total_bytes += len(chunk)
                    if size > max_bytes:
                        out.close()
                        path.unlink(missing_ok=True)
                        raise bad_request(f"文件 {original} 超过大小限制（{max_bytes // (1 << 20)} MB）")
                    if max_total_bytes is not None and total_bytes > max_total_bytes:
                        out.close()
                        path.unlink(missing_ok=True)
                        raise bad_request(
                            f"本次附件总大小超过限制（{max_total_bytes // (1 << 20)} MB）"
                        )
                    out.write(chunk)
            if size == 0:
                path.unlink(missing_ok=True)
                raise bad_request(f"文件 {original} 为空")
            saved.append((original, path, size))
    except Exception:
        remove(p for _, p, _ in saved)
        raise
    return saved


def remove(paths) -> None:  # noqa: ANN001 - 任意可迭代路径
    for p in paths:
        Path(p).unlink(missing_ok=True)


def human_size(n: float) -> str:
    """字节数 → 可读大小，如 2.4 GB。"""
    units = ("B", "KB", "MB", "GB", "TB")
    i = 0
    while n >= 1024 and i < len(units) - 1:
        n /= 1024
        i += 1
    return f"{n:.0f} {units[i]}" if i == 0 else f"{n:.1f} {units[i]}"
