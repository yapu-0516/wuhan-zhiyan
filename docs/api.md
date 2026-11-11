# 城市智眼 API 契约（v1）

> 本文件是前后端的**唯一接口契约**。后端（FastAPI）严格按此实现，前端 `src/types/*` 与 `src/api/*` 严格按此调用。
> 所有 REST 接口统一前缀 `/api`；时间字段统一为东八区本地时间字符串 `yyyy-MM-dd HH:mm:ss`（Asia/Shanghai）；JSON 字段使用 snake_case
>（历史兼容字段 `AnalysisTask.createdAt` 除外）。

---

## 0. 通用约定

| 项 | 约定 |
| --- | --- |
| 错误响应 | HTTP 4xx/5xx + `{"detail": "中文错误信息"}`（FastAPI 默认格式） |
| 列表接口 | 直接返回 JSON 数组（保持与第 3 周前端原型兼容），不包分页信封 |
| 坐标系 | WGS84 经纬度，`longitude` / `latitude` 为十进制度 |
| 静态文件 | 上传文件、算法证据图、示例数据统一挂载在 `/files/**`（非 `/api` 前缀） |
| 实时推送 | WebSocket `ws(s)://<host>/api/ws` |

### 枚举

```ts
type EventType   = 'fire' | 'traffic' | 'building' | 'flood'          // 火灾 / 交通拥堵 / 建筑异常 / 内涝积水
type EventStatus = 'pending' | 'monitoring' | 'processing' | 'resolved' // 待核查 / 监测中 / 处置中 / 已办结
type Severity    = 'low' | 'medium' | 'high' | 'critical'               // Ⅳ一般 / Ⅲ较大 / Ⅱ重大 / Ⅰ特别重大
type EventSource = 'drone' | 'satellite' | 'video' | 'sensor' | 'citizen' | 'ai_task'
type TrafficLevel = 'smooth' | 'basic' | 'light' | 'moderate' | 'heavy' // 畅通/基本畅通/轻度/中度/严重拥堵 (TPI 0-2/2-4/4-6/6-8/8-10)
```

事件状态机（后端校验，非法流转返回 409）：

```
pending ──► monitoring ──► processing ──► resolved
   │             │                          ▲   │
   │             └──────────────────────────┤   │ (reopen)
   └──────────► processing ─────────────────┘   ▼
   └────────────────────────────────────► resolved      resolved ──► processing
```

即：`pending → monitoring | processing | resolved`；`monitoring → processing | resolved`；`processing → resolved`；`resolved → processing`（重新打开）。同状态 PATCH 视为无状态变更（仅更新其他字段/备注）。

---

## 1. 系统

### `GET /api/health`
```json
{ "status": "ok", "time": "2026-10-22 20:00:00" }
```

### `GET /api/system/info`
```json
{
  "name": "城市智眼 CityEye",
  "version": "1.0.0",
  "demo_mode": true,
  "simulator": { "enabled": true, "interval_sec": 45 },
  "database": "sqlite",
  "uptime_sec": 1234,
  "region": { "name": "武汉中心城区", "city": "武汉", "center": [114.3495, 30.5835], "bbox": [114.15, 30.45, 114.55, 30.72] },
  "algorithms": [
    { "type": "fire", "name": "FlameNet-Lite", "method": "YCbCr+HSV 火焰色彩规则 + 形态学 + 连通域分析", "version": "1.0.0" }
  ]
}
```
`region.center` / `bbox` 为 `[lon, lat]` / `[west, south, east, north]`，前端据此设置相机默认视角。

---

## 2. 事件

