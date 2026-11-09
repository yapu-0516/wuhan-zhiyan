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
  "url": null                  // 可下载/预览地址（上传文件有值）
}
```

### `GET /api/data` → `DataItem[]`（按 time 倒序）
### `GET /api/data/stats` → `{ "total": 12, "total_size": "18.6 GB", "by_type": [{ "type": "遥感影像", "count": 3 }] }`
### `POST /api/data/upload`（multipart：`files` 多个，`type` 可选）→ `DataItem[]`

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
| GET | `/api/scenario/sessions/{id}` | 获取消息、参数、版本和最近结果 |
| POST | `/api/scenario/sessions/{id}/messages` | 自然语言更新、运行或比较 |
| POST | `/api/scenario/sessions/{id}/runs` | 直接运行当前完整版本 |
| GET | `/api/scenario/runs/{id}` | 获取推演时间帧 |
| POST | `/api/scenario/sessions/{id}/compare` | 比较两次运行 |
| POST | `/api/scenario/runs/{id}/report` | 生成结构化推演报告 |

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

情景类型：`flood | traffic | fire`。数据性质：
`real | professional_analysis | simulated | llm_inference | unknown`。
