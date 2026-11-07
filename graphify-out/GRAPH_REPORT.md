# Graph Report - CityEye  (2026-11-07)

## Corpus Check
- 369 files · ~140,705 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 31 file(s) not represented in the graph (top: .csv 14, (none) 8, .geojson 4)

## Summary
- 3093 nodes · 7205 edges · 131 communities (111 shown, 20 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 436 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- 数据加工 · aerial_render
- 业务页面 · TaskResultView
- 后端核心 · seed
- 前端接口
- 推演引擎 · simulator
- 城市总览
- 应急演练
- 业务页面 · EventCreateDialog
- 视觉算法 · render
- 业务页面 · BuildingSafetyPanel
- 前端组件 · CesiumViewer
- 情景服务
- AI分析
- 事件服务
- 视觉算法 · imgproc
- 业务页面 · AssistantChatPanel
- 事件中心
- 前端组件 · AppHeader
- 核心代码 · format
- 视觉算法 · timeseries
- 大模型测试 · test_client
- 数据管理
- 任务服务
- 业务页面 · EventDrawer
- 业务页面 · TrafficPanel
- 前端组件 · Sidebar
- API路由 · scenario
- 后端模型
- 数据工具 · download_satellite_basemap
- 业务页面 · EventTable
- 核心代码 · pages
- 人群疏散 · crowdLayer
- 大模型测试 · test_tool_runner
- 前端模型 · api
- 人群疏散 · crowdLayer
- 业务页面 · ScenarioWorkspace
- 指挥面板
- 前端组件 · EventDetail
- 视觉算法 · traffic
- 后端测试 · test_llm_api
- 三维场景 · roadLayer
- 大模型测试 · test_chat
- 数据加工 · build_geo
- 核心代码 · 武汉智眼首批数据集确定方案_dd680806
- 后端测试 · test_api
- 三维场景 · types
- 核心代码 · ci
- 核心代码 · api
- 人群疏散 · roadGraph
- 业务页面 · CrowdSimulationPanel
- 三维场景 · shaders
- 三维场景 · poiLayer
- 核心代码 · tsconfig
- 视觉算法 · flood
- 大模型测试 · test_report_generator
- 后端服务 · simulator
- API路由 · llm
- 后端核心 · seed
- 核心代码 · crowd-simulation
- 大模型能力 · task_parser
- 前端状态 · metrics
- 三维场景 · cameraControl
- 三维场景 · eventLayer
- 城市空间数据
- 三维场景 · buildingLayer
- 三维场景 · basemap
- 前端状态 · useCityEvents
- 后端核心 · config
- 核心代码 · docker-compose
- 后端核心 · models
- 后端核心 · context
- 三维场景 · roadLayer
- 核心代码 · spec
- 后端服务 · sources
- 核心代码 · algorithms
- 前端模型 · event
- 核心代码 · README
- 算法测试 · test_fire
- 后端测试 · conftest
- 情景空间 · scenarioLayer
- 大模型能力 · HANDOFF
- 后端服务 · realtime
- 核心代码 · README
- 算法测试 · conftest
- 后端测试 · test_scenario_api
- 城市监测
- 前端状态 · useDemoTour
- API路由 · data
- 核心代码 · package
- 前端模型 · scenario
- 三维场景 · icons
- 大模型能力 · README
- 核心代码 · package
- 业务页面 · ScenarioWorkspace
- 业务页面 · ScenarioWorkspace
- 前端模型 · building
- 提示词系统 · cityeye_system
- 业务页面 · TaskHistory
- 核心代码 · tsconfig.node
- API路由 · demo
- 核心代码 · architecture
- 核心代码 · scenario-simulation
- 核心代码 · emergency-drill
- 核心代码 · interface-design
- 数据加工 · build_wuhan_buildings
- 核心代码 · README
- 视觉算法 · base
- 数据加工 · fetch_osm
- 核心代码 · api
- 推演引擎 · missing_fields()
- 情景空间 · scenarioLayer
- 核心代码 · .prettierrc
- 三维场景 · types
- 视觉算法 · imgproc
- 业务页面 · SourceCard
- 核心代码 · README
- 数据工具 · dev
- 核心代码 · manifests/README.md
- 核心代码 · basemap/README.md
- 数据工具 · demo.sh

## God Nodes (most connected - your core abstractions)
1. `AppContext` - 78 edges
2. `CrowdLayer` - 73 edges
3. `vue` - 60 edges
4. `LLMError` - 45 edges
5. `Settings` - 43 edges
6. `request()` - 38 edges
7. `AnalysisResult` - 37 edges
8. `EventType` - 34 edges
9. `CityEvent` - 33 edges
10. `select()` - 31 edges

## Surprising Connections (you probably didn't know these)
- `3. 关键接口` --references--> `CrowdLayer`  [INFERRED]
  docs/crowd-simulation.md → frontend/src/components/scene/crowd/crowdLayer.ts
- ``AnalysisTask`` --references--> `AnalysisTask`  [INFERRED]
  docs/api.md → frontend/src/types/api.ts
- ``GET /api/tasks/{id}` → `AnalysisTask`` --references--> `AnalysisTask`  [INFERRED]
  docs/api.md → frontend/src/types/api.ts
- `外部提供方预留` --references--> `MockScenarioProvider`  [INFERRED]
  docs/scenario-simulation.md → scenario_engine/simulator.py
- `实现边界` --references--> `MockScenarioProvider`  [INFERRED]
  docs/scenario-simulation.md → scenario_engine/simulator.py

## Import Cycles
- 3-file cycle: `algorithm/cityeye_algo/__init__.py -> algorithm/cityeye_algo/registry.py -> algorithm/cityeye_algo/traffic.py -> algorithm/cityeye_algo/__init__.py`
- 3-file cycle: `algorithm/cityeye_algo/__init__.py -> algorithm/cityeye_algo/registry.py -> algorithm/cityeye_algo/fire.py -> algorithm/cityeye_algo/__init__.py`
- 3-file cycle: `algorithm/cityeye_algo/__init__.py -> algorithm/cityeye_algo/registry.py -> algorithm/cityeye_algo/flood.py -> algorithm/cityeye_algo/__init__.py`
- 3-file cycle: `algorithm/cityeye_algo/__init__.py -> algorithm/cityeye_algo/registry.py -> algorithm/cityeye_algo/building.py -> algorithm/cityeye_algo/__init__.py`

## Communities (131 total, 20 thin omitted)

### Community 0 - "数据加工 · aerial_render"
Cohesion: 0.06
Nodes (43): add_collapse(), add_fire(), add_flood(), add_new_structure(), add_street_lights(), BuildingShape, Corridor, finish() (+35 more)

### Community 1 - "业务页面 · TaskResultView"
Cohesion: 0.08
Nodes (38): evidence, evidence, activeAnn, annotated, color, confPct, detected, detections (+30 more)

### Community 2 - "后端核心 · seed"
Cohesion: 0.08
Nodes (9): Base, init_data(), AppMeta, Source, is_seeded(), load_runtime_state(), seed_database(), _seed_sources() (+1 more)

### Community 3 - "前端接口"
Cohesion: 0.11
Nodes (34): getDataList(), getDataStats(), getBuildings(), getFineBuildings(), getPois(), getRoads(), ApiError, ApiMode (+26 more)

### Community 4 - "推演引擎 · simulator"
Cohesion: 0.12
Nodes (19): compare_runs(), _risk_rank(), ImpactZone, PeopleState, ScenarioComparison, ScenarioDraft, ScenarioFrame, ScenarioRun (+11 more)

### Community 5 - "城市总览"
Cohesion: 0.04
Nodes (48): resetDemo(), props, rows, askAssistantDemo(), assistantDemoQuestion, assistantOpen, assistantRef, autoTrack (+40 more)

### Community 6 - "应急演练"
Cohesion: 0.05
Nodes (59): HAZARD_PROFILES, HazardProfile, hazardProfile(), hazardRadiusAt(), requiresPedestrianEvacuation(), smoothstep(), accent, actionText (+51 more)

### Community 7 - "业务页面 · EventCreateDialog"
Cohesion: 0.13
Nodes (18): createEvent(), bbox, center, emit, FALLBACK_CENTER, form, formRef, loadRegion() (+10 more)

### Community 8 - "视觉算法 · render"
Cohesion: 0.08
Nodes (23): assess_settlement(), ChangeDetector, ChangeParams, SettlementAnalyzer, SettlementReport, SettlementThresholds, annotate_image(), Chart (+15 more)

### Community 9 - "业务页面 · BuildingSafetyPanel"
Cohesion: 0.05
Nodes (41): getBuilding(), emit, LEVELS, open, props, SEVERITIES, bProps, CATEGORY (+33 more)

### Community 10 - "前端组件 · CesiumViewer"
Cohesion: 0.06
Nodes (53): active, alarmBuildingIds(), api, bindInteraction(), bindRenderErrorRecovery(), closePanels(), containerRef, createViewer() (+45 more)

### Community 11 - "情景服务"
Cohesion: 0.18
Nodes (12): select(), not_found(), ScenarioRunRecord, ScenarioSession, ScenarioVersion, building_detail(), _apply_demo_defaults(), _new_id() (+4 more)

### Community 12 - "AI分析"
Cohesion: 0.04
Nodes (72): getSamples(), allowedExt, createEvent, emit, fileList, latitude, loadingSamples, loadSamples() (+64 more)

### Community 13 - "事件服务"
Cohesion: 0.19
Nodes (7): add_log(), apply_patch(), create_event(), event_from_result(), event_name_for(), next_id(), transition()

### Community 14 - "视觉算法 · imgproc"
Cohesion: 0.10
Nodes (26): clamp01(), blur(), box_mean(), box_sum(), closing(), dilate(), erode(), label_components() (+18 more)

### Community 15 - "业务页面 · AssistantChatPanel"
Cohesion: 0.05
Nodes (45): chatWithAssistant(), generateEventReport(), llmRequest(), parseTaskText(), AnswerBlock, busy, canSend, dataType (+37 more)

### Community 16 - "事件中心"
Cohesion: 0.05
Nodes (42): todayPrefix(), activeOnly, applyQuery(), createVisible, diffFlash(), drawerId, drawerOpen, FILTER_KEYS (+34 more)

### Community 17 - "前端组件 · AppHeader"
Cohesion: 0.13
Nodes (24): 10. WebSocket `/api/ws`, getTask(), city, conn, { connected }, date, demoTip, everConnected (+16 more)

### Community 18 - "核心代码 · format"
Cohesion: 0.18
Nodes (20): metrics, defaultIndex(), deriveOverview(), normalize(), useOverview(), refresh(), resume(), fixed() (+12 more)

### Community 19 - "视觉算法 · timeseries"
Cohesion: 0.12
Nodes (12): InputError, damped_holt(), fmt_t(), median_step_minutes(), moving_average(), parse_times(), read_header(), read_table() (+4 more)

### Community 20 - "大模型测试 · test_client"
Cohesion: 0.17
Nodes (11): ask(), LLMError, main(), main(), FakeClient, FakeCompletions, settings(), test_ask_includes_system_prompt() (+3 more)

### Community 21 - "数据管理"
Cohesion: 0.05
Nodes (44): uploadData(), option, props, statuses, emit, option, props, total (+36 more)

### Community 22 - "任务服务"
Cohesion: 0.12
Nodes (18): bad_request(), Task, _check_type(), get_task(), list_tasks(), _parse_float(), post_task(), upload_task() (+10 more)

### Community 23 - "业务页面 · EventDrawer"
Cohesion: 0.07
Nodes (25): ACTION_META, actionLabel(), ASSIGNEES, copyCoord(), currentId, emit, event, fetched (+17 more)

### Community 24 - "业务页面 · TrafficPanel"
Cohesion: 0.13
Nodes (18): BASE, chart, el, props, gauge, groups, level, levelCounts (+10 more)

### Community 25 - "前端组件 · Sidebar"
Cohesion: 0.07
Nodes (24): dependencies, element-plus@^2.9.0, @element-plus/icons-vue@^2.3.1, vue@^3.5.13, vue-router@^4.5.0, isDrill, route, { sidebarCollapsed } (+16 more)

### Community 26 - "API路由 · scenario"
Cohesion: 0.21
Nodes (15): AppContext, buildings(), fine_buildings(), compare_runs(), create_session(), get_run(), get_session(), post_message() (+7 more)

### Community 27 - "后端模型"
Cohesion: 0.08
Nodes (33): get_event(), list_events(), patch_event(), post_event(), AlgorithmInfoOut, AlgorithmOut, AnalysisTaskOut, BuildingDetailOut (+25 more)

### Community 28 - "数据工具 · download_satellite_basemap"
Cohesion: 0.18
Nodes (11): BBox, build_parser(), crop_window(), download_tile(), lat_to_tile_y(), lon_to_tile_x(), main(), parse_bbox() (+3 more)

### Community 29 - "业务页面 · EventTable"
Cohesion: 0.16
Nodes (10): emit, onRowClick(), onSortChange(), props, showAssignee, showSource, SortState, vw (+2 more)

### Community 30 - "核心代码 · pages"
Cohesion: 0.05
Nodes (38): defaults, runs-on, steps, concurrency, cancel-in-progress, group, run, environment (+30 more)

### Community 31 - "人群疏散 · crowdLayer"
Cohesion: 0.09
Nodes (27): CrowdPerson, EXIT_CAPACITIES, EXIT_LABELS, HazardState, installGaitShader(), makeStickFigureGeometry(), makeVehicleGeometry(), RoadPath (+19 more)

### Community 32 - "大模型测试 · test_tool_runner"
Cohesion: 0.12
Nodes (18): _client(), get_demo_event(), list_demo_facilities(), 4. Tool Calling, build_input(), main(), ScriptedClient, ScriptedCompletions (+10 more)

### Community 33 - "前端模型 · api"
Cohesion: 0.06
Nodes (36): `DataItem`, props, rate, ringOffset, rows, sources, totals, option (+28 more)

### Community 34 - "人群疏散 · crowdLayer"
Cohesion: 0.10
Nodes (4): CrowdLayer, CrowdBenchmarkRow, PersonType, SpawnType

### Community 35 - "业务页面 · ScenarioWorkspace"
Cohesion: 0.07
Nodes (28): busy, classLabel(), comparison, currentFrame, currentRadius, dataClassLabel, error, extentChange (+20 more)

### Community 36 - "指挥面板"
Cohesion: 0.09
Nodes (29): 2. 事件, `CityEvent`, `EventLog`, `GET /api/events`, `GET /api/events/{id}` → `CityEvent`（404 不存在）, `GET /api/events/{id}/logs` → `EventLog[]`（按时间正序）, `PATCH /api/events/{id}`, `POST /api/events`（人工上报 / 市民上报） (+21 more)

### Community 37 - "前端组件 · EventDetail"
Cohesion: 0.08
Nodes (26): getEventLogs(), assignee, assigneeOptions, busy, confidence, demoDispatch(), dispatchOpen, dispatchTarget (+18 more)

### Community 38 - "视觉算法 · traffic"
Cohesion: 0.13
Nodes (16): AnalysisResult, Band, network_tpi(), speed_to_tpi(), _touches_border(), tpi_level(), TrafficSeriesAnalyzer, VehicleOccupancyAnalyzer (+8 more)

### Community 39 - "后端测试 · test_llm_api"
Cohesion: 0.13
Nodes (15): report(), test_chat_attaches_seeded_event_context(), test_chat_rejects_invalid_history(), test_chat_without_event_context(), fake_chat(), test_llm_status_availability_is_environment_independent(), test_parse_task_rejects_invalid_length(), test_report_marks_citizen_input_unverified() (+7 more)

### Community 40 - "三维场景 · roadLayer"
Cohesion: 0.16
Nodes (18): cleanRing(), distance(), isFiniteCoord(), lineLength(), lineMidpoint(), LonLat, resampleLine(), ringAreaM2() (+10 more)

### Community 41 - "大模型测试 · test_chat"
Cohesion: 0.15
Nodes (12): answer_chat(), _build_prompt(), ChatTurn, load_system_prompt(), main(), FakeClient, FakeCompletions, test_chat_includes_history_and_event_context() (+4 more)

### Community 42 - "数据加工 · build_geo"
Cohesion: 0.16
Nodes (18): build_buildings(), build_pois(), build_roads(), length(), classify(), clip_chain(), dist_m(), district_of() (+10 more)

### Community 43 - "核心代码 · 武汉智眼首批数据集确定方案_dd680806"
Cohesion: 0.07
Nodes (26): 01　火灾与烟雾：D-Fire, 02　航拍车辆：VisDrone2019-DET, 03　建筑灾前灾后：xBD / xView2, 04　获取顺序、登记与验收, 05　武汉本地数据补充, 05　武汉本地数据补充（续）, 05　武汉本地数据补充（续）, 5.1　UAV-OBB：含武汉道路的车辆数据 (+18 more)

### Community 44 - "后端测试 · test_api"
Cohesion: 0.09
Nodes (3): test_data_list_stats_upload(), test_events_list_shape_and_order(), test_stats_overview()

### Community 46 - "核心代码 · ci"
Cohesion: 0.09
Nodes (25): name, runs-on, steps, run, defaults, name, runs-on, steps (+17 more)

### Community 47 - "核心代码 · api"
Cohesion: 0.08
Nodes (25): 0. 通用约定, 11. 城市智能情景推演, 1. 系统, 3. 城市三维对象, 4. 统计, 5. 数据资产, 7. 监测数据源, 8. 演示控制（demo_mode=true 时可用） (+17 more)

### Community 48 - "人群疏散 · roadGraph"
Cohesion: 0.14
Nodes (10): GraphEdge, GraphLine, GraphPoint, hazardPenalizedCost(), MinHeap, PlannedRoute, pointDistance(), projectOnSegment() (+2 more)

### Community 49 - "业务页面 · CrowdSimulationPanel"
Cohesion: 0.10
Nodes (19): benchmark, busy, clearPeople(), count, dangerRadius, emptyEvacuation, emptyStats, evacuate() (+11 more)

### Community 50 - "三维场景 · shaders"
Cohesion: 0.12
Nodes (16): cesium@1.125.0, Region, AmbientEffects, beamAppearance(), encode(), f(), LINE_VERTEX_FORMAT, lineAppearance() (+8 more)

### Community 51 - "三维场景 · poiLayer"
Cohesion: 0.19
Nodes (6): poiIcon(), roundRect(), PoiLayer, SCALE_BY_DISTANCE, Poi, POI_META

### Community 52 - "核心代码 · tsconfig"
Cohesion: 0.09
Nodes (21): compilerOptions, allowImportingTsExtensions, baseUrl, isolatedModules, jsx, lib, module, moduleDetection (+13 more)

### Community 53 - "视觉算法 · flood"
Cohesion: 0.17
Nodes (9): FloodThresholds, WaterLevelAnalyzer, _storm(), test_csv_samples(), test_light_rain_not_detected(), test_rainstorm_detected_with_lag(), test_rising_series_forecast_without_rain(), test_threshold_levels() (+1 more)

### Community 54 - "大模型测试 · test_report_generator"
Cohesion: 0.18
Nodes (12): AnalysisFinding, EventOverview, generate_report(), load_report_prompt(), ReportError, RiskAssessment, FakeClient, FakeCompletions (+4 more)

### Community 55 - "后端服务 · simulator"
Cohesion: 0.09
Nodes (7): lifespan(), ws_endpoint(), Simulator, now(), test_lifecycle_advances_and_respects_state_machine(), test_patrol_creates_events_only_on_detection(), test_traffic_tick_and_events()

### Community 56 - "API路由 · llm"
Cohesion: 0.21
Nodes (13): _call_llm(), ChatIn, ChatMessageIn, _distance_m(), _event_data_nature(), _event_view(), llm_status(), _load_event_context() (+5 more)

### Community 57 - "后端核心 · seed"
Cohesion: 0.15
Nodes (4): _EventBuilder, _seed_data_assets(), _seed_settlement(), _Spec

### Community 58 - "核心代码 · crowd-simulation"
Cohesion: 0.10
Nodes (21): 1.1 选型结论, 1.2 坐标系, 1. 技术融合方案, 2.1 人物模型, 2.2 实例化策略, 2. 模块架构, 3. 关键接口, 4.1 单人行为 (+13 more)

### Community 59 - "大模型能力 · task_parser"
Cohesion: 0.11
Nodes (20): parsed_task(), test_parse_task_retries_one_malformed_model_output(), flaky_parse(), test_parse_task_route_and_provider_error(), fake_parse(), Settings, generate_scenario_report(), HybridReportError (+12 more)

### Community 60 - "前端状态 · metrics"
Cohesion: 0.12
Nodes (21): metrics, metrics, EXTRA_COLORS, extraKeys, MAIN_NAME, option, props, Series (+13 more)

### Community 61 - "三维场景 · cameraControl"
Cohesion: 0.16
Nodes (4): CameraController, wait(), FlyOptions, OrbitOptions

### Community 62 - "三维场景 · eventLayer"
Cohesion: 0.09
Nodes (20): ALWAYS, beamInstance(), circlePositions(), clusterBadge(), clusterColor(), clusterOutlineInstance(), ellipseFillInstance(), ellipseInstance() (+12 more)

### Community 63 - "城市空间数据"
Cohesion: 0.08
Nodes (7): base_road_name(), GeoRepository, is_generic_name(), Road, congestion_curve(), RoadLive, TrafficState

### Community 64 - "三维场景 · buildingLayer"
Cohesion: 0.09
Nodes (17): buildingColor(), BuildingLayer, BuildingRecord, extrude(), frameNumberOf(), HEIGHT_STOPS, nextFrame(), polygonsOf() (+9 more)

### Community 65 - "三维场景 · basemap"
Cohesion: 0.27
Nodes (6): BasemapController, GLOBE_BASE_COLOR, STYLE, BasemapConfig, BasemapKey, BASEMAPS

### Community 66 - "前端状态 · useCityEvents"
Cohesion: 0.12
Nodes (23): getEvents(), patchEvent(), snapshotEvents(), { calm, demoEventIds }, { connected, lastMessageAt }, displayStats, lastUpdate, MODE_LABEL (+15 more)

### Community 67 - "后端核心 · config"
Cohesion: 0.16
Nodes (5): _bool(), _float(), _path(), Settings, main()

### Community 68 - "核心代码 · docker-compose"
Cohesion: 0.11
Nodes (17): build, container_name, environment, image, ports, restart, volumes, CITYEYE_DEMO_MODE (+9 more)

### Community 69 - "后端核心 · models"
Cohesion: 0.13
Nodes (11): Event, EventLog, SettlementSeries, get_logs(), stats_overview(), log_to_dict(), overview(), safety_score() (+3 more)

### Community 71 - "三维场景 · roadLayer"
Cohesion: 0.15
Nodes (4): alphaOf(), RoadLayer, TrafficUpdate, Road

### Community 72 - "核心代码 · spec"
Cohesion: 0.12
Nodes (15): resetFilters(), 1. 现状结论（已核实）, 2. 改动清单, 3. 明确不做（本轮）, 4. 验证计划, 5. 风险与回退, R1 表格响应式列断点修正, R2 事件表格空状态增加操作入口 (+7 more)

### Community 74 - "核心代码 · algorithms"
Cohesion: 0.12
Nodes (15): severity_for(), 1. 火灾 · FlameNet-Lite（`fire.py`）, 2.1 TrafficPulse · 时序路况（`traffic.py`）, 2.2 RoadOcc · 航拍路面车辆占有率, 2. 交通, 3.1 SettleWatch · 沉降监测（`building.py`）, 3.2 ChangeScope · 前后时相变化检测, 3. 建筑 (+7 more)

### Community 75 - "前端模型 · event"
Cohesion: 0.18
Nodes (17): EventQuery, FormState, aggregateEventsByDistrict(), EventCluster, SEVERITY_RANK, now, DrillMetric, DrillSeed (+9 more)

### Community 76 - "核心代码 · README"
Cohesion: 0.12
Nodes (17): 🔌 API 一览, ✨ 亮点, 🕸️ 代码图谱, 🗺️ 功能导览, 城市智眼 · CityEye, 🚀 快速开始, 📚 数据来源与致谢, 方式一：Docker（推荐，一条命令） (+9 more)

### Community 77 - "算法测试 · test_fire"
Cohesion: 0.19
Nodes (7): det(), test_plain_city_not_detected(), test_procedural_flame_detected(), test_red_roofs_and_orange_car_not_detected(), test_samples_negative(), test_samples_positive(), test_smoke_scored_on_sample_with_plume()

### Community 78 - "后端测试 · conftest"
Cohesion: 0.14
Nodes (6): client(), ctx(), tmp_root(), wait_task(), dump(), main()

### Community 79 - "情景空间 · scenarioLayer"
Cohesion: 0.33
Nodes (3): ScenarioLayer, ScenarioFrame, ScenarioZone

### Community 80 - "大模型能力 · HANDOFF"
Cohesion: 0.14
Nodes (13): 1. DeepSeek API, 2. CityEye 系统提示词, 3. 自然语言任务解析, 5. 结构化报告, CityEye 大模型模块压缩交接, Git 状态, 下一步, 会话目标 (+5 more)

### Community 81 - "后端服务 · realtime"
Cohesion: 0.08
Nodes (8): make_engine(), make_session_factory(), create_app(), _on_validation(), __getattr__(), _validation_message(), envelope(), RealtimeHub

### Community 82 - "核心代码 · README"
Cohesion: 0.15
Nodes (5): cityeye_algo —— 城市智眼算法包, 使用, 测试, 5 分钟路演脚本, 演示备忘

### Community 83 - "算法测试 · conftest"
Cohesion: 0.12
Nodes (9): city_background(), paint_flame(), rng(), sample(), save(), test_steady_settlement_is_watch(), test_select(), test_select_errors() (+1 more)

### Community 84 - "后端测试 · test_scenario_api"
Cohesion: 0.17
Nodes (9): agent_output(), test_compare_does_not_require_current_parameters(), test_demo_auto_run_fills_assumptions_and_builds_three_variants(), test_scenario_missing_parameters_are_reported(), test_scenario_session_and_run(), converse(), ScenarioAgentOutput, ScenarioParameters (+1 more)

### Community 85 - "城市监测"
Cohesion: 0.11
Nodes (19): nowText(), ageSec, buildings, cityTpi, devicesOnline, devicesTotal, history, info (+11 more)

### Community 86 - "前端状态 · useDemoTour"
Cohesion: 0.18
Nodes (21): getEvent(), apiState, triggerScenario(), ensureEvent(), TourFocus, DemoTourContext, DemoTourHooks, TourCancelled (+13 more)

### Community 87 - "API路由 · data"
Cohesion: 0.16
Nodes (12): DataAsset, asset_to_dict(), data_stats(), list_data(), upload_data(), pois(), roads(), health() (+4 more)

### Community 88 - "核心代码 · package"
Cohesion: 0.06
Nodes (38): echarts@^5.6.0, three@^0.187.0, vite-plugin-static-copy@^2.2.0, description, devDependencies, eslint@^9.39.5, eslint-config-prettier@^9.1.2, eslint-plugin-vue@^9.33.0 (+30 more)

### Community 89 - "前端模型 · scenario"
Cohesion: 0.23
Nodes (10): SCENARIO_LABEL, ScenarioComparison, ScenarioDataClass, ScenarioMessage, ScenarioParameters, ScenarioPerson, ScenarioReport, ScenarioRun (+2 more)

### Community 90 - "三维场景 · icons"
Cohesion: 0.16
Nodes (12): props, rows, total, cache, emojiSupported(), EVENT_GLYPH, eventIcon(), POI_COLOR (+4 more)

### Community 92 - "大模型能力 · README"
Cohesion: 0.17
Nodes (11): CityEye 大模型模块, Tool Calling 验证, 城市治理问答, 安装, 当前范围, 测试, 系统提示词测试, 结构化研判报告 (+3 more)

### Community 93 - "核心代码 · package"
Cohesion: 0.18
Nodes (11): scripts, build, dev, format, format:check, lint, lint:fix, preview (+3 more)

### Community 94 - "业务页面 · ScenarioWorkspace"
Cohesion: 0.17
Nodes (13): compareScenarioRuns(), createScenarioSession(), generateScenarioReport(), runCurrentScenarioVariants(), scenarioRequest(), sendScenarioMessage(), compare(), demoStart() (+5 more)

### Community 95 - "业务页面 · ScenarioWorkspace"
Cohesion: 0.28
Nodes (9): applyPeople(), demoStop(), ensureLayer(), loadRun(), pause(), reset(), setMapVisible(), showFrame() (+1 more)

### Community 96 - "前端模型 · building"
Cohesion: 0.09
Nodes (19): display, props, grade, levelMeta, LEVELS, marker, option, props (+11 more)

### Community 97 - "提示词系统 · cityeye_system"
Cohesion: 0.18
Nodes (10): CityEye 城市治理助手, 信息使用规则, 信息缺口, 分析, 回答格式, 安全规则, 已知信息, 建议 (+2 more)

### Community 98 - "业务页面 · TaskHistory"
Cohesion: 0.18
Nodes (9): emit, onRowClick(), page, props, rows, showAlgo, showProg, vw (+1 more)

### Community 99 - "核心代码 · tsconfig.node"
Cohesion: 0.20
Nodes (9): compilerOptions, allowSyntheticDefaultImports, composite, module, moduleResolution, outDir, skipLibCheck, strict (+1 more)

### Community 100 - "API路由 · demo"
Cohesion: 0.24
Nodes (6): get_ctx(), _require_demo(), reset(), scenario(), ScenarioRequest, random_site()

### Community 101 - "核心代码 · architecture"
Cohesion: 0.22
Nodes (8): 1. 总体架构, 2.1 实时事件闭环, 2.2 AI 分析任务, 2. 关键数据流, 3. 三维场景设计, 4. 运行模式, 5. 扩展点, 系统架构

### Community 102 - "核心代码 · scenario-simulation"
Cohesion: 0.20
Nodes (10): API, CityEye 城市智能情景推演, 三场景, 三维联动, 交互与状态, 外部提供方预留, 实现边界, 数据性质 (+2 more)

### Community 103 - "核心代码 · emergency-drill"
Cohesion: 0.25
Nodes (7): Demo 演示增强, 事件种子, 交互闭环, 入口与实现, 城市应急演练, 定位, 数据边界

### Community 104 - "核心代码 · interface-design"
Cohesion: 0.25
Nodes (8): CityEye 界面设计说明, 各页面问题, 应急演练页, 方向, 本轮调整, 真实城市视图中的事件层级, 设计边界, 验证

### Community 105 - "数据加工 · build_wuhan_buildings"
Cohesion: 0.36
Nodes (3): main(), polygons(), main()

### Community 106 - "核心代码 · README"
Cohesion: 0.33
Nodes (5): sources(), ER 图, 数据库设计, 种子数据（`backend/app/seed.py`）, 表说明

### Community 107 - "视觉算法 · base"
Cohesion: 0.09
Nodes (15): AlgorithmMeta, Analyzer, Artifact, _clean_metric(), Detection, FireDetector, FireParams, WaterSegmenter (+7 more)

### Community 108 - "数据加工 · fetch_osm"
Cohesion: 0.39
Nodes (3): main(), query(), tiles()

### Community 109 - "核心代码 · api"
Cohesion: 0.29
Nodes (7): 6. AI 分析任务, `AnalysisTask`, `GET /api/samples?type=fire` → 示例数据, `GET /api/tasks` → `AnalysisTask[]`（按创建时间倒序）, `GET /api/tasks/{id}` → `AnalysisTask`, `POST /api/tasks`（JSON，兼容原型）, `POST /api/tasks/upload`（multipart）

### Community 111 - "情景空间 · scenarioLayer"
Cohesion: 0.22
Nodes (7): PREVIOUS_EDGE, RISK_COLOR, WATER_BODY, WATER_EDGE, RoadCollection, ScenarioRisk, ScenarioType

### Community 112 - "核心代码 · .prettierrc"
Cohesion: 0.33
Nodes (5): arrowParens, printWidth, semi, singleQuote, trailingComma

### Community 113 - "三维场景 · types"
Cohesion: 0.15
Nodes (13): BASEMAP_OPTIONS, emit, LAYERS, EventSyncOptions, emit, DEFAULT_LAYERS, EventTypeFilter, LayerKey (+5 more)

### Community 115 - "业务页面 · SourceCard"
Cohesion: 0.07
Nodes (24): props, shown, checking, props, text, emit, age, extent (+16 more)

### Community 116 - "核心代码 · README"
Cohesion: 0.50
Nodes (3): 当前数据, 数据集目录, 目录约定

## Knowledge Gaps
- **20 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `create_event()` connect `事件服务` to `后端核心 · seed`, `后端核心 · models`, `后端核心 · context`, `核心代码 · api`, `后端服务 · simulator`, `后端核心 · seed`, `后端模型`?**
  _High betweenness centrality (0.215) - this node is a cross-community bridge._
- **Are the 46 inferred relationships involving `AppContext` (e.g. with `init_data()` and `data_stats()`) actually correct?**
  _`AppContext` has 46 INFERRED edges - model-reasoned connections that need verification._
- **Should `数据加工 · aerial_render` be split into smaller, more focused modules?**
  _Cohesion score 0.06275946275946276 - nodes in this community are weakly interconnected._
- **Why does `6. AI 分析任务` connect `核心代码 · api` to `核心代码 · api`?**
  _High betweenness centrality (0.215) - this node is a cross-community bridge._
- **Are the 16 inferred relationships involving `LLMError` (e.g. with `_call_llm()` and `llm_status()`) actually correct?**
  _`LLMError` has 16 INFERRED edges - model-reasoned connections that need verification._
- **Should `业务页面 · TaskResultView` be split into smaller, more focused modules?**
  _Cohesion score 0.07610993657505286 - nodes in this community are weakly interconnected._
- **Why does `CrowdLayer` connect `人群疏散 · crowdLayer` to `应急演练`, `前端组件 · CesiumViewer`, `人群疏散 · roadGraph`, `业务页面 · CrowdSimulationPanel`, `核心代码 · crowd-simulation`, `人群疏散 · crowdLayer`, `人群疏散 · crowdLayer`?**
  _High betweenness centrality (0.215) - this node is a cross-community bridge._