### `CityEvent`
```jsonc
{
  "id": "E0001",
  "event_type": "fire",
  "name": "江汉路步行街商铺疑似火情",
  "longitude": 114.2921,
  "latitude": 30.5812,
  "confidence": 0.93,                 // 0~1
  "status": "processing",
  "timestamp": "2026-10-22 10:30:00", // 发现时间
  "severity": "high",
  "source": "drone",
  "district": "江汉区",
  "address": "江汉路 · 中山大道交汇处",
  "grid": "JH-03-07",                  // 网格化管理编号
  "description": "无人机巡检影像识别到明火与烟雾，火焰像素占比 3.4%",
  "building_id": "B0123",             // 可空
  "road_id": null,                     // 可空
  "task_id": "T0003",                  // 可空，由 AI 任务生成时填充
  "evidence_url": "/files/evidence/E0001.jpg", // 可空，算法标注后的证据图
  "metrics": { "flame_area_ratio": 0.034, "smoke_score": 0.61 }, // 数值或字符串
  "assignee": "江汉区消防救援大队",     // 可空
  "updated_at": "2026-10-22 10:42:00"
}
```

### `EventLog`
```json
{ "id": 12, "event_id": "E0001", "action": "status_changed", "from_status": "pending", "to_status": "processing",
  "operator": "值班员 张敏", "note": "已派单至江汉区消防救援大队", "timestamp": "2026-10-22 10:35:00" }
```
`action ∈ created | status_changed | assigned | comment | ai_detected`

### `GET /api/events`
查询参数（均可选）：`type`、`status`、`severity`、`q`（名称/地址/编号模糊匹配）、`limit`（默认 500）。
按 `timestamp` 倒序返回 `CityEvent[]`。

### `GET /api/events/{id}` → `CityEvent`（404 不存在）

### `GET /api/events/{id}/logs` → `EventLog[]`（按时间正序）

### `POST /api/events`（人工上报 / 市民上报）
```json
{ "event_type": "flood", "name": "路面积水", "longitude": 114.29, "latitude": 30.58,
  "severity": "medium", "description": "…", "source": "citizen", "confidence": 1.0 }
```
返回创建后的 `CityEvent`（`status=pending`，后端补齐 district/address/grid）。并推送 WS `event.created`。

### `PATCH /api/events/{id}`
```json
{ "status": "processing", "assignee": "江汉区消防救援大队", "operator": "值班员 张敏", "note": "已派单" }
```
所有字段可选。状态变更校验状态机；写 `EventLog`；返回更新后的 `CityEvent`；推送 WS `event.updated`。

---

## 3. 城市三维对象

### `GET /api/buildings` → GeoJSON `FeatureCollection<Polygon>`
```jsonc
{
  "type": "FeatureCollection",
  "features": [{
    "type": "Feature",
    "id": "WHB000007",
    "geometry": { "type": "Polygon", "coordinates": [[[114.29, 30.58], ...]] },
    "properties": {
      "id": "WHB000007", "name": "建筑 WHB000007", "height": 120.0, "levels": 38,
      "height_source": "floor",        // floor | osm | levels | estimated
      "category": "commercial",        // residential | commercial | office | public | industrial | other
      "district": "江汉区", "grid": "JH-34-27",
      "longitude": 114.2921, "latitude": 30.5812, // 质心
      "area_m2": 2310.5,
      "monitored": true,               // 是否接入沉降监测
      "risk_level": "normal"           // normal | watch | warning（由沉降算法得出）
    }
  }]
}
```

### `GET /api/buildings/fine?district=武昌区` → GeoJSON `FeatureCollection<Polygon>`

返回武汉中心城区按行政区拆分的精细建筑图层，七个城区合计 111,943 栋。
属性中的 `id` 使用 `WHB000001` 格式，`height` 按楼层数估算，仅用于可视化；
该接口不替代原始 OSM 建筑接口，也不包含沉降监测关联。

不传 `district` 时保留旧版单文件入口；`GET /api/buildings/fine/districts`
返回各城区名称、中心点、包围盒、建筑数量和推荐加载地址。

