# CityEye 项目交接说明

## 1. 接手后先做什么

1. 安装 Python 3.10+、Node.js 18+、npm。
2. 创建虚拟环境并安装后端依赖：

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
   ```

3. 安装前端依赖并解压地标模型：

   ```powershell
   Set-Location frontend
   npm ci
   Set-Location ..
   python scripts/prepare_3d_tiles.py
   ```

4. 若要使用真实大模型问答，将 `llm_module/.env.example` 复制为
   `llm_module/.env`，填写自己的 `DEEPSEEK_API_KEY`。不要提交 `.env`。
5. 启动演示：

   ```powershell
   .\start-demo.ps1 -Rebuild
   ```

   或使用 Docker：

   ```bash
   docker compose up --build
   ```

首次启动可设置 `CITYEYE_RESET_ON_START=true`，让系统重新生成种子事件。

## 2. 已纳入云端的关键数据

| 数据 | 路径 | 用途 |
| --- | --- | --- |
| 七城区精细建筑 | `data/datasets/derived/buildings/districts/` | 页面底部按区切换精细模型 |
| 完整建筑楼层源数据 | `data/datasets/raw/wuhan_buildings/wh_building.json` | 重新生成概览与精细图层 |
| 黄鹤楼 3D Tiles 压缩包 | `data/datasets/raw/3d_tiles/yellow_building/` | 解压后生成黄鹤楼模型 |
| 长江大桥 3D Tiles 压缩包 | `data/datasets/raw/3d_tiles/yangtze_river_bridge/` | 解压后生成大桥模型 |
| OSM 抓取缓存 | `data/raw/osm/` | 无网络时重建道路与行政区域数据 |
| 全市概览与资源 | `data/geo/` | 建筑、道路、224 处应急资源 |
| 全城离线底图 | `frontend/public/basemap/wuhan-city-z13.jpg` | 在线卫星失败后的全城概览 |
| 离线快照 | `frontend/public/snapshot/` | GitHub Pages/无后端演示 |

不要把 `data/datasets/raw` 整个目录直接提交。这里还包含约 2.9 GB 且与
CityEye 运行无关的 D-Fire 数据。

## 3. 数据再生成顺序

```powershell
python data/scripts/fetch_osm.py --out data/raw/osm --bbox 114.15,30.45,114.55,30.72 --tile 0.08 --skip-buildings --skip-water
python data/scripts/build_geo.py --raw data/raw/osm --out data/geo --bbox 114.15 30.45 114.55 30.72 --skip-buildings
python data/scripts/build_wuhan_buildings.py
python data/scripts/fetch_city_pois.py
python scripts/prepare_3d_tiles.py
```

Nominatim 有公共频率限制，补 POI 时脚本会按请求间隔执行。公开部署前请再次
核实地标模型的来源和再分发许可；如果许可不明确，仓库应保持私有。

## 4. 当前功能边界

- 默认入口是武汉中心城区平静基线，点击“一键演示”后运行随机异常、派单、
  AI 问答、情景推演、AI 分析和多城区异常监测。
- 建筑概览 17,458 栋，七城区精细建筑合计 111,943 栋。
- 随机事件覆盖江岸、江汉、硚口、汉阳、武昌、洪山、青山。
- 黄鹤楼模型按需加载，首次点击“黄鹤楼”时需等待约 269 MB 本地模型读取；
  长江大桥压缩包约 2.2 MB。
- 道路来自已缓存的 OSM 中心城区数据，应急资源来自 OSM/Nominatim。
- 人口、路况、传感器和异常发现是演示模拟；算法检出与事件生成链路可继续替换为
  真实数据源。

## 5. 验证

```powershell
.\.venv\Scripts\python.exe -m pytest -q
Set-Location frontend
npm run lint
npm run test -- --run
npm run build
```

完整构建后访问 `http://127.0.0.1:8000`。静态模式由
`.github/workflows/pages.yml` 自动构建，七城区模型会随构建产物发布。

## 6. 不应提交的内容

- `llm_module/.env` 或任何 API Key
- `backend/var/` 中的数据库、上传文件、证据图
- `node_modules/`、`.venv/`、`frontend/dist/`
- `frontend/public/models/3d-tiles/` 解压目录，可由压缩包重新生成
- 无关的 D-Fire 原始数据、日志和本地缓存
