import numpy as np

from cityeye_algo import imgproc as ip


def _flood_fill_count(mask: np.ndarray) -> int:
    """朴素 8 邻域 DFS 计数，作为连通域标记的参照实现。"""
    seen = np.zeros_like(mask, bool)
    h, w = mask.shape
    n = 0
    for y in range(h):
        for x in range(w):
            if mask[y, x] and not seen[y, x]:
                n += 1
                stack = [(y, x)]
                seen[y, x] = True
                while stack:
                    cy, cx = stack.pop()
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            ny, nx = cy + dy, cx + dx
                            if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                                seen[ny, nx] = True
                                stack.append((ny, nx))
    return n


def test_label_components_matches_reference(rng):
    for density in (0.2, 0.45, 0.6):
        m = rng.random((40, 50)) < density
        labels, regions = ip.label_components(m)
        assert len(regions) == _flood_fill_count(m)
        assert sum(r.area for r in regions) == int(m.sum())
        assert ((labels > 0) == m).all()


def test_label_components_bbox_and_min_area():
    m = np.zeros((20, 30), bool)
    m[2:6, 3:10] = True  # 28 px
    m[15, 25] = True  # 1 px
    labels, regions = ip.label_components(m, min_area=2)
    assert len(regions) == 1
    assert regions[0].bbox == (3, 2, 7, 4)
    assert regions[0].area == 28
    assert labels[15, 25] == 0


def test_box_sum_matches_naive(rng):
    a = rng.random((17, 23))
    k = 5
    p = np.pad(a, 2)
    naive = np.array([[p[y : y + k, x : x + k].sum() for x in range(23)] for y in range(17)])
    assert np.allclose(ip.box_sum(a, k), naive)


def test_otsu_separates_bimodal(rng):
    v = np.concatenate([rng.normal(50, 5, 1000), rng.normal(200, 5, 1000)])
    t = ip.otsu_threshold(v)
    assert 70 < t < 180


def test_morphology_removes_speckle_and_fills_holes():
    m = np.zeros((30, 30), bool)
    m[5:25, 5:25] = True
    m[14, 14] = False  # 孔洞
    m[1, 1] = True  # 噪点
    assert not ip.opening(m, 3)[1, 1]
    assert ip.closing(m, 3)[14, 14]


def test_color_spaces():
    rgb = np.array([[[255, 0, 0], [0, 0, 255], [128, 128, 128]]], np.float32)
    y, cb, cr = ip.rgb_to_ycbcr(rgb)
    assert cr[0, 0] > cb[0, 0] and cb[0, 1] > cr[0, 1]
    h, s, v = ip.rgb_to_hsv(rgb)
    assert abs(h[0, 0]) < 1e-3 and abs(h[0, 1] - 240) < 1e-3 and s[0, 2] == 0