### `GET /api/buildings/{id}` → 建筑详情
```jsonc
{
  "properties": { /* 同上 */ },
  "monitoring": {                       // monitored=false 时为 null
    "series": [{ "date": "2026-07-01", "displacement_mm": -1.2 }],
    "rate_mm_per_month": -2.8,
    "acceleration": -0.4,
    "cumulative_mm": -9.6,
    "risk_level": "watch",
    "analysis": "近 30 天沉降速率 2.8 mm/月，超过 2 mm/月 关注阈值"
  },
  "events": [ /* 关联该建筑的 CityEvent[] */ ]
}
```

### `GET /api/roads` → GeoJSON `FeatureCollection<LineString>`
### `GET/PATCH /api/spatial/{entity_type}/{id}`

`entity_type` 为 `building | road`。GET 返回属性和 GeoJSON 几何；PATCH 可提交
`{ "properties": {...}, "geometry": {...} }`，保存后重新加载地图空间索引。
properties：`{ id: "R001", name: "解放大道", highway: "primary", length_m, speed_limit, speed, tpi, level: TrafficLevel }`

### `GET /api/pois` → `[{ id, name, kind: "hospital"|"fire_station"|"police"|"school", longitude, latitude }]`

---

## 4. 统计

### `GET /api/stats/overview`
```jsonc
{
  "total": 42, "active": 17, "today": 9, "resolved_today": 5,
  "resolve_rate": 0.62,                 // 已办结 / 总数
  "avg_response_min": 12.4,             // 创建 → 首次状态变更 平均分钟
  "by_type":     { "fire": 6, "traffic": 18, "building": 7, "flood": 11 },
  "by_status":   { "pending": 5, "monitoring": 4, "processing": 8, "resolved": 25 },
  "by_severity": { "low": 10, "medium": 18, "high": 11, "critical": 3 },
  "by_district": [{ "name": "江汉区", "count": 20 }, { "name": "江岸区", "count": 22 }],
  "trend": [{ "time": "21:00", "fire": 0, "traffic": 2, "building": 0, "flood": 1 }], // 近 24 小时，24 个点，最早在前
  "city_index": {
    "traffic_tpi": 4.6,                 // 全路网长度加权 TPI
    "traffic_level": "light",
    "safety_score": 86,                 // 0~100 城市安全指数
    "sensors_online": 1382, "sensors_total": 1420
  },
  "updated_at": "2026-10-22 20:00:00"
}
```

---

## 5. 数据资产

### `DataItem`
```jsonc
{
  "id": "D0001",
  "name": "汉口沿江示范区遥感影像",
  "type": "遥感影像",          // 遥感影像 | 无人机影像 | 视频流 | 三维模型 | 传感器数据 | 矢量数据
  "time": "2026-10-20 08:00",  // 获取时间 yyyy-MM-dd HH:mm（兼容原型）
  "status": "已入库",          // 已入库 | 处理中 | 采集中 | 待接入
  "source": "高分二号卫星",
  "format": "GeoTIFF",
  "size": "2.4 GB",
  "size_bytes": 2576980378,
  "records": 1,                // 记录/文件数
  "description": "0.8m 全色 + 3.2m 多光谱融合",
  "url": null,                 // 可下载/预览地址（上传文件有值）
  "spatial_extent": { "label": "武汉中心城区", "bbox": [114.15, 30.45, 114.55, 30.72] },
  "time_start": "2026-10-20 00:00",
  "time_end": "2026-10-20 08:00",
  "crs": "EPSG:4326",
  "quality_score": 88.0,       // 0~100，质量检查得分
  "quality_notes": ["空间与时相口径已登记"],
  "version": "2026.10.20",
  "analysis_status": "ready"   // ready | pending | unavailable | unknown
}
```

### `GET /api/data` → `DataItem[]`（按 time 倒序）
可选查询参数：`type`、`status`、`analysis_status`、`q`、`time_from`、`time_to`、
`longitude`、`latitude`、`radius_m`。空间条件按数据资源空间范围与查询圆的扩展边界求交。
### `GET /api/data/stats` → 总数、总容量、类型分布、`analyzable` 与 `by_analysis_status`
### `POST /api/data/upload`（multipart：`files` 多个，`type` 可选）→ `DataItem[]`
### `GET /api/data/{id}/validations` → `DataValidation[]`
### `POST /api/data/{id}/validations`
### `POST /api/data/{id}/auto-check` → 自动预检记录

