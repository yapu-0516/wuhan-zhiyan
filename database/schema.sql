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
    spatial_extent JSON       NOT NULL,               -- {label, bbox}
    time_start   DATETIME,                            -- 数据覆盖起始时间
    time_end     DATETIME,                            -- 数据覆盖结束时间；实时流为空
    crs          VARCHAR(32)  NOT NULL,               -- 坐标参考系
    quality_score FLOAT       NOT NULL,               -- 0~100，质量检查覆盖得分
    quality_notes JSON        NOT NULL,               -- 质量说明与已知限制
    version      VARCHAR(32)  NOT NULL,               -- 数据版本
    analysis_status VARCHAR(16) NOT NULL,             -- ready | pending | unavailable | unknown
    created_at   DATETIME     NOT NULL
);
CREATE INDEX ix_data_assets_type ON data_assets (type);
CREATE INDEX ix_data_assets_time ON data_assets (time);
CREATE INDEX ix_data_assets_analysis_status ON data_assets (analysis_status);

-- 数据资源坐标、时相与字段校验历史
CREATE TABLE data_validations (
    id             VARCHAR(16) NOT NULL PRIMARY KEY,
    asset_id       VARCHAR(16) NOT NULL REFERENCES data_assets(id) ON DELETE CASCADE,
    decision       VARCHAR(16) NOT NULL,               -- pass | needs_repair | reject
    checks         JSON        NOT NULL,               -- {coordinate,time,fields}
    quality_score  FLOAT       NOT NULL,
    notes          JSON        NOT NULL,
    operator       VARCHAR(64) NOT NULL,
    created_at     DATETIME    NOT NULL
);
CREATE INDEX ix_data_validations_asset ON data_validations (asset_id);
CREATE INDEX ix_data_validations_decision ON data_validations (decision);

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

-- 业务监测任务：业务目标与执行配置（区别于 AI 分析作业 tasks）
CREATE TABLE monitoring_tasks (
    id                VARCHAR(16)  NOT NULL PRIMARY KEY,
    name              VARCHAR(128) NOT NULL,
    event_type        VARCHAR(16)  NOT NULL,
    schedule_type     VARCHAR(16)  NOT NULL,          -- instant | periodic | special | drill
    status            VARCHAR(16)  NOT NULL,          -- draft | scheduled | running | completed | failed
    area_name         VARCHAR(64)  NOT NULL,
    bbox              JSON         NOT NULL,
    data_source_ids   JSON         NOT NULL,
    rule_config       JSON         NOT NULL,
    owner             VARCHAR(64)  NOT NULL,
    notify_targets    JSON         NOT NULL,
    template_key      VARCHAR(32),
    start_at          DATETIME,
    end_at            DATETIME,
    next_run_at       DATETIME,
    last_run_at       DATETIME,
    created_at        DATETIME     NOT NULL,
    updated_at        DATETIME     NOT NULL
);
CREATE INDEX ix_monitoring_tasks_event_type ON monitoring_tasks (event_type);
CREATE INDEX ix_monitoring_tasks_status ON monitoring_tasks (status);

-- 可复用的监测任务模板
CREATE TABLE monitoring_task_templates (
    id                VARCHAR(16)  NOT NULL PRIMARY KEY,
    name              VARCHAR(128) NOT NULL,
    description       TEXT         NOT NULL,
    event_type        VARCHAR(16)  NOT NULL,
    schedule_type     VARCHAR(16)  NOT NULL,
    area_name         VARCHAR(64)  NOT NULL,
    bbox              JSON         NOT NULL,
    data_source_ids   JSON         NOT NULL,
    rule_config       JSON         NOT NULL,
    owner             VARCHAR(64)  NOT NULL,
    notify_targets    JSON         NOT NULL,
    created_at        DATETIME     NOT NULL,
    updated_at        DATETIME     NOT NULL
);
CREATE INDEX ix_monitoring_task_templates_type ON monitoring_task_templates (event_type);

CREATE TABLE task_template_revisions (
    id                INTEGER     NOT NULL PRIMARY KEY,
    template_id       VARCHAR(16) NOT NULL REFERENCES monitoring_task_templates(id) ON DELETE CASCADE,
    version_no        INTEGER     NOT NULL,
    rule_config       JSON        NOT NULL,
    source_review_id  VARCHAR(16),
    operator          VARCHAR(64) NOT NULL,
    created_at        DATETIME    NOT NULL
);
CREATE INDEX ix_task_template_revisions_template ON task_template_revisions (template_id);
CREATE INDEX ix_task_template_revisions_review ON task_template_revisions (source_review_id);

