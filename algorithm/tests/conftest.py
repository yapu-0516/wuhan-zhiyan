"""测试公共夹具：把 algorithm/ 加入 sys.path，并提供程序化生成的测试输入。"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

ALGO_DIR = Path(__file__).resolve().parents[1]
REPO = ALGO_DIR.parent
sys.path.insert(0, str(ALGO_DIR))

SAMPLES = REPO / "data" / "samples"


def sample(rel: str) -> Path:
    p = SAMPLES / rel
    if not p.exists():
        pytest.skip(f"示例数据缺失：{rel}（请先运行 data/scripts/generate_samples.py）")
    return p


def city_background(rng: np.random.Generator, h: int = 480, w: int = 720) -> np.ndarray:
    """灰色城市底图：地面 + 若干灰色屋顶矩形 + 噪声。"""
    img = np.full((h, w, 3), 148.0) + rng.normal(0, 4, (h, w, 3))
    for _ in range(14):
        x, y = rng.integers(0, w - 80), rng.integers(0, h - 60)
        bw, bh = rng.integers(40, 120), rng.integers(30, 90)
        img[y : y + bh, x : x + bw] = rng.integers(110, 200) + rng.normal(0, 3, (min(bh, h - y), min(bw, w - x), 3))
    return img


def paint_flame(img: np.ndarray, cx: int, cy: int, r: int, rng: np.random.Generator) -> None:
    """程序化火焰：湍流扰动的径向强度场 + 黄白焰心→橙→红色阶。"""
    h, w = img.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.hypot(xx - cx, (yy - cy) * 1.3) / r
    turb = np.asarray(Image.fromarray(rng.random((h // 8, w // 8)).astype(np.float32), mode="F").resize((w, h), Image.BICUBIC))
    f = 1.0 - d + 0.5 * (turb - 0.5)
    inten = np.clip(f / 0.8, 0, 1)
    stops = np.array([0.0, 0.3, 0.6, 0.85, 1.0])
    cols = np.array([[150, 30, 8], [235, 85, 20], [255, 170, 50], [255, 235, 150], [255, 252, 230]], float)
    flame = np.stack([np.interp(inten, stops, cols[:, k]) for k in range(3)], -1)
    a = np.clip(f * 5, 0, 1)[..., None]
    img[:] = img * (1 - a) + flame * a


def save(img: np.ndarray, path: Path) -> Path:
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(path, quality=90)
    return path


@pytest.fixture
def rng() -> np.random.Generator:
    return np.random.default_rng(7)