```json
{
  "decision": "pass",          // pass | needs_repair | reject
  "coordinate_check": true,
  "time_check": true,
  "fields_check": true,
  "notes": ["坐标、时相与字段已核验"],
  "operator": "数据管理员 周宁"
}
```

上传文件默认进入 `analysis_status=pending`，表示已入库但尚未完成坐标、时相与字段校验；
页面不得仅因文件存在就把它标记为可分析。
`decision=pass` 要求三项检查全部通过，并将资源更新为 `ready`；`needs_repair` 保持 `pending`，
`reject` 更新为 `unavailable`。监测任务只能绑定 `ready` 资源，执行前还会再次校验其状态。
自动预检检查本地文件、空间/时相登记、CSV 字段与重复记录，只生成 `needs_repair` 预检记录，
仍需人工确认后才能转为 `ready`。

---

## 6. AI 分析任务

### `AnalysisTask`
```jsonc
{
  "id": "T0001",
  "type": "fire",                       // EventType
  "status": "done",                     // prototype | pending | running | done | failed
  "createdAt": "2026-10-22 10:00:00",   // 兼容原型字段名
  "finished_at": "2026-10-22 10:00:03",
  "progress": 100,                      // 0~100
  "file_count": 1,
  "inputs": [{ "name": "drone_fire_01.jpg", "url": "/files/samples/fire/drone_fire_01.jpg" }],
  "algorithm": { "name": "FlameNet-Lite", "version": "1.0.0", "method": "YCbCr+HSV 火焰色彩规则 + 形态学 + 连通域分析" },
  "location": { "longitude": 114.29, "latitude": 30.58 },   // 可空
  "result": {
    "detected": true,
    "confidence": 0.91,
    "summary": "检测到 2 处火焰区域，最大区域占画面 3.4%，伴随烟雾特征",
    "detections": [{ "label": "flame", "confidence": 0.91, "bbox": [120, 80, 64, 90] }], // bbox=[x,y,w,h] 像素
    "metrics": { "flame_area_ratio": 0.034, "smoke_score": 0.61, "elapsed_ms": 142 },
    "artifacts": [{ "name": "标注结果", "url": "/files/results/T0001_annotated.jpg", "kind": "image" }],
    "series": [ { "t": "08:00", "v": 32.1 } ],   // 时序类分析（交通/沉降/内涝）用于前端绘图，可空
    "event_ids": ["E0042"]                       // 由该任务自动生成的事件
  },
  "error": null
}
```

### `GET /api/tasks` → `AnalysisTask[]`（按创建时间倒序）
### `GET /api/tasks/{id}` → `AnalysisTask`
### `POST /api/tasks`（JSON，兼容原型）
```json
{ "type": "fire", "fileCount": 0, "sample_id": "fire-01", "longitude": 114.29, "latitude": 30.58, "create_event": true }
```
- 指定 `sample_id` 时在示例数据上运行真实算法；
- 未指定 `sample_id` 且无文件时，返回 400。
- 任务异步执行：立即返回 `status=pending` 的任务，随后通过 WS `task.updated` 推送进度，或轮询 `GET /api/tasks/{id}`。

### `POST /api/tasks/upload`（multipart）
字段：`type`（必填）、`files`（1~N 个文件）、`longitude`、`latitude`、`create_event`（默认 true）。
- fire / building：图片（jpg/png）。building 传 **2 张** 图片时执行前后时相变化检测；传 1 个 CSV 时执行沉降时序分析。
- traffic：CSV（列 `time,speed[,flow]`）或图片（路面车辆占有率估计）。
- flood：CSV（列 `time,water_level_cm[,rainfall_mm]`）或图片（积水区域分割）。

