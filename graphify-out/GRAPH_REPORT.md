# Graph Report - CityEye  (2026-11-11)

## Corpus Check
- 324 files · ~694,995 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 41 file(s) not represented in the graph (top: .csv 14, .geojson 11, (none) 8)

## Summary
- 3968 nodes · 9628 edges · 167 communities (119 shown, 48 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 655 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `66cd814`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- ReviewBoard.vue
- EventDrawer.vue
- WorkflowPulse.vue
- @element-plus/icons-vue
- Dashboard.vue
- EmergencyDrill.vue
- schemas.py
- api/workflow.ts
- BuildingSafetyPanel.vue
- CesiumViewer.vue
- AIAnalysis.vue
- InputError
- numpy
- errMsg
- EventCenter.vue
- scene/types.ts
- useOverview.ts
- WaterLevelAnalyzer
- ask
- DataManagement.vue
- services/tasks.py
- registry.py
- icons.ts
- Monitoring.vue
- AppContext
- types/event.ts
- download_satellite_basemap.py
- Simulator
- steps
- crowdLayer.ts
- cityeye_algo/traffic.py
- http.ts
- CrowdLayer
- ScenarioWorkspace.vue
- LLMError
- EventDetail.vue
- AssessmentQueue.vue
- routers/geo.py
- roadLayer.ts
- TrafficSeriesAnalyzer
- 武汉智眼首批数据集确定方案_dd680806.md
- test_api.py
- SceneApi
- with
- 城市智眼 API 契约（v1）
- roadGraph.ts
- CrowdSimulationPanel.vue
- numpy
- TaskSeriesChart.vue
- compilerOptions
- StatusPanel.vue
- seed.py
- LandmarkLayer
- llm.py
- _EventBuilder
- CityEye 城市虚拟人群仿真模块
- Settings
- assess_settlement
- CameraController
- tool_runner.py
- GeoRepository
- roadLayer.ts
- api/scenario.ts
- OrderBoard.vue
- services/scenario.py
- cityeye
- Monitoring.vue
- SystemManagement.vue
- pytest
- 规格：CityEye 前端渐进式改进（第 1 批）
- routers/workflow.py
- 城市智眼 · 算法说明
- EventDrawer.vue
- 城市智眼 · CityEye
- test_fire.py
- algorithm/tests/conftest.py
- types/scenario.ts
- CityEye 大模型模块压缩交接
- build_geo.py
- README.md
- test_workflow_api.py
- devDependencies
- request
- CityEvent
- AssistantChatPanel.vue
- SourceState
- dependencies
- create_app
- scripts
- CityEye 大模型模块
- 5. 数据资产
- CityEye 项目交接说明
- TaskQueue.vue
- 回答格式
- EventCreateDialog.vue
- compilerOptions
- loadRun
- 系统架构
- manifest.json
- 城市应急演练
- CityEye 界面设计说明
- building.ts
- AIAnalysis.vue
- vite.config.ts
- eventLayer.ts
- argparse
- .prettierrc.json
- 数据库设计
- 数据集目录
- dev.sh
- manifests/README.md
- basemap/README.md
- demo.sh
- package.json
- TrafficState
- pages/format.ts
- cesium
- export_snapshot.py
- RealtimeHub
- eslint.config.js
- build_wuhan_buildings.py
- TaskHistory.vue
- config.py
- backend/tests/conftest.py
- EventTable.vue
- AppHeader.vue
- llm_module/__init__.py
- Road
- record_http_audit
- .create
- Region
- 城市智眼业务闭环重构：第一阶段
- 3. 城市三维对象

## God Nodes (most connected - your core abstractions)
1. `AppContext` - 146 edges
2. `request()` - 91 edges
3. `CrowdLayer` - 73 edges
4. `vue` - 68 edges
5. `select()` - 67 edges
6. `get()` - 54 edges
7. `not_found()` - 49 edges
8. `now()` - 48 edges
9. `Settings` - 42 edges
10. `jsonBody()` - 40 edges

## Surprising Connections (you probably didn't know these)
- `3. 关键接口` --references--> `CrowdLayer`  [INFERRED]
  docs/crowd-simulation.md → frontend/src/components/scene/crowd/crowdLayer.ts
- ``DataItem`` --references--> `DataItem`  [INFERRED]
  docs/api.md → frontend/src/types/api.ts
- ``MonitoringRun`` --references--> `Task`  [INFERRED]
  docs/api.md → backend/app/models.py
- ``Assessment`` --references--> `Assessment`  [INFERRED]
  docs/api.md → frontend/src/types/workflow.ts
- `3.1 SettleWatch · 沉降监测（`building.py`）` --references--> `SettlementThresholds`  [INFERRED]
  docs/algorithms.md → algorithm/cityeye_algo/building.py

## Import Cycles
- 3-file cycle: `algorithm/cityeye_algo/__init__.py -> algorithm/cityeye_algo/registry.py -> algorithm/cityeye_algo/building.py -> algorithm/cityeye_algo/__init__.py`
- 3-file cycle: `algorithm/cityeye_algo/__init__.py -> algorithm/cityeye_algo/registry.py -> algorithm/cityeye_algo/fire.py -> algorithm/cityeye_algo/__init__.py`
- 3-file cycle: `algorithm/cityeye_algo/__init__.py -> algorithm/cityeye_algo/registry.py -> algorithm/cityeye_algo/flood.py -> algorithm/cityeye_algo/__init__.py`
- 3-file cycle: `algorithm/cityeye_algo/__init__.py -> algorithm/cityeye_algo/registry.py -> algorithm/cityeye_algo/traffic.py -> algorithm/cityeye_algo/__init__.py`

## Communities (167 total, 48 thin omitted)

### Community 0 - "ReviewBoard.vue"
Cohesion: 0.06
Nodes (35): applyReviewToTemplate(), createReview(), getReviewCases(), getReviewDraft(), reviewExportUrl(), updateReview(), applyBusy, applyRule() (+27 more)

### Community 1 - "EventDrawer.vue"
Cohesion: 0.09
Nodes (25): evidence, evidence, activeAnn, annotated, color, confPct, detected, detections (+17 more)

### Community 2 - "WorkflowPulse.vue"
Cohesion: 0.06
Nodes (44): getDataList(), getDataStats(), qs(), getAssessmentContext(), getAssessments(), getMonitoringRuns(), getMonitoringTasks(), getReviews() (+36 more)

### Community 3 - "@element-plus/icons-vue"
Cohesion: 0.07
Nodes (25): isDrill, route, { sidebarCollapsed }, aiItems, { calm, demoEventIds }, displayActive, mobileMoreOpen, moreItems (+17 more)

### Community 5 - "Dashboard.vue"
Cohesion: 0.04
Nodes (49): resetDemo(), askAssistantDemo(), assistantDemoQuestion, assistantOpen, assistantRef, autoTrack, basemap, { calm: calmBaseline, demoEventIds, enterCalmBaseline, revealAnomalies, setDemoEventIds } (+41 more)

### Community 6 - "EmergencyDrill.vue"
Cohesion: 0.05
Nodes (59): HAZARD_PROFILES, HazardProfile, hazardProfile(), hazardRadiusAt(), requiresPedestrianEvacuation(), smoothstep(), accent, actionText (+51 more)

### Community 7 - "schemas.py"
Cohesion: 0.05
Nodes (77): revision_to_dict(), AccountOut, AlgorithmInfoOut, AlgorithmOut, AnalysisTaskOut, AssessmentContextOut, AssessmentCreate, AssessmentOut (+69 more)

### Community 8 - "api/workflow.ts"
Cohesion: 0.09
Nodes (35): EventCluster, SEVERITY_RANK, DRILL_SEEDS, DrillMetric, DrillSeed, EventType, Severity, Assessment (+27 more)

### Community 9 - "BuildingSafetyPanel.vue"
Cohesion: 0.05
Nodes (39): getBuilding(), BASE, chart, el, props, bProps, CATEGORY, chart (+31 more)

### Community 10 - "CesiumViewer.vue"
Cohesion: 0.05
Nodes (56): active, alarmBuildingIds(), api, bindInteraction(), bindRenderErrorRecovery(), chooseDistrict(), closePanels(), containerRef (+48 more)

### Community 12 - "AIAnalysis.vue"
Cohesion: 0.05
Nodes (50): getSamples(), findRiskBuilding(), allowedExt, createEvent, emit, fileList, latitude, loadingSamples (+42 more)

### Community 13 - "InputError"
Cohesion: 0.12
Nodes (12): InputError, damped_holt(), fmt_t(), median_step_minutes(), moving_average(), parse_times(), read_header(), read_table() (+4 more)

### Community 14 - "numpy"
Cohesion: 0.10
Nodes (26): clamp01(), blur(), box_mean(), box_sum(), closing(), dilate(), erode(), label_components() (+18 more)

### Community 15 - "errMsg"
Cohesion: 0.09
Nodes (31): generateEventReport(), llmRequest(), parseTaskText(), busy, error, KIND_META, offline, props (+23 more)

### Community 16 - "EventCenter.vue"
Cohesion: 0.05
Nodes (42): todayPrefix(), activeOnly, applyQuery(), createVisible, diffFlash(), drawerId, drawerOpen, FILTER_KEYS (+34 more)

### Community 17 - "scene/types.ts"
Cohesion: 0.11
Nodes (19): BASEMAP_OPTIONS, emit, LAYERS, BasemapController, GLOBE_BASE_COLOR, STYLE, emit, DEFAULT_LAYERS (+11 more)

### Community 18 - "useOverview.ts"
Cohesion: 0.23
Nodes (16): metrics, lastUpdate, pad(), fixed(), hhmm(), isToday(), metricLabel(), metricValue() (+8 more)

### Community 19 - "WaterLevelAnalyzer"
Cohesion: 0.15
Nodes (10): FloodThresholds, WaterLevelAnalyzer, Bars, _storm(), test_csv_samples(), test_light_rain_not_detected(), test_rainstorm_detected_with_lag(), test_rising_series_forecast_without_rain() (+2 more)

### Community 20 - "ask"
Cohesion: 0.11
Nodes (15): main(), ask(), _client(), LLMError, converse(), main(), FakeClient, FakeCompletions (+7 more)

### Community 21 - "DataManagement.vue"
Cohesion: 0.03
Nodes (77): autoCheckDataAsset(), getDataValidations(), uploadData(), validateDataAsset(), patchEmergencyResource(), option, props, statuses (+69 more)

### Community 22 - "services/tasks.py"
Cohesion: 0.06
Nodes (35): bad_request(), DataValidationRecord, Task, auto_check_data_asset(), upload_data(), validate_data_asset(), validation_to_dict(), _require_demo() (+27 more)

### Community 23 - "registry.py"
Cohesion: 0.13
Nodes (7): Analyzer, _clean_metric(), algorithms(), file_kind(), run(), _run_batch(), validate()

### Community 24 - "icons.ts"
Cohesion: 0.19
Nodes (6): poiIcon(), roundRect(), PoiLayer, SCALE_BY_DISTANCE, Poi, POI_META

### Community 25 - "Monitoring.vue"
Cohesion: 0.04
Nodes (46): props, shown, props, rows, props, rate, ringOffset, rows (+38 more)

### Community 26 - "AppContext"
Cohesion: 0.05
Nodes (97): select(), AppContext, not_found(), ScenarioTemplate, data_stats(), list_data(), list_data_validations(), get_event() (+89 more)

### Community 27 - "types/event.ts"
Cohesion: 0.12
Nodes (29): EventQuery, getEvents(), patchEvent(), snapshotEvents(), nowString(), getOverview(), lastCreated, revision (+21 more)

### Community 28 - "download_satellite_basemap.py"
Cohesion: 0.17
Nodes (11): BBox, build_parser(), crop_window(), download_tile(), lat_to_tile_y(), lon_to_tile_x(), main(), parse_bbox() (+3 more)

### Community 29 - "Simulator"
Cohesion: 0.09
Nodes (6): lifespan(), random_site(), Simulator, test_lifecycle_advances_and_respects_state_machine(), test_patrol_creates_events_only_on_detection(), test_traffic_tick_and_events()

### Community 30 - "steps"
Cohesion: 0.05
Nodes (39): defaults, runs-on, steps, concurrency, cancel-in-progress, group, run, environment (+31 more)

### Community 31 - "crowdLayer.ts"
Cohesion: 0.10
Nodes (28): CrowdPerson, EXIT_CAPACITIES, EXIT_LABELS, HazardState, installGaitShader(), makeStickFigureGeometry(), makeVehicleGeometry(), RoadPath (+20 more)

### Community 32 - "cityeye_algo/traffic.py"
Cohesion: 0.09
Nodes (20): AlgorithmMeta, Artifact, Detection, SettlementAnalyzer, FireDetector, FireParams, WaterSegmenter, WaterSegParams (+12 more)

### Community 33 - "http.ts"
Cohesion: 0.09
Nodes (29): ApiError, ApiMode, apiState, isGatewayFailure(), isRetryableStatus(), jsonBody(), markOffline(), RETRY_DELAYS (+21 more)

### Community 34 - "CrowdLayer"
Cohesion: 0.10
Nodes (3): CrowdLayer, PersonType, SpawnType

### Community 35 - "ScenarioWorkspace.vue"
Cohesion: 0.03
Nodes (68): deleteScenarioTemplate(), getScenarioTemplateRevisions(), scenarioExportUrl(), setScenarioResources(), getEmergencyResources(), dispatchScenarioRun(), affectedCounts, businessEvents (+60 more)

### Community 36 - "LLMError"
Cohesion: 0.14
Nodes (14): report(), test_chat_attaches_seeded_event_context(), test_chat_rejects_invalid_history(), test_chat_without_event_context(), fake_chat(), test_llm_status_availability_is_environment_independent(), test_parse_task_rejects_invalid_length(), test_parse_task_route_and_provider_error() (+6 more)

### Community 37 - "EventDetail.vue"
Cohesion: 0.08
Nodes (26): getEventLogs(), assignee, assigneeOptions, busy, confidence, demoDispatch(), dispatchOpen, dispatchTarget (+18 more)

### Community 38 - "AssessmentQueue.vue"
Cohesion: 0.08
Nodes (24): createAssessment(), mergeCandidateEvents(), context, contextLoading, { currentName, load: loadOperator }, distanceMeters(), emit, form (+16 more)

### Community 39 - "routers/geo.py"
Cohesion: 0.09
Nodes (10): get_ctx(), init_data(), patch_spatial_feature(), _write_geojson(), export_graph(), graph(), SpatialFeaturePatch, load_runtime_state() (+2 more)

### Community 40 - "roadLayer.ts"
Cohesion: 0.11
Nodes (20): ellipseInstance(), distance(), hashByte(), isFiniteCoord(), lineLength(), lineMidpoint(), LonLat, resampleLine() (+12 more)

### Community 41 - "TrafficSeriesAnalyzer"
Cohesion: 0.12
Nodes (16): AnalysisResult, network_tpi(), speed_to_tpi(), tpi_level(), TrafficSeriesAnalyzer, VehicleOccupancyAnalyzer, _series(), test_csv_missing_column() (+8 more)

### Community 43 - "武汉智眼首批数据集确定方案_dd680806.md"
Cohesion: 0.07
Nodes (26): 01　火灾与烟雾：D-Fire, 02　航拍车辆：VisDrone2019-DET, 03　建筑灾前灾后：xBD / xView2, 04　获取顺序、登记与验收, 05　武汉本地数据补充, 05　武汉本地数据补充（续）, 05　武汉本地数据补充（续）, 5.1　UAV-OBB：含武汉道路的车辆数据 (+18 more)

### Community 44 - "test_api.py"
Cohesion: 0.09
Nodes (3): test_data_list_stats_upload(), test_events_list_shape_and_order(), test_stats_overview()

### Community 46 - "with"
Cohesion: 0.09
Nodes (25): name, runs-on, steps, run, defaults, name, runs-on, steps (+17 more)

### Community 47 - "城市智眼 API 契约（v1）"
Cohesion: 0.08
Nodes (26): limit(), 0. 通用约定, 10. WebSocket `/api/ws`, 11. 城市智能情景推演, 12. 业务闭环, 13. 公共支撑, 14. 业务链路, 1. 系统 (+18 more)

### Community 48 - "roadGraph.ts"
Cohesion: 0.13
Nodes (11): GraphEdge, GraphLine, GraphPoint, hazardPenalizedCost(), MinHeap, PlannedRoute, pointDistance(), projectOnSegment() (+3 more)

### Community 49 - "CrowdSimulationPanel.vue"
Cohesion: 0.10
Nodes (19): benchmark, busy, clearPeople(), count, dangerRadius, emptyEvacuation, emptyStats, evacuate() (+11 more)

### Community 50 - "numpy"
Cohesion: 0.06
Nodes (43): add_collapse(), add_fire(), add_flood(), add_new_structure(), add_street_lights(), BuildingShape, Corridor, finish() (+35 more)

### Community 51 - "TaskSeriesChart.vue"
Cohesion: 0.12
Nodes (21): metrics, metrics, EXTRA_COLORS, extraKeys, MAIN_NAME, option, props, Series (+13 more)

### Community 52 - "compilerOptions"
Cohesion: 0.09
Nodes (21): compilerOptions, allowImportingTsExtensions, baseUrl, isolatedModules, jsx, lib, module, moduleDetection (+13 more)

### Community 53 - "StatusPanel.vue"
Cohesion: 0.07
Nodes (27): emit, LEVELS, open, props, SEVERITIES, props, rows, total (+19 more)

### Community 54 - "seed.py"
Cohesion: 0.05
Nodes (37): Base, make_engine(), make_session_factory(), AppMeta, AuditLog, EmergencyResource, Event, EventLog (+29 more)

### Community 55 - "LandmarkLayer"
Cohesion: 0.22
Nodes (3): Landmark, LandmarkLayer, LANDMARKS

### Community 56 - "llm.py"
Cohesion: 0.21
Nodes (13): _call_llm(), ChatIn, ChatMessageIn, _distance_m(), _event_data_nature(), _event_view(), llm_status(), _load_event_context() (+5 more)

### Community 58 - "CityEye 城市虚拟人群仿真模块"
Cohesion: 0.09
Nodes (21): 1.1 选型结论, 1.2 坐标系, 1. 技术融合方案, 2.1 人物模型, 2.2 实例化策略, 2. 模块架构, 3. 关键接口, 4.1 单人行为 (+13 more)

### Community 59 - "Settings"
Cohesion: 0.12
Nodes (19): parsed_task(), test_parse_task_retries_one_malformed_model_output(), flaky_parse(), Settings, generate_scenario_report(), HybridReportError, ScenarioReport, main() (+11 more)

### Community 60 - "assess_settlement"
Cohesion: 0.11
Nodes (14): assess_settlement(), ChangeDetector, ChangeParams, SettlementReport, SettlementThresholds, test_accelerating_settlement_is_warning(), test_change_detection_finds_new_structure(), test_change_detection_ignores_illumination() (+6 more)

### Community 61 - "CameraController"
Cohesion: 0.16
Nodes (4): CameraController, wait(), FlyOptions, OrbitOptions

### Community 62 - "tool_runner.py"
Cohesion: 0.15
Nodes (16): get_demo_event(), list_demo_facilities(), 4. Tool Calling, build_input(), main(), ScriptedClient, ScriptedCompletions, test_execute_known_and_unknown_tool() (+8 more)

### Community 64 - "roadLayer.ts"
Cohesion: 0.10
Nodes (15): buildingColor(), BuildingLayer, BuildingRecord, extrude(), frameNumberOf(), HEIGHT_STOPS, nextFrame(), polygonsOf() (+7 more)

### Community 65 - "api/scenario.ts"
Cohesion: 0.12
Nodes (24): compareScenarioRuns(), createScenarioTemplate(), generateScenarioReport(), patchScenarioTemplate(), scenarioRequest(), sendScenarioMessage(), compare(), makeReport() (+16 more)

### Community 66 - "OrderBoard.vue"
Cohesion: 0.04
Nodes (59): assessWorkOrderFeedback(), createWorkOrder(), patchWorkOrder(), uploadWorkOrderFeedback(), useWorkOrderResource(), advance(), ATTACHMENT_ACCEPT, ATTACHMENT_SUFFIXES (+51 more)

### Community 67 - "services/scenario.py"
Cohesion: 0.05
Nodes (51): ScenarioResourceReservation, ScenarioSession, ScenarioVersion, _apply_demo_defaults(), _new_id(), _now(), ScenarioService, _timestamp() (+43 more)

### Community 68 - "cityeye"
Cohesion: 0.11
Nodes (17): build, container_name, environment, image, ports, restart, volumes, CITYEYE_DEMO_MODE (+9 more)

### Community 69 - "Monitoring.vue"
Cohesion: 0.10
Nodes (19): nowText(), ageSec, buildings, cityTpi, devicesOnline, devicesTotal, history, info (+11 more)

### Community 70 - "SystemManagement.vue"
Cohesion: 0.04
Nodes (67): getSupportAccounts(), markAllNotificationsRead(), markNotificationRead(), patchResponsibilityGrid(), patchRuntimeConfig(), accounts, currentId, load() (+59 more)

### Community 71 - "pytest"
Cohesion: 0.18
Nodes (13): AnalysisFinding, CityEventReport, EventOverview, generate_report(), load_report_prompt(), ReportError, RiskAssessment, FakeClient (+5 more)

### Community 72 - "规格：CityEye 前端渐进式改进（第 1 批）"
Cohesion: 0.12
Nodes (15): resetFilters(), 1. 现状结论（已核实）, 2. 改动清单, 3. 明确不做（本轮）, 4. 验证计划, 5. 风险与回退, R1 表格响应式列断点修正, R2 事件表格空状态增加操作入口 (+7 more)

### Community 73 - "routers/workflow.py"
Cohesion: 0.09
Nodes (44): AssessmentRecord, DataAsset, MonitoringRun, MonitoringTask, ReviewRecord, ScenarioRunRecord, WorkOrder, asset_to_dict() (+36 more)

### Community 74 - "城市智眼 · 算法说明"
Cohesion: 0.11
Nodes (16): cityeye_algo —— 城市智眼算法包, 使用, 测试, 1. 火灾 · FlameNet-Lite（`fire.py`）, 2.1 TrafficPulse · 时序路况（`traffic.py`）, 2.2 RoadOcc · 航拍路面车辆占有率, 2. 交通, 3.1 SettleWatch · 沉降监测（`building.py`） (+8 more)

### Community 75 - "EventDrawer.vue"
Cohesion: 0.07
Nodes (26): ACTION_META, actionLabel(), ASSIGNEES, copyCoord(), currentId, emit, event, fetched (+18 more)

### Community 76 - "城市智眼 · CityEye"
Cohesion: 0.12
Nodes (17): 🔌 API 一览, ✨ 亮点, 🕸️ 代码图谱, 🗺️ 功能导览, 城市智眼 · CityEye, 🚀 快速开始, 📚 数据来源与致谢, 方式一：Docker（推荐，一条命令） (+9 more)

### Community 77 - "test_fire.py"
Cohesion: 0.19
Nodes (7): det(), test_plain_city_not_detected(), test_procedural_flame_detected(), test_red_roofs_and_orange_car_not_detected(), test_samples_negative(), test_samples_positive(), test_smoke_scored_on_sample_with_plume()

### Community 78 - "algorithm/tests/conftest.py"
Cohesion: 0.19
Nodes (5): city_background(), paint_flame(), rng(), sample(), save()

### Community 79 - "types/scenario.ts"
Cohesion: 0.18
Nodes (9): PREVIOUS_EDGE, RISK_COLOR, ScenarioLayer, WATER_BODY, WATER_EDGE, ScenarioFrame, ScenarioRisk, ScenarioType (+1 more)

### Community 80 - "CityEye 大模型模块压缩交接"
Cohesion: 0.14
Nodes (13): 1. DeepSeek API, 2. CityEye 系统提示词, 3. 自然语言任务解析, 5. 结构化报告, CityEye 大模型模块压缩交接, Git 状态, 下一步, 会话目标 (+5 more)

### Community 81 - "build_geo.py"
Cohesion: 0.17
Nodes (19): build_buildings(), build_pois(), build_roads(), length(), classify(), clip_chain(), dist_m(), district_of() (+11 more)

### Community 84 - "devDependencies"
Cohesion: 0.17
Nodes (12): devDependencies, eslint@^9.39.5, prettier@^3.9.10, @types/three@^0.187.0, typescript@~5.6.3, vitest@^2.1.9, vue-tsc@^2.1.10, eslint (+4 more)

### Community 85 - "request"
Cohesion: 0.13
Nodes (30): getBuildingDistricts(), getBuildings(), getFineBuildings(), getPois(), getRoads(), getSpatialFeature(), loadDistrictManifest(), patchSpatialFeature() (+22 more)

### Community 86 - "CityEvent"
Cohesion: 0.15
Nodes (26): 2. 事件, `CityEvent`, `EventLog`, `GET /api/events/{id}` → `CityEvent`（404 不存在）, `GET /api/events/{id}/logs` → `EventLog[]`（按时间正序）, `PATCH /api/events/{id}`, `POST /api/events`（人工上报 / 市民上报）, getEvent() (+18 more)

### Community 87 - "AssistantChatPanel.vue"
Cohesion: 0.11
Nodes (16): chatWithAssistant(), AnswerBlock, busy, canSend, dataType, emit, error, input (+8 more)

### Community 89 - "dependencies"
Cohesion: 0.20
Nodes (10): dependencies, cesium@1.125.0, echarts@^5.6.0, element-plus@^2.9.0, @element-plus/icons-vue@^2.3.1, three@^0.187.0, vue@^3.5.13, vue-router@^4.5.0 (+2 more)

### Community 90 - "create_app"
Cohesion: 0.18
Nodes (4): create_app(), _on_validation(), __getattr__(), _validation_message()

### Community 91 - "scripts"
Cohesion: 0.18
Nodes (11): scripts, build, dev, format, format:check, lint, lint:fix, preview (+3 more)

### Community 92 - "CityEye 大模型模块"
Cohesion: 0.17
Nodes (11): CityEye 大模型模块, Tool Calling 验证, 城市治理问答, 安装, 当前范围, 测试, 系统提示词测试, 结构化研判报告 (+3 more)

### Community 93 - "5. 数据资产"
Cohesion: 0.25
Nodes (8): 5. 数据资产, `DataItem`, `GET /api/data` → `DataItem[]`（按 time 倒序）, `GET /api/data/{id}/validations` → `DataValidation[]`, `GET /api/data/stats` → 总数、总容量、类型分布、`analyzable` 与 `by_analysis_status`, `POST /api/data/{id}/auto-check` → 自动预检记录, `POST /api/data/{id}/validations`, `POST /api/data/upload`（multipart：`files` 多个，`type` 可选）→ `DataItem[]`

### Community 94 - "CityEye 项目交接说明"
Cohesion: 0.25
Nodes (7): 1. 接手后先做什么, 2. 已纳入云端的关键数据, 3. 数据再生成顺序, 4. 当前功能边界, 5. 验证, 6. 不应提交的内容, CityEye 项目交接说明

### Community 95 - "TaskQueue.vue"
Cohesion: 0.04
Nodes (52): createMonitoringTask(), createTaskTemplate(), deleteTaskTemplate(), executeMonitoringTask(), getTaskTemplateRevisions(), getTaskTemplates(), patchMonitoringTask(), patchTaskTemplate() (+44 more)

### Community 97 - "回答格式"
Cohesion: 0.18
Nodes (10): CityEye 城市治理助手, 信息使用规则, 信息缺口, 分析, 回答格式, 安全规则, 已知信息, 建议 (+2 more)

### Community 98 - "EventCreateDialog.vue"
Cohesion: 0.12
Nodes (20): createEvent(), bbox, center, emit, FALLBACK_CENTER, form, formRef, FormState (+12 more)

### Community 99 - "compilerOptions"
Cohesion: 0.20
Nodes (9): compilerOptions, allowSyntheticDefaultImports, composite, module, moduleResolution, outDir, skipLibCheck, strict (+1 more)

### Community 100 - "loadRun"
Cohesion: 0.15
Nodes (17): createScenarioSession(), runCurrentScenarioVariants(), applyPeople(), demoStart(), demoStop(), emit, ensureLayer(), ensureSession() (+9 more)

### Community 101 - "系统架构"
Cohesion: 0.25
Nodes (8): 1. 总体架构, 2.1 实时事件闭环, 2.2 AI 分析任务, 2. 关键数据流, 3. 三维场景设计, 4. 运行模式, 5. 扩展点, 系统架构

### Community 102 - "manifest.json"
Cohesion: 0.33
Nodes (5): bbox, districts, overview_count, overview_url, source

### Community 103 - "城市应急演练"
Cohesion: 0.25
Nodes (7): Demo 演示增强, 事件种子, 交互闭环, 入口与实现, 城市应急演练, 定位, 数据边界

### Community 104 - "CityEye 界面设计说明"
Cohesion: 0.22
Nodes (8): CityEye 界面设计说明, 各页面问题, 应急演练页, 方向, 本轮调整, 真实城市视图中的事件层级, 设计边界, 验证

### Community 105 - "building.ts"
Cohesion: 0.07
Nodes (33): grade, levelMeta, LEVELS, marker, option, props, gauge, groups (+25 more)

### Community 106 - "AIAnalysis.vue"
Cohesion: 0.07
Nodes (46): 6. AI 分析任务, `AnalysisTask`, `GET /api/samples?type=fire` → 示例数据, `GET /api/tasks` → `AnalysisTask[]`（按创建时间倒序）, `GET /api/tasks/{id}` → `AnalysisTask`, `POST /api/tasks`（JSON，兼容原型）, `POST /api/tasks/upload`（multipart）, createTask() (+38 more)

### Community 107 - "vite.config.ts"
Cohesion: 0.20
Nodes (7): vite-plugin-static-copy@^2.2.0, vite@^5.4.11, @vitejs/plugin-vue@^5.2.1, srcDir, vite, vite-plugin-static-copy, @vitejs/plugin-vue

### Community 108 - "eventLayer.ts"
Cohesion: 0.06
Nodes (33): priorityEvents, aggregateEventsByDistrict(), now, Alert, ALWAYS, beamInstance(), circlePositions(), clusterBadge() (+25 more)

### Community 109 - "argparse"
Cohesion: 0.14
Nodes (15): distance_m(), district_in_text(), main(), merge(), search(), valid_name(), main(), parse_bbox() (+7 more)

### Community 112 - ".prettierrc.json"
Cohesion: 0.29
Nodes (6): arrowParens, endOfLine, printWidth, semi, singleQuote, trailingComma

### Community 113 - "数据库设计"
Cohesion: 0.50
Nodes (3): ER 图, 数据库设计, 种子数据（`backend/app/seed.py`）

### Community 116 - "数据集目录"
Cohesion: 0.50
Nodes (3): 当前数据, 数据集目录, 目录约定

### Community 131 - "package.json"
Cohesion: 0.25
Nodes (7): description, name, overrides, @cesium/widgets, private, type, version

### Community 132 - "TrafficState"
Cohesion: 0.23
Nodes (3): congestion_curve(), RoadLive, TrafficState

### Community 133 - "pages/format.ts"
Cohesion: 0.27
Nodes (13): timeCost, fmtBytes(), fmtDuration(), fmtNum(), hexA(), isCsvUrl(), p2(), parseTs() (+5 more)

### Community 135 - "cesium"
Cohesion: 0.09
Nodes (20): Region, AmbientEffects, beamAppearance(), buildingAppearance(), buildingVS(), encode(), f(), LINE_VERTEX_FORMAT (+12 more)

### Community 136 - "export_snapshot.py"
Cohesion: 0.19
Nodes (4): test_building_spatial_properties_can_be_maintained(), dump(), main(), main()

### Community 139 - "eslint.config.js"
Cohesion: 0.29
Nodes (6): eslint-config-prettier@^9.1.2, eslint-plugin-vue@^9.33.0, typescript-eslint@^8.72.0, eslint-config-prettier, eslint-plugin-vue, typescript-eslint

### Community 140 - "build_wuhan_buildings.py"
Cohesion: 0.28
Nodes (9): bounds(), centroid(), compact_json(), district_of(), grid_of(), load_district_segments(), main(), point_in_segments() (+1 more)

### Community 141 - "TaskHistory.vue"
Cohesion: 0.18
Nodes (9): emit, onRowClick(), page, props, rows, showAlgo, showProg, vw (+1 more)

### Community 142 - "config.py"
Cohesion: 0.26
Nodes (5): _bool(), _float(), _path(), Settings, main()

### Community 144 - "backend/tests/conftest.py"
Cohesion: 0.23
Nodes (4): client(), ctx(), tmp_root(), wait_task()

### Community 145 - "EventTable.vue"
Cohesion: 0.09
Nodes (20): activeCount, activeEvents, emit, fresh, list, now, props, sorted (+12 more)

### Community 146 - "AppHeader.vue"
Cohesion: 0.20
Nodes (11): city, conn, { connected }, date, demoTip, everConnected, { info, region, demoMode, load }, now (+3 more)

### Community 147 - "llm_module/__init__.py"
Cohesion: 0.14
Nodes (11): test_select(), test_select_errors(), test_validate_checks_csv_header(), answer_chat(), _build_prompt(), ChatTurn, FakeClient, FakeCompletions (+3 more)

### Community 153 - "record_http_audit"
Cohesion: 0.24
Nodes (8): _audit_writes(), account_to_dict(), audit_action(), audit_entity(), audit_to_dict(), capture_audit_entity(), _json_value(), record_http_audit()

### Community 160 - "城市智眼业务闭环重构：第一阶段"
Cohesion: 0.25
Nodes (8): API, 公共支撑, 内涝示例闭环, 城市智眼业务闭环重构：第一阶段, 尚未完成, 数据资源画像, 状态机, 迁移与回滚

### Community 170 - "3. 城市三维对象"
Cohesion: 0.29
Nodes (7): 3. 城市三维对象, `GET /api/buildings/fine?district=武昌区` → GeoJSON `FeatureCollection<Polygon>`, `GET /api/buildings` → GeoJSON `FeatureCollection<Polygon>`, `GET /api/buildings/{id}` → 建筑详情, `GET /api/pois` → `[{ id, name, kind: "hospital"|"fire_station"|"police"|"school", longitude, latitude }]`, `GET /api/roads` → GeoJSON `FeatureCollection<LineString>`, `GET/PATCH /api/spatial/{entity_type}/{id}`

## Knowledge Gaps
- **48 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Task` connect `services/tasks.py` to `schemas.py`, `routers/geo.py`, `routers/workflow.py`, `城市智眼 API 契约（v1）`, `seed.py`, `llm.py`, `_EventBuilder`, `AppContext`, `Simulator`?**
  _High betweenness centrality (0.194) - this node is a cross-community bridge._
- **Are the 50 inferred relationships involving `AppContext` (e.g. with `GeoRepository` and `create_app()`) actually correct?**
  _`AppContext` has 50 INFERRED edges - model-reasoned connections that need verification._
- **Should `ReviewBoard.vue` be split into smaller, more focused modules?**
  _Cohesion score 0.06153846153846154 - nodes in this community are weakly interconnected._
- **Why does ``MonitoringRun`` connect `城市智眼 API 契约（v1）` to `services/tasks.py`?**
  _High betweenness centrality (0.189) - this node is a cross-community bridge._
- **Should `EventDrawer.vue` be split into smaller, more focused modules?**
  _Cohesion score 0.08620689655172414 - nodes in this community are weakly interconnected._
- **Should `WorkflowPulse.vue` be split into smaller, more focused modules?**
  _Cohesion score 0.06028368794326241 - nodes in this community are weakly interconnected._
- **Should `@element-plus/icons-vue` be split into smaller, more focused modules?**
  _Cohesion score 0.06606606606606606 - nodes in this community are weakly interconnected._