-- 业务任务的一次运行，记录覆盖、质量、AI 作业与产出的多个事件
CREATE TABLE monitoring_runs (
    id                  VARCHAR(16) NOT NULL PRIMARY KEY,
    monitoring_task_id  VARCHAR(16) NOT NULL REFERENCES monitoring_tasks(id) ON DELETE CASCADE,
    analysis_task_id    VARCHAR(16),
    event_ids           JSON        NOT NULL,
    status              VARCHAR(16) NOT NULL,         -- pending | running | completed | failed
    coverage            JSON        NOT NULL,
    quality             JSON        NOT NULL,
    failure_reason      TEXT,
    started_at          DATETIME,
    finished_at         DATETIME,
    created_at          DATETIME    NOT NULL
);
CREATE INDEX ix_monitoring_runs_task ON monitoring_runs (monitoring_task_id);
CREATE INDEX ix_monitoring_runs_analysis ON monitoring_runs (analysis_task_id);

-- 事件研判记录：事件是风险对象，研判记录保存每一轮证据和结论
CREATE TABLE assessments (
    id                    VARCHAR(16) NOT NULL PRIMARY KEY,
    event_id              VARCHAR(16) NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    monitoring_run_id     VARCHAR(16) REFERENCES monitoring_runs(id) ON DELETE SET NULL,
    decision              VARCHAR(20) NOT NULL,       -- candidate | needs_review | confirmed | false_alarm
    summary               TEXT        NOT NULL,
    evidence              JSON        NOT NULL,
    impact                JSON        NOT NULL,
    missing_information   JSON        NOT NULL,
    priority              VARCHAR(16) NOT NULL,
    operator              VARCHAR(64) NOT NULL,
    created_at            DATETIME    NOT NULL
);
CREATE INDEX ix_assessments_event ON assessments (event_id);
CREATE INDEX ix_assessments_decision ON assessments (decision);

-- 处置工单：一个事件可拆为核查、管控、处置、复测等多个工单
CREATE TABLE work_orders (
    id                VARCHAR(16) NOT NULL PRIMARY KEY,
    event_id          VARCHAR(16) NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    assessment_id     VARCHAR(16) REFERENCES assessments(id) ON DELETE SET NULL,
    scenario_run_id   VARCHAR(24),
    title             VARCHAR(128) NOT NULL,
    unit              VARCHAR(64) NOT NULL,
    assignee          VARCHAR(64) NOT NULL,
    status            VARCHAR(16) NOT NULL,           -- pending | accepted | in_progress | completed | verified | rejected | cancelled
    priority          VARCHAR(16) NOT NULL,
    description       TEXT        NOT NULL,
    due_at            DATETIME,
    feedback          JSON        NOT NULL,
    created_at        DATETIME    NOT NULL,
    updated_at        DATETIME    NOT NULL
);
CREATE INDEX ix_work_orders_event ON work_orders (event_id);
CREATE INDEX ix_work_orders_status ON work_orders (status);

-- 任务/事件/演练复盘
CREATE TABLE reviews (
    id                VARCHAR(16) NOT NULL PRIMARY KEY,
    entity_type       VARCHAR(20) NOT NULL,           -- event | monitoring_task | drill
    entity_id         VARCHAR(32) NOT NULL,
    status            VARCHAR(16) NOT NULL,           -- draft | confirmed
    summary           TEXT        NOT NULL,
    metrics           JSON        NOT NULL,
    findings          JSON        NOT NULL,
    recommendations   JSON        NOT NULL,
    created_at        DATETIME    NOT NULL,
    updated_at        DATETIME    NOT NULL
);
CREATE INDEX ix_reviews_entity ON reviews (entity_type, entity_id);

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

-- 演示操作身份：用于署名和角色提示，不替代正式认证
CREATE TABLE operator_accounts (
    id              VARCHAR(16) NOT NULL PRIMARY KEY,
    name            VARCHAR(64) NOT NULL,
    role            VARCHAR(24) NOT NULL,             -- duty | analyst | dispatcher | field | data_admin | admin
    organization    VARCHAR(96) NOT NULL,
    grid_ids        JSON        NOT NULL,
    status          VARCHAR(16) NOT NULL,
    contact         VARCHAR(64) NOT NULL,
    created_at      DATETIME    NOT NULL,
    updated_at      DATETIME    NOT NULL
);
CREATE INDEX ix_operator_accounts_role ON operator_accounts (role);

-- 行政区责任网格与属地责任单位
CREATE TABLE responsibility_grids (
    id             VARCHAR(24) NOT NULL PRIMARY KEY,
    district       VARCHAR(32) NOT NULL,
    name           VARCHAR(96) NOT NULL,
    organization   VARCHAR(96) NOT NULL,
    owner          VARCHAR(64) NOT NULL,
    contact        VARCHAR(64) NOT NULL,
    bbox           JSON        NOT NULL,
    risk_types     JSON        NOT NULL,
    created_at     DATETIME    NOT NULL
);
CREATE INDEX ix_responsibility_grids_district ON responsibility_grids (district);