### `GET /api/samples?type=fire` → 示例数据
```json
[{ "id": "fire-01", "type": "fire", "name": "无人机巡检 · 商铺明火", "description": "…",
   "kind": "image", "thumbnail_url": "/files/samples/fire/drone_fire_01.jpg",
   "files": ["/files/samples/fire/drone_fire_01.jpg"], "longitude": 114.29, "latitude": 30.58 }]
```

---

## 7. 监测数据源

### `GET /api/sources`
```json
[{ "id": "S-DRONE", "name": "无人机巡检", "type": "drone", "icon": "🚁", "desc": "…",
   "status": "采集中", "devices_online": 6, "devices_total": 8, "throughput": 124, "unit": "帧/分钟",
   "last_active": "2026-10-22 20:00:00", "coverage": "汉口沿江 12.4 km²" }]
```
`status ∈ 在线 | 采集中 | 离线 | 待接入`。

---

## 8. 演示控制（demo_mode=true 时可用）

### `POST /api/demo/scenario`
```json
{ "scenario": "fire" }   // fire | traffic | building | flood | random
```
立即在示例数据上跑一遍对应算法流水线，生成任务和（如检测到）事件，返回 `{ "task_id": "T0009", "event_id": "E0051" }`（`event_id` 可空）。

### `POST /api/demo/reset` → `{ "ok": true }` 重置数据库为初始种子数据。

---

## 9. 大模型与城市治理助手

所有接口都要求服务端已配置 `DEEPSEEK_API_KEY`。密钥未配置、限流或模型服务异常时返回
`503 {"detail": "..."}`；演示或模拟事件的数据性质不得被改写成真实事件。

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/llm/status` | 只检查密钥配置，不调用模型 |
| POST | `/api/llm/parse-task` | 自然语言任务解析为受控 JSON |
| POST | `/api/llm/chat` | 最多 8 轮城市治理问答，可选关联事件 |
| POST | `/api/llm/report` | 基于事件和周边设施生成结构化研判报告 |

治理问答请求：

```json
{
  "event_id": "E0001",
  "messages": [
    { "role": "user", "content": "这起事件目前有哪些未知信息？" },
    { "role": "assistant", "content": "还需要现场核验。" },
    { "role": "user", "content": "下一步应确认什么？" }
  ]
}
```

`event_id` 可省略；当 `messages` 超过 8 条时前端只发送最近 8 条。最后一条消息必须来自
`user`。响应：

```json
{
  "answer": "建议先确认现场情况……",
  "event_id": "E0001",
  "data_type": "示例数据，不代表真实事件"
}
```

关联事件时，后端从事件目录读取事件、任务来源、1 km 内 POI 和 200 m 内道路，
并把保守判定的数据性质与信息缺口一并提供给模型。问答接口不执行工具、不修改事件状态。

---

## 10. WebSocket `/api/ws`

服务端推送 JSON：`{ "type": string, "data": any, "ts": "2026-10-22 20:00:00" }`

| type | data | 说明 |
| --- | --- | --- |
| `hello` | `{ server_time, demo_mode, clients }` | 连接建立 |
| `event.created` | `CityEvent` | 新事件（AI/传感器/人工） |
| `event.updated` | `CityEvent` | 事件状态/指派变更 |
| `task.updated` | `AnalysisTask` | 任务进度/结果 |
| `traffic.updated` | `{ city_tpi, level, roads: [{ id, speed, tpi, level }] }` | 路网实时路况（约 10s 一次） |
| `sensor.tick` | `{ sources: [{ id, throughput, devices_online }] }` | 数据源吞吐刷新 |
| `heartbeat` | `{}` | 每 20s |

客户端可发送 `{"type":"ping"}`，服务端回 `{"type":"pong"}`。

---

## 11. 城市智能情景推演

所有情景结果均包含 `provider` 与 `data_classification`。当前默认提供方为 `mock`，
返回的数据明确标记为 `simulated`。

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/scenario/status` | DeepSeek 与提供方可用性 |
| POST | `/api/scenario/sessions` | 创建多轮情景会话 |
| GET/POST/PATCH/DELETE | `/api/scenario/templates` · `/api/scenario/templates/{id}` | 情景模板查询、保存、编辑和删除 |
| GET | `/api/scenario/templates/{id}/revisions` | 完整参数修订历史 |
| GET | `/api/scenario/sessions/{id}` | 获取消息、参数、版本和最近结果 |
| POST | `/api/scenario/sessions/{id}/messages` | 自然语言更新、运行或比较 |
| POST | `/api/scenario/sessions/{id}/runs` | 直接运行当前完整版本 |
| PUT | `/api/scenario/sessions/{id}/resources` | 选择并预留具体应急资源 |
| GET | `/api/scenario/runs/{id}` | 获取推演时间帧 |
| POST | `/api/scenario/sessions/{id}/compare` | 比较两次运行 |
| POST | `/api/scenario/runs/{id}/report` | 生成结构化推演报告 |
| GET | `/api/scenario/runs/{id}/export` | 导出推演结果 JSON |
| POST | `/api/scenario-runs/{id}/dispatch` | 将选定方案转为同事件下的多张处置工单 |

