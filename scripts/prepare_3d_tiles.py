"""把本地地标压缩包解压到前端静态目录，供 Cesium 3D Tiles 加载。"""
from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "frontend" / "public" / "models" / "3d-tiles"
SOURCES = {
    "yellow-building": ROOT / "data" / "datasets" / "raw" / "3d_tiles" / "yellow_building" / "yellow building.zip",
    "yangtze-bridge": ROOT / "data" / "datasets" / "raw" / "3d_tiles" / "yangtze_river_bridge" / "Yantze River Bridge.zip",
}


def main() -> None:
    for name, archive in SOURCES.items():
        if not archive.exists():
            print(f"跳过 {name}：缺少 {archive}")
            continue
        target = OUTPUT / name
        output_root = OUTPUT.resolve()
        destination = target.resolve()
        if output_root not in destination.parents:
            raise ValueError(f"输出目录越界：{destination}")
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True)
        with zipfile.ZipFile(archive) as zf:
            root = target.resolve()
            for item in zf.infolist():
                destination = (target / item.filename).resolve()
                if root not in destination.parents and destination != root:
                    raise ValueError(f"压缩包包含越界路径：{item.filename}")
                zf.extract(item, target)
        entries = list(target.iterdir())
        if len(entries) == 1 and entries[0].is_dir():
            nested = entries[0]
            for child in list(nested.iterdir()):
                child.rename(target / child.name)
            nested.rmdir()
        size = sum(path.stat().st_size for path in target.rglob("*") if path.is_file())
        print(f"{name}: {size / 1024 / 1024:.1f} MB → {target}")


if __name__ == "__main__":
    main()