-- 应急资源可调度能力；与地理 POI 点位分离
CREATE TABLE emergency_resources (
    id           VARCHAR(16) NOT NULL PRIMARY KEY,
    name         VARCHAR(128) NOT NULL,
    kind         VARCHAR(24) NOT NULL,
    longitude    FLOAT       NOT NULL,
    latitude     FLOAT       NOT NULL,
    capability   VARCHAR(128) NOT NULL,
    capacity     INTEGER     NOT NULL,
    available    INTEGER     NOT NULL,
    status       VARCHAR(16) NOT NULL,               -- available | limited | unavailable
    contact      VARCHAR(64) NOT NULL,
    notes        TEXT        NOT NULL,
    updated_at   DATETIME    NOT NULL
);
CREATE INDEX ix_emergency_resources_kind ON emergency_resources (kind);
CREATE INDEX ix_emergency_resources_status ON emergency_resources (status);

-- 站内通知：工单、反馈、复盘和任务事件
CREATE TABLE notifications (
    id           INTEGER     NOT NULL PRIMARY KEY,
    target       VARCHAR(96) NOT NULL,
    title        VARCHAR(128) NOT NULL,
    body         TEXT        NOT NULL,
    level        VARCHAR(16) NOT NULL,
    entity_type  VARCHAR(24) NOT NULL,
    entity_id    VARCHAR(32) NOT NULL,
    is_read      BOOLEAN     NOT NULL,
    created_at   DATETIME    NOT NULL
);
CREATE INDEX ix_notifications_created_at ON notifications (created_at);
CREATE INDEX ix_notifications_is_read ON notifications (is_read);

-- 跨模块写操作审计
CREATE TABLE audit_logs (
    id             INTEGER      NOT NULL PRIMARY KEY,
    method         VARCHAR(12)  NOT NULL,
    path           VARCHAR(255) NOT NULL,
    action         VARCHAR(24)  NOT NULL,
    entity_type    VARCHAR(24)  NOT NULL,
    entity_id      VARCHAR(32)  NOT NULL,
    operator_id    VARCHAR(16)  NOT NULL,
    operator_name  VARCHAR(64)  NOT NULL,
    role           VARCHAR(24)  NOT NULL,
    status_code    INTEGER      NOT NULL,
    summary        TEXT         NOT NULL,
    before_data    JSON         NOT NULL,
    after_data     JSON         NOT NULL,
    created_at     DATETIME     NOT NULL
);
CREATE INDEX ix_audit_logs_created_at ON audit_logs (created_at);
CREATE INDEX ix_audit_logs_operator ON audit_logs (operator_id);

-- 城市情景推演：会话、不可变版本与运行时间帧
CREATE TABLE scenario_templates (
    id             VARCHAR(16)  NOT NULL PRIMARY KEY,
    name           VARCHAR(128) NOT NULL,
    description    TEXT         NOT NULL,
    scenario_type  VARCHAR(16)  NOT NULL,
    parameters     JSON         NOT NULL,
    created_at     DATETIME     NOT NULL,
    updated_at     DATETIME     NOT NULL
);
CREATE INDEX ix_scenario_templates_type ON scenario_templates (scenario_type);

-- 情景模板的不可变修订版本
CREATE TABLE scenario_template_revisions (
    id             INTEGER      NOT NULL PRIMARY KEY,
    template_id    VARCHAR(16)  NOT NULL REFERENCES scenario_templates(id) ON DELETE CASCADE,
    version_no     INTEGER      NOT NULL,
    name           VARCHAR(128) NOT NULL,
    description    TEXT         NOT NULL,
    scenario_type  VARCHAR(16)  NOT NULL,
    parameters     JSON         NOT NULL,
    operator       VARCHAR(64)  NOT NULL,
    created_at     DATETIME     NOT NULL
);
CREATE INDEX ix_scenario_template_revisions_template
    ON scenario_template_revisions (template_id);

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

CREATE TABLE scenario_resource_reservations (
    id           INTEGER     NOT NULL PRIMARY KEY,
    session_id   VARCHAR(24) NOT NULL REFERENCES scenario_sessions(id) ON DELETE CASCADE,
    resource_id  VARCHAR(16) NOT NULL REFERENCES emergency_resources(id) ON DELETE CASCADE,
    quantity     INTEGER     NOT NULL,
    status       VARCHAR(16) NOT NULL,               -- active | released
    created_at   DATETIME    NOT NULL
);
CREATE INDEX ix_scenario_reservations_session ON scenario_resource_reservations (session_id);
CREATE INDEX ix_scenario_reservations_resource ON scenario_resource_reservations (resource_id);

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