消息请求：

```json
{ "message": "江汉路在 2026-10-31 15:00 起发生持续60分钟、80毫米/小时的强降雨，请推演内涝影响。" }
```

响应包含：

```json
{
  "session_id": "SCXXXXXXXXXX",
  "scenario_type": "flood",
  "state": "completed",
  "parameters": {},
  "messages": [],
  "run_ids": [],
  "latest_run": {
    "run_id": "SRXXXXXXXXXX",
    "provider": "mock",
    "data_classification": "simulated",
    "frames": []
  },
  "assistant_reply": "……"
}
```

情景类型：`flood | traffic | fire | building`。数据性质：
`real | professional_analysis | simulated | llm_inference | unknown`。

`POST /api/scenario/sessions` 可传 `{ "event_id": "E0016" }`，从现有事件带入位置、时间、
可用资源数量和 `source_event_id`；推演帧包含受影响建筑与道路编号。

---

## 12. 业务闭环

现有事件、AI 任务和情景接口保持兼容；以下资源将事件拆成可追溯的任务、运行、研判、工单和复盘链。

### `MonitoringTask`

```jsonc
{
  "id": "MT0001",
  "name": "强降雨道路积水专项监测",
  "event_type": "flood",
  "schedule_type": "periodic",          // instant | periodic | special | drill
  "status": "completed",                // draft | scheduled | running | completed | failed
  "area_name": "武汉中心城区",
  "bbox": [114.15, 30.45, 114.55, 30.72],
  "data_source_ids": ["S-SAT", "S-IOT-WATER"],
  "rule_config": { "water_level_threshold_cm": 15 },
  "owner": "防汛值班组",
  "notify_targets": ["水务排水中心", "属地街道"],
  "template_key": "flood-road",
  "start_at": "2026-11-07 15:00:00",
  "end_at": "2026-11-07 16:20:00",
  "next_run_at": null,
  "last_run_at": "2026-11-07 16:20:00",
  "created_at": "2026-11-07 15:00:00",
  "updated_at": "2026-11-07 16:20:00"
}
```

### `MonitoringRun`

一次业务运行可关联一个 AI `Task` 和多个事件：

```json
{
  "id": "MR0001",
  "monitoring_task_id": "MT0001",
  "analysis_task_id": "T0003",
  "event_ids": ["E0027"],
  "status": "completed",
  "coverage": { "window_minutes": 120 },
  "quality": { "data_completeness": 0.92 },
  "failure_reason": null,
  "started_at": "2026-11-07 15:00:00",
  "finished_at": "2026-11-07 16:20:00",
  "created_at": "2026-11-07 15:00:00"
}
```

