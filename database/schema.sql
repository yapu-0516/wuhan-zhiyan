-- 城市智眼 CityEye 数据库结构（SQLite 方言；与 backend/app/models.py 的 SQLAlchemy ORM 一致）
-- 后端启动时由 ORM 自动建表（Base.metadata.create_all），本文件用于审阅与手工建库。
-- 约定：时间字段为东八区（Asia/Shanghai）本地时间；JSON 列在 SQLite 中以 TEXT 存储。
-- 道路实时路况（speed / tpi / level）由模拟器在内存中维护，不落库；建筑 / 道路几何来自 data/geo/*.geojson。

PRAGMA foreign_keys = ON;

-- 城市事件：火灾 / 交通拥堵 / 建筑异常 / 内涝积水
CREATE TABLE events (
    id            VARCHAR(16)  NOT NULL PRIMARY KEY,  -- 事件编号 E0001
    event_type    VARCHAR(16)  NOT NULL,              -- fire | traffic | building | flood
    name          VARCHAR(128) NOT NULL,
    longitude     FLOAT        NOT NULL,              -- WGS84
    latitude      FLOAT        NOT NULL,
    confidence    FLOAT        NOT NULL,              -- 0~1，算法置信度（人工上报为 1）
    status        VARCHAR(16)  NOT NULL,              -- pending | monitoring | processing | resolved（状态机见 docs/api.md）
    timestamp     DATETIME     NOT NULL,              -- 发现时间
    severity      VARCHAR(16)  NOT NULL,              -- low | medium | high | critical
    source        VARCHAR(16)  NOT NULL,              -- drone | satellite | video | sensor | citizen | ai_task
    district      VARCHAR(32)  NOT NULL,              -- 行政区（最近建筑所属区）
    address       VARCHAR(128) NOT NULL,              -- 由路网 / 具名建筑推算的地址描述
    grid          VARCHAR(16)  NOT NULL,              -- 网格化管理编号 {区前缀}-{行}-{列}
    description   TEXT         NOT NULL,
    building_id   VARCHAR(16),                        -- 关联建筑（data/geo/buildings.geojson 的 id）
    road_id       VARCHAR(16),                        -- 关联道路（data/geo/roads.geojson 的 id）
    task_id       VARCHAR(16),                        -- 生成该事件的 AI 任务（不设外键：任务可被清理）
    evidence_url  VARCHAR(255),                       -- 算法标注证据图 /files/evidence/...
    metrics       JSON         NOT NULL,              -- 算法指标 {name: number | string}
    assignee      VARCHAR(64),                        -- 当前处置单位
    created_at    DATETIME     NOT NULL,              -- 入库时间
    updated_at    DATETIME     NOT NULL
);
CREATE INDEX ix_events_event_type  ON events (event_type);
CREATE INDEX ix_events_status      ON events (status);
CREATE INDEX ix_events_severity    ON events (severity);
CREATE INDEX ix_events_timestamp   ON events (timestamp);
CREATE INDEX ix_events_building_id ON events (building_id);
CREATE INDEX ix_events_road_id     ON events (road_id);

-- 事件处置日志（时间线）
CREATE TABLE event_logs (
    id           INTEGER     NOT NULL PRIMARY KEY,    -- 自增
    event_id     VARCHAR(16) NOT NULL REFERENCES events (id) ON DELETE CASCADE,
    action       VARCHAR(16) NOT NULL,                -- created | status_changed | assigned | comment | ai_detected
    from_status  VARCHAR(16),
    to_status    VARCHAR(16),
    operator     VARCHAR(64) NOT NULL,                -- 值班员 / 系统 / 处置单位 / AI 任务
    note         TEXT        NOT NULL,
    timestamp    DATETIME    NOT NULL
);
CREATE INDEX ix_event_logs_event_id  ON event_logs (event_id);
CREATE INDEX ix_event_logs_timestamp ON event_logs (timestamp);

-- 数据资产目录
CREATE TABLE data_assets (
    id           VARCHAR(16)  NOT NULL PRIMARY KEY,   -- D0001
    name         VARCHAR(128) NOT NULL,
    type         VARCHAR(16)  NOT NULL,               -- 遥感影像 | 无人机影像 | 视频流 | 三维模型 | 传感器数据 | 矢量数据
    time         DATETIME     NOT NULL,               -- 获取时间
    status       VARCHAR(16)  NOT NULL,               -- 已入库 | 处理中 | 采集中 | 待接入
    source       VARCHAR(64)  NOT NULL,
    format       VARCHAR(32)  NOT NULL,
    size_bytes   BIGINT       NOT NULL,
    records      INTEGER      NOT NULL,
    description  TEXT         NOT NULL,
    url          VARCHAR(255),                        -- 预览 / 下载地址（上传文件为 /files/uploads/...）
    created_at   DATETIME     NOT NULL
);
CREATE INDEX ix_data_assets_type ON data_assets (type);
CREATE INDEX ix_data_assets_time ON data_assets (time);

-- AI 分析任务
CREATE TABLE tasks (
    id            VARCHAR(16) NOT NULL PRIMARY KEY,   -- T0001
    type          VARCHAR(16) NOT NULL,               -- fire | traffic | building | flood
    status        VARCHAR(16) NOT NULL,               -- pending | running | done | failed
    origin        VARCHAR(16) NOT NULL,               -- user（示例数据）| upload | demo | seed
    created_at    DATETIME    NOT NULL,
    started_at    DATETIME,
    finished_at   DATETIME,
    progress      INTEGER     NOT NULL,               -- 0~100
    stage         VARCHAR(32) NOT NULL,               -- 排队中 / 加载输入 / 算法推理 / 生成结论 / 完成 / 失败
    file_count    INTEGER     NOT NULL,
    inputs        JSON        NOT NULL,               -- [{name, url}]
    algorithm     JSON        NOT NULL,               -- {name, version, method}
    sample_id     VARCHAR(32),                        -- 使用的示例数据（data/samples/manifest.json）
    longitude     FLOAT,
    latitude      FLOAT,
    create_event  BOOLEAN     NOT NULL,               -- 检出时是否生成事件
    result        JSON,                               -- AnalysisTask.result（含 event_ids）
    error         TEXT
);
CREATE INDEX ix_tasks_type       ON tasks (type);
CREATE INDEX ix_tasks_status     ON tasks (status);
CREATE INDEX ix_tasks_created_at ON tasks (created_at);

-- 建筑沉降监测：位移时序 + SettleWatch 算法评估结果（建筑几何在 GeoJSON 中，按 building_id 关联）
CREATE TABLE settlement_series (
    building_id        VARCHAR(16) NOT NULL PRIMARY KEY,
    series             JSON        NOT NULL,          -- [{date: "yyyy-MM-dd", displacement_mm}]，负值为下沉
    rate_mm_per_month  FLOAT       NOT NULL,          -- 近 30 天 Theil–Sen 速率
    acceleration       FLOAT       NOT NULL,          -- 近 90 天二次拟合加速度（mm/月²）
    cumulative_mm      FLOAT       NOT NULL,
    risk_level         VARCHAR(16) NOT NULL,          -- normal | watch | warning
    analysis           TEXT        NOT NULL,
    updated_at         DATETIME    NOT NULL
);
CREATE INDEX ix_settlement_series_risk_level ON settlement_series (risk_level);

-- 监测数据源（基线配置；实时吞吐由模拟器在内存刷新）
CREATE TABLE sources (
    id              VARCHAR(32) NOT NULL PRIMARY KEY, -- S-DRONE
    name            VARCHAR(64) NOT NULL,
    type            VARCHAR(16) NOT NULL,             -- drone | satellite | video | sensor | other
    icon            VARCHAR(8)  NOT NULL,
    "desc"          TEXT        NOT NULL,
    status          VARCHAR(8)  NOT NULL,             -- 在线 | 采集中 | 离线 | 待接入
    devices_online  INTEGER     NOT NULL,
    devices_total   INTEGER     NOT NULL,
    throughput      FLOAT       NOT NULL,
    unit            VARCHAR(16) NOT NULL,
    coverage        VARCHAR(64) NOT NULL,
    last_active     DATETIME    NOT NULL,
    sort_order      INTEGER     NOT NULL
);

-- 键值元数据（seed_version / seeded_at）
CREATE TABLE app_meta (
    "key"  VARCHAR(32) NOT NULL PRIMARY KEY,
    value  TEXT        NOT NULL
);

-- 城市情景推演：会话、不可变版本与运行时间帧
CREATE TABLE scenario_sessions (
    id                  VARCHAR(24) NOT NULL PRIMARY KEY,
    title               VARCHAR(128) NOT NULL,
    scenario_type       VARCHAR(16),
    state               VARCHAR(16) NOT NULL,
    parameters          JSON        NOT NULL,
    messages            JSON        NOT NULL,
    current_version_id  VARCHAR(24),
    last_comparison     JSON,
    created_at          DATETIME    NOT NULL,
    updated_at          DATETIME    NOT NULL
);

CREATE TABLE scenario_versions (
    id             VARCHAR(24) NOT NULL PRIMARY KEY,
    session_id     VARCHAR(24) NOT NULL REFERENCES scenario_sessions(id) ON DELETE CASCADE,
    version_no     INTEGER     NOT NULL,
    scenario_type  VARCHAR(16) NOT NULL,
    title          VARCHAR(128) NOT NULL,
    parameters     JSON        NOT NULL,
    created_at     DATETIME    NOT NULL
);
CREATE INDEX ix_scenario_versions_session_id ON scenario_versions (session_id);

CREATE TABLE scenario_runs (
    id                   VARCHAR(24) NOT NULL PRIMARY KEY,
    session_id           VARCHAR(24) NOT NULL REFERENCES scenario_sessions(id) ON DELETE CASCADE,
    version_id           VARCHAR(24) NOT NULL REFERENCES scenario_versions(id) ON DELETE CASCADE,
    scenario_type        VARCHAR(16) NOT NULL,
    provider             VARCHAR(32) NOT NULL,
    data_classification  VARCHAR(24) NOT NULL,
    status               VARCHAR(16) NOT NULL,
    payload              JSON        NOT NULL,
    created_at           DATETIME    NOT NULL
);
CREATE INDEX ix_scenario_runs_session_id ON scenario_runs (session_id);
CREATE INDEX ix_scenario_runs_version_id ON scenario_runs (version_id);
