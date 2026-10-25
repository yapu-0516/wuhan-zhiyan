# 数据集目录

本目录用于存放算法训练、验证和真实场景评测所需的数据。运行演示所依赖的
小型合成样本仍位于 `data/samples/`，本目录下的研究数据不参与当前 Demo 的
默认示例列表。

## 目录约定

```text
data/datasets/
├── raw/                    # 原始下载包或原始目录，不提交 Git
│   ├── dfire/
│   ├── rooftop_traffic/
│   ├── visdrone_det/       # 待获取
│   ├── xbd/                # 待获取
│   ├── uav_obb/            # 待获取
│   ├── wusu/
│   └── whu_aerial_video/   # 待取得许可和数据
└── derived/                # 清洗、切片、转换后的派生产物，不提交 Git
```

原始数据包保留下载时的格式，避免在来源、许可和校验信息尚未登记前反复转换。
后续处理结果放入 `derived/`，并在 `manifests/` 中记录来源、划分、标签映射、
校验值和许可状态。

## 当前数据

| 目录 | 数据 | 状态 |
| --- | --- | --- |
| `raw/dfire/D-Fire.zip` | D-Fire 火焰与烟雾数据 | 完整；21,527 张图像及 21,527 份 YOLO 标签 |
| `raw/rooftop_traffic/` | 屋顶/航拍道路车辆数据 | 完整；548 张图像及 548 份 YOLO-OBB 标签，训练 492 / 验证 56 |
| `raw/wusu/` | 武汉大学 WUSU 语义数据 | 不完整；864 份标签中仅 88 组有配套影像，776 张影像缺失，另有 5 张未下载完 |
| `raw/wuhan_buildings/` | 武汉建筑轮廓 GeoJSON | 两版均可用：完整版 128,066 个 Polygon，精简版 37,872 个 Polygon；来源与许可待核验 |
| `raw/3d_tiles/yangtze_river_bridge/` | 长江大桥 3D Tiles | Cesium 3D Tiles 1.0；2 个 B3DM。原始坐标位于北京，当前未接入 Demo；来源与许可待核验 |
| `raw/3d_tiles/yellow_building/` | 黄鹤楼 3D Tiles | Cesium 3D Tiles 1.0；32 个 B3DM、9 个 CMPT，均属于同一栋楼；当前未接入 Demo，来源与许可待核验 |

现有数据尚未接入 `algorithm/cityeye_algo`，也不能用当前合成样本的测试结果
代表真实场景精度。数据选型、来源、许可和取样计划见
`docs/datasets/武汉智眼首批数据集确定方案.docx`。

建筑轮廓的属性字段为 `OBJECTID`、`Floor`、`Shape_Leng` 和 `Shape_Area`；
完整版坐标范围约为经度 `113.979—114.573`、纬度 `30.338—30.864`，覆盖范围
大于当前汉口沿江示范区。两版 GeoJSON 均应保留原始文件，待来源、许可和
去重关系确认后再生成 Cesium 或训练所用的派生数据。

运行 `python data/scripts/build_wuhan_buildings.py` 可将完整版按 Demo 范围
裁剪为 `derived/buildings/wuhan_demo_buildings.geojson`。当前派生结果包含
8,277 栋建筑，生成 `WHB000001` 格式的稳定 ID，并按 `Floor × 3.2 m` 估算高度；
该图层由 `/api/buildings/fine` 提供，与现有 OSM 建筑图层互斥显示。

两套 3D Tiles 当前只作为本地原始资料保留，Demo 不再加载。如后续正式接入，
需要先完成来源与许可核验、坐标校正以及示范区范围确认。