### `Assessment`

```json
{
  "id": "AS0001",
  "event_id": "E0027",
  "monitoring_run_id": "MR0001",
  "decision": "confirmed",              // candidate | needs_review | confirmed | false_alarm
  "summary": "现场水位与监测序列一致。",
  "evidence": [{ "kind": "event", "id": "E0027", "url": null }],
  "impact": { "district": "江汉区", "risk_level": "medium" },
  "missing_information": [],
  "priority": "medium",
  "operator": "值班员 王磊",
  "created_at": "2026-11-07 15:20:00"
}
```

### `WorkOrder`

```json
{
  "id": "WO0001",
  "event_id": "E0027",
  "assessment_id": "AS0001",
  "scenario_run_id": null,
  "title": "积水抽排",
  "unit": "武汉市水务局排水中心",
  "assignee": "武汉市水务局排水中心",
  "status": "verified",
  "priority": "medium",
  "description": "清理雨水口并安排移动泵车。",
  "due_at": null,
  "feedback": [
    {
      "at": "2026-11-07 15:45:00",
      "operator": "现场处置员",
      "action": "field_feedback",
      "note": "积水已降至脚踝以下，雨水口仍有树叶。",
      "location": { "longitude": 114.2712, "latitude": 30.6011 },
      "attachments": [{
        "name": "field.png",
        "url": "/files/uploads/work-orders/WO0001/field.png",
        "size_bytes": 182400
      }]
    },
    { "at": "2026-11-07 16:20:00", "action": "verified", "note": "道路恢复通行" }
  ],
  "sla": {
    "accepted_at": "2026-11-07 15:22:00",
    "started_at": "2026-11-07 15:28:00",
    "completed_at": "2026-11-07 16:08:00",
    "verified_at": "2026-11-07 16:20:00",
    "response_min": 2,
    "execution_min": 40,
    "review_min": 12,
    "elapsed_min": 60,
    "remaining_min": null,
    "overdue": false
  },
  "created_at": "2026-11-07 15:20:00",
  "updated_at": "2026-11-07 16:20:00"
}
```

工单状态：`pending → accepted → in_progress → completed → verified`；`rejected` 可退回执行，`cancelled` 为终止态。

### `ReviewRecord`

```json
{
  "id": "RV0001",
  "entity_type": "event",
  "entity_id": "E0027",
  "status": "confirmed",
  "summary": "发现、核查、处置与复核流程完整。",
  "metrics": { "response_min": 8, "resolve_min": 95 },
  "findings": ["雨水箅子堵塞是主要积水原因"],
  "recommendations": ["降雨前增加重点路段雨水口巡检"],
  "created_at": "2026-11-07 17:00:00",
  "updated_at": "2026-11-07 17:00:00"
}
```

接口：

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET/POST | `/api/monitoring-tasks` | 监测任务列表 / 创建 |
| GET/PATCH | `/api/monitoring-tasks/{id}` | 监测任务详情 / 状态和规则更新 |
| POST | `/api/monitoring-tasks/{id}/execute` | 立即运行任务并创建真实算法作业与运行记录 |
| GET/POST/PATCH/DELETE | `/api/task-templates` · `/api/task-templates/{id}` | 任务模板查询、保存、编辑和删除 |
| GET | `/api/task-templates/{id}/revisions` | 任务模板规则修订历史 |
| GET/POST | `/api/monitoring-runs` | 运行列表 / 登记运行 |
| GET/POST | `/api/assessments` | 研判列表 / 创建研判 |
| GET | `/api/assessments/context?event_id=...&radius_m=300` | 查询周边建筑、道路和设施 |
| POST | `/api/assessments/candidates/merge` | 合并同类型、1 km / 2 小时内的相近告警 |
| GET/POST | `/api/work-orders` | 工单列表 / 创建工单 |
| GET/PATCH | `/api/work-orders/{id}` | 工单详情 / 执行流转和反馈 |
| POST | `/api/work-orders/{id}/feedback` | multipart 提交现场文字、经纬度和 0~5 张 JPG / PNG / WEBP 照片 |
| POST | `/api/work-orders/{id}/feedback/{index}/assess` | 将现场反馈转为待补核研判记录 |
| POST | `/api/work-orders/{id}/resources/use` | 从应急资源库存登记使用并扣减可用数量 |
| GET/POST | `/api/reviews` | 复盘列表 / 创建复盘 |
| GET | `/api/reviews/draft?entity_type=event&entity_id=...` | 自动汇总复盘时间线、指标、发现和建议 |
| GET | `/api/reviews/cases?q=...` | 已确认复盘案例库检索 |
| PATCH | `/api/reviews/{id}` | 审核并更新复盘 |
| GET | `/api/reviews/{id}/export` | 导出 Markdown 复盘报告 |
| POST | `/api/reviews/{id}/apply-template` | 将审核后的规则应用到任务模板并保留修订版本 |

