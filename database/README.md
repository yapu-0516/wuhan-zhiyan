# 数据库设计

后端使用 SQLAlchemy 2.x ORM（`backend/app/models.py`），默认 SQLite（`backend/var/cityeye.db`，WAL 模式），
可通过环境变量 `CITYEYE_DB_URL` 切换到 PostgreSQL / MySQL。`schema.sql` 是与 ORM 一致的 DDL（SQLite 方言，附字段注释），
应用启动时会自动建表，无需手工执行。

## ER 图

```mermaid
erDiagram
    events ||--o{ event_logs : "处置日志"
    tasks ||--o{ events : "task_id（AI 任务生成）"
    monitoring_tasks ||--o{ monitoring_runs : "业务运行"
    monitoring_runs ||--o{ assessments : "研判来源"
    events ||--o{ assessments : "事件研判"
    events ||--o{ work_orders : "处置工单"
    assessments ||--o{ work_orders : "研判派单"
    settlement_series |o--o{ events : "building_id"
    events {
        string id PK "E0001"
        string event_type "fire/traffic/building/flood"
        string status "pending/monitoring/processing/resolved"
        string severity
        string source
        datetime timestamp "发现时间"
        string building_id "→ buildings.geojson"
        string road_id "→ roads.geojson"
        string task_id "→ tasks.id"
        json metrics
    }
    event_logs {
        int id PK
        string event_id FK
        string action
        string from_status
        string to_status
        string operator
        datetime timestamp
    }
    tasks {
        string id PK "T0001"
        string type
        string status
        int progress
        json inputs
        json algorithm
        json result "含 event_ids"
    }
    monitoring_tasks {
        string id PK "MT0001"
        string event_type
        string schedule_type
        string status
        json rule_config
    }
    monitoring_runs {
        string id PK "MR0001"
        string monitoring_task_id FK
        string analysis_task_id "→ tasks.id"
        json event_ids
        string status
    }
    assessments {
        string id PK "AS0001"
        string event_id FK
        string monitoring_run_id FK
        string decision
        json evidence
    }
    work_orders {
        string id PK "WO0001"
        string event_id FK
        string assessment_id FK
        string status
        json feedback
    }
    settlement_series {
        string building_id PK
        json series "180 天位移"
        float rate_mm_per_month
        string risk_level
    }
    data_assets {
        string id PK "D0001"
        string type
        bigint size_bytes
    }
    sources {
        string id PK "S-DRONE"
        int devices_online
        float throughput
    }
    app_meta {
        string key PK
        string value
    }
```

建筑与道路的几何、属性来自 `data/geo/*.geojson`（OpenStreetMap，ODbL），不入库；`events.building_id / road_id`
与 `settlement_series.building_id` 按文件中的编号关联。编号会在地理数据重新生成时变化，因此种子数据每次都从文件派生，
不写死任何编号。

## 表说明

| 表 | 说明 |
| --- | --- |
| `events` | 城市事件。`status` 按状态机流转（非法流转 API 返回 409）；`metrics` 保存算法指标；`evidence_url` 指向算法标注图 |
| `event_logs` | 事件处置时间线：`created` / `ai_detected` / `status_changed` / `assigned` / `comment`，随事件级联删除 |
| `tasks` | AI 分析任务，`result` 为 docs/api.md §6 的 `AnalysisTask.result`（检测框、指标、产物、时序、生成的事件） |
| `monitoring_tasks` | 业务监测任务；与 AI 分析作业分离 |
| `monitoring_task_templates` | 可复用的任务区域、数据源、周期和责任配置 |
| `task_template_revisions` | 复盘审核后应用的任务规则修订版本 |
| `monitoring_runs` | 业务任务的一次运行，记录覆盖范围、质量、AI 作业和产出事件 |
| `assessments` | 事件研判记录，保存核查结论、证据、影响和缺失信息 |
| `work_orders` | 核查、管控、处置、复测等工单，与事件状态分离 |
| `reviews` | 任务、事件或演练的复盘结果 |
| `settlement_series` | 接入沉降监测的建筑：位移时序 + SettleWatch 算法计算的速率 / 加速度 / 风险等级 |
| `data_assets` | 数据资产目录；除文件信息外还记录空间范围、时相、坐标系、质量、版本和可分析状态 |
| `data_validations` | 数据资源坐标、时相、字段校验历史及结论 |
| `sources` | 监测数据源基线配置，实时吞吐由模拟器在内存中刷新 |
| `app_meta` | 种子版本与生成时间 |
| `operator_accounts` | 演示角色、组织、联系方式和关联网格 |
| `responsibility_grids` | 行政区责任网格、责任单位和风险类型 |
| `emergency_resources` | 应急资源点的能力、容量、可用数量和调度状态 |
| `notifications` | 站内提醒与已读状态 |
| `audit_logs` | 跨模块写操作审计、操作身份以及对象修改前后值 |
| `scenario_sessions` | 多轮情景推演会话、当前参数和消息 |
| `scenario_templates` | 可复用的情景类型、假设和参数模板 |
| `scenario_template_revisions` | 情景模板每次编辑后的不可变完整参数版本 |
| `scenario_resource_reservations` | 情景对具体应急资源的预留和释放记录 |
| `scenario_versions` | 不可变情景参数版本，用于修改前后对比 |
| `scenario_runs` | 推演时间帧、提供方、数据性质和结构化报告 |

道路实时路况（车速 / TPI / 等级）只存在于内存（`services/traffic.py`），通过 `GET /api/roads` 与 WebSocket `traffic.updated` 输出。

旧数据库启动时，`AppContext.create_schema()` 会为 `data_assets` 增量补充画像字段并做保守回填，
为 `audit_logs` 补充修改前后值字段；不重建数据库，也不会删除用户上传记录或历史审计。
上传文件默认标记为 `analysis_status=pending`，需完成校验后再用于分析。

## 种子数据（`backend/app/seed.py`）

首次启动（库中无 `seed_version`）、`CITYEYE_RESET_ON_START=true` 或调用 `POST /api/demo/reset` 时生成，约 8 秒：

1. **数据源 8 个、数据资产 12 条**：OSM 建筑 / 道路 / POI 的条目使用真实文件大小与记录数；没有附带文件的遥感目录条目注明"演示目录条目"。
2. **沉降监测 40 栋**：汉口侧最高的 40 栋建筑，生成 180 天位移序列（多数稳定，少数持续沉降 / 加速沉降，风险剖面优先放在无名建筑上），
   风险等级由 SettleWatch 算法计算。
3. **AI 任务 8 个**：在示例数据上真实运行算法（含 1 个红瓦屋面反例，结论为未检出）。
4. **近 7 天约 50 个事件**：
   - 图片类事件的证据图来自示例影像的真实分析结果；
   - 交通 / 内涝 / 沉降事件由与实时模拟器同一模型生成的历史序列（车速、水位 + 雨量、位移）经 TrafficPulse / AquaLevel / SettleWatch 分析得到，**未检出则不生成事件**；
   - 包含 3 天前一场暴雨引发的多点内涝、每日早晚高峰拥堵、交通事故、市民上报（含 1 起核查为误报的冒烟）；
   - 每个事件的处置时间线（响应、派单、现场反馈、办结）按类型推演到当前时刻截断，因此越久远的事件越可能已办结，日志与状态一致。

随机数固定（`random.Random(42)`），时间相对当前时刻生成，所以演示数据始终是"最近 7 天"。