周期任务在 `rule_config.interval_minutes` 中保存执行频率。调度器执行到期的
`schedule_type=periodic`、`status=scheduled` 任务，并在完成后排入下一次运行。

---

## 13. 公共支撑

公共支撑接口用于演示角色、责任网格、站内通知、写操作审计和 SLA 汇总。当前身份由请求头
`X-Operator-Id`（如 `A0003`）选择，用于在操作审计中署名；这不是正式登录或权限认证。

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/support/accounts` | 演示角色与组织目录 |
| GET/PATCH | `/api/support/grids` · `/api/support/grids/{id}` | 责任网格查询与责任单位、人员、联系方式维护 |
| GET/PATCH | `/api/support/emergency-resources` · `/api/support/emergency-resources/{id}` | 应急资源能力、容量、可用状态维护 |
| GET | `/api/support/service-status` | 数据库、模拟器、调度间隔、任务/数据状态和算法版本 |
| PATCH | `/api/support/config` | 更新任务节奏、周期扫描间隔和上传上限（仅当前运行实例） |
| GET | `/api/support/review-stats` | 真实事件、监测任务与演练复盘分类统计 |
| GET | `/api/support/notifications` | 站内通知，可用 `unread_only=true` |
| GET | `/api/support/notifications/unread-count` | 未读提醒数 |
| PATCH | `/api/support/notifications/{id}/read` | 标记单条已读 |
| PATCH | `/api/support/notifications/read-all` | 全部标记已读 |
| GET | `/api/support/audit` | 跨模块写操作审计，可按对象和身份筛选 |
| GET | `/api/support/audit/export` | 导出 UTF-8 BOM CSV 审计台账 |
| GET | `/api/support/sla-summary` | 工单响应、执行、复核、超时汇总 |
| GET | `/api/support/sla-summary/export` | 导出 UTF-8 BOM CSV SLA 报表 |

所有非 GET / HEAD / OPTIONS 的 `/api/**` 写请求会记录方法、路径、身份、角色、响应状态、可识别对象
以及数据库对象的修改前后值；
审计写入失败不会阻断原业务。读取接口不写入审计。

SLA 汇总的 `trend` 字段按工单创建日返回最近 14 个业务日的工单量、超时量、
完成量、平均响应和平均执行分钟。

---

## 14. 业务链路

业务链路接口把数据资源、监测任务、运行记录、分析作业、事件、研判、情景会话、
推演结果、工单和复盘组织为统一有向图。

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/traceability/graph` | 完整关系图；可用 `entity_type`、`entity_id` 定位双向链路 |
| GET | `/api/traceability/export` | 导出包含节点、边和统计信息的完整 JSON |

`limit` 控制页面显示对象数量，默认 240，导出接口最多取 5000。节点包含稳定 `id`、
业务类型、编号、显示名、阶段、状态、时间和摘要；边包含来源、去向与关系标签。
图只表达已存在的业务引用，不推断不存在的数据来源或因果关系。
