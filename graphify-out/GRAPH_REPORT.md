# Graph Report - CityEye  (2026-11-11)

## Corpus Check
- 324 files · ~694,836 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 42 file(s) not represented in the graph (top: .csv 14, .geojson 11, (none) 9)

## Summary
- 3967 nodes · 9627 edges · 163 communities (118 shown, 45 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 655 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `4ac92c0`
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
- http.ts
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
- EventType
- download_satellite_basemap.py
- services/events.py
- steps
- crowdLayer.ts
- cityeye_algo/traffic.py
- WorkflowWorkspace.vue
- CrowdLayer
- ScenarioWorkspace.vue
- LLMError
- EventDetail.vue
- AssessmentQueue.vue
- DataTypeDistribution.vue
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
- types/event.ts
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
- data.py
- OrderBoard.vue
- services/scenario.py
- cityeye
- eventLayer.ts
- SystemManagement.vue
- pytest
- 规格：CityEye 前端渐进式改进（第 1 批）
- routers/workflow.py
- 城市智眼 · 算法说明
- EventDrawer.vue
- 城市智眼 · CityEye
- test_fire.py
- sys
- types/scenario.ts
- CityEye 大模型模块压缩交接
- build_geo.py
- README.md
- test_workflow_api.py
- devDependencies
- request
- useDemoTour
- scene/types.ts
- SourceState
- dependencies
- routers/support.py
- scripts
- CityEye 大模型模块
- 5. 数据资产
- CityEye 项目交接说明
- TaskQueue.vue
- 回答格式
- EventCreateDialog.vue
- compilerOptions
- 12. 业务闭环
- 系统架构
- manifest.json
- 城市应急演练
- CityEye 界面设计说明
- TrafficPanel.vue
- AIAnalysis.vue
- vite.config.ts
- EventLayer
- argparse
- .prettierrc.json
- 数据库设计
- 数据集目录
- dev.sh
- manifests/README.md
- basemap/README.md
- demo.sh
- package.json
- converse
- useTaskRunner.ts
- cesium
- shutil
- RealtimeHub
- eslint.config.js
- export_snapshot.py
- DistrictRank.vue
- config.py
- backend/tests/conftest.py
- EventTable.vue
- AppHeader.vue
- llm_module/__init__.py
- AnalysisTask
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
10. `errMsg()` - 40 edges

## Surprising Connections (you probably didn't know these)
- `API` --references--> `task_template_revisions()`  [INFERRED]
  docs/workflow-refactor.md → backend/app/routers/workflow.py
- ``DataItem`` --references--> `DataItem`  [INFERRED]
  docs/api.md → frontend/src/types/api.ts
- ``AnalysisTask`` --references--> `AnalysisTask`  [INFERRED]
  docs/api.md → frontend/src/types/api.ts
- ``GET /api/tasks/{id}` → `AnalysisTask`` --references--> `AnalysisTask`  [INFERRED]
  docs/api.md → frontend/src/types/api.ts
- ``POST /api/tasks/upload`（multipart）` --references--> `create_event()`  [INFERRED]
  docs/api.md → backend/app/services/events.py

## Import Cycles
- 3-file cycle: `algorithm/cityeye_algo/__init__.py -> algorithm/cityeye_algo/registry.py -> algorithm/cityeye_algo/building.py -> algorithm/cityeye_algo/__init__.py`
- 3-file cycle: `algorithm/cityeye_algo/__init__.py -> algorithm/cityeye_algo/registry.py -> algorithm/cityeye_algo/fire.py -> algorithm/cityeye_algo/__init__.py`
- 3-file cycle: `algorithm/cityeye_algo/__init__.py -> algorithm/cityeye_algo/registry.py -> algorithm/cityeye_algo/flood.py -> algorithm/cityeye_algo/__init__.py`
- 3-file cycle: `algorithm/cityeye_algo/__init__.py -> algorithm/cityeye_algo/registry.py -> algorithm/cityeye_algo/traffic.py -> algorithm/cityeye_algo/__init__.py`

## Communities (163 total, 45 thin omitted)

### Community 0 - "ReviewBoard.vue"
Cohesion: 0.07
Nodes (33): applyReviewToTemplate(), createReview(), getReviewCases(), getReviewDraft(), reviewExportUrl(), updateReview(), applyBusy, applyRule() (+25 more)

### Community 1 - "EventDrawer.vue"
Cohesion: 0.08
Nodes (38): evidence, evidence, activeAnn, annotated, color, confPct, detected, detections (+30 more)

### Community 2 - "WorkflowPulse.vue"
Cohesion: 0.13
Nodes (24): getDataList(), getDataStats(), qs(), getAssessmentContext(), getAssessments(), getMonitoringRuns(), getMonitoringTasks(), getReviews() (+16 more)

### Community 3 - "@element-plus/icons-vue"
Cohesion: 0.09
Nodes (19): isDrill, route, { sidebarCollapsed }, aiItems, { calm, demoEventIds }, displayActive, mobileMoreOpen, moreItems (+11 more)

### Community 5 - "Dashboard.vue"
Cohesion: 0.04
Nodes (49): resetDemo(), askAssistantDemo(), assistantDemoQuestion, assistantOpen, assistantRef, autoTrack, basemap, { calm: calmBaseline, demoEventIds, enterCalmBaseline, revealAnomalies, setDemoEventIds } (+41 more)

### Community 6 - "EmergencyDrill.vue"
Cohesion: 0.05
Nodes (59): HAZARD_PROFILES, HazardProfile, hazardProfile(), hazardRadiusAt(), requiresPedestrianEvacuation(), smoothstep(), accent, actionText (+51 more)

### Community 7 - "schemas.py"
Cohesion: 0.06
Nodes (73): AccountOut, AlgorithmInfoOut, AlgorithmOut, AnalysisTaskOut, AssessmentContextOut, AssessmentCreate, AssessmentOut, AuditLogOut (+65 more)

### Community 8 - "api/workflow.ts"
Cohesion: 0.11
Nodes (27): AssessmentCreate, CandidateMergeResult, MonitoringExecuteResult, MonitoringRunStatus, MonitoringTaskCreate, MonitoringTaskStatus, MonitoringTaskTemplate, MonitoringTaskTemplateCreate (+19 more)

### Community 9 - "BuildingSafetyPanel.vue"
Cohesion: 0.06
Nodes (28): getBuilding(), bProps, CATEGORY, chart, counts, detail, detailLoading, mon (+20 more)

### Community 10 - "CesiumViewer.vue"
Cohesion: 0.05
Nodes (56): active, alarmBuildingIds(), api, bindInteraction(), bindRenderErrorRecovery(), chooseDistrict(), closePanels(), containerRef (+48 more)

### Community 12 - "AIAnalysis.vue"
Cohesion: 0.06
Nodes (46): findRiskBuilding(), allowedExt, createEvent, emit, fileList, latitude, loadingSamples, longitude (+38 more)

### Community 13 - "InputError"
Cohesion: 0.11
Nodes (12): InputError, damped_holt(), fmt_t(), median_step_minutes(), moving_average(), parse_times(), read_header(), read_table() (+4 more)

### Community 14 - "numpy"
Cohesion: 0.06
Nodes (34): AnalysisResult, ChangeDetector, WaterSegmenter, WaterSegParams, blur(), box_mean(), box_sum(), closing() (+26 more)

### Community 15 - "http.ts"
Cohesion: 0.04
Nodes (61): ApiError, ApiMode, apiState, isGatewayFailure(), isRetryableStatus(), markOffline(), RETRY_DELAYS, retryConnection() (+53 more)

### Community 16 - "EventCenter.vue"
Cohesion: 0.05
Nodes (42): todayPrefix(), activeOnly, applyQuery(), createVisible, diffFlash(), drawerId, drawerOpen, FILTER_KEYS (+34 more)

### Community 17 - "scene/types.ts"
Cohesion: 0.21
Nodes (9): BasemapController, GLOBE_BASE_COLOR, STYLE, BasemapConfig, BasemapKey, BASEMAPS, CESIUM_ION_TOKEN, DEFAULT_BASEMAP (+1 more)

### Community 18 - "useOverview.ts"
Cohesion: 0.12
Nodes (28): nowString(), metrics, { calm, demoEventIds }, { connected, lastMessageAt }, displayStats, lastUpdate, MODE_LABEL, pad() (+20 more)

### Community 19 - "WaterLevelAnalyzer"
Cohesion: 0.24
Nodes (8): FloodThresholds, WaterLevelAnalyzer, _storm(), test_csv_samples(), test_light_rain_not_detected(), test_rainstorm_detected_with_lag(), test_rising_series_forecast_without_rain(), test_threshold_levels()

### Community 20 - "ask"
Cohesion: 0.17
Nodes (11): main(), ask(), _client(), main(), FakeClient, FakeCompletions, settings(), test_ask_includes_system_prompt() (+3 more)

### Community 21 - "DataManagement.vue"
Cohesion: 0.03
Nodes (71): autoCheckDataAsset(), getDataValidations(), uploadData(), validateDataAsset(), getEmergencyResources(), patchEmergencyResource(), openResources(), openResource() (+63 more)

### Community 22 - "services/tasks.py"
Cohesion: 0.07
Nodes (28): bad_request(), Task, _require_demo(), reset(), scenario(), _check_type(), _parse_float(), post_task() (+20 more)

### Community 23 - "registry.py"
Cohesion: 0.13
Nodes (7): Analyzer, _clean_metric(), algorithms(), file_kind(), run(), _run_batch(), validate()

### Community 24 - "icons.ts"
Cohesion: 0.19
Nodes (6): poiIcon(), roundRect(), PoiLayer, SCALE_BY_DISTANCE, Poi, POI_META

### Community 25 - "Monitoring.vue"
Cohesion: 0.04
Nodes (48): props, shown, props, rate, ringOffset, rows, sources, totals (+40 more)

### Community 26 - "AppContext"
Cohesion: 0.05
Nodes (89): select(), AppContext, not_found(), ScenarioTemplate, data_stats(), list_data_validations(), get_event(), get_logs() (+81 more)

### Community 27 - "EventType"
Cohesion: 0.06
Nodes (40): 2. 事件, `CityEvent`, `EventLog`, `GET /api/events/{id}` → `CityEvent`（404 不存在）, `GET /api/events/{id}/logs` → `EventLog[]`（按时间正序）, `PATCH /api/events/{id}`, `POST /api/events`（人工上报 / 市民上报）, activeCount (+32 more)

### Community 28 - "download_satellite_basemap.py"
Cohesion: 0.17
Nodes (11): BBox, build_parser(), crop_window(), download_tile(), lat_to_tile_y(), lon_to_tile_x(), main(), parse_bbox() (+3 more)

### Community 29 - "services/events.py"
Cohesion: 0.06
Nodes (21): lifespan(), Event, EventLog, patch_event(), post_event(), merge_candidates(), EventPatch, add_log() (+13 more)

### Community 30 - "steps"
Cohesion: 0.05
Nodes (39): defaults, runs-on, steps, concurrency, cancel-in-progress, group, run, environment (+31 more)

### Community 31 - "crowdLayer.ts"
Cohesion: 0.09
Nodes (28): CrowdPerson, EXIT_CAPACITIES, EXIT_LABELS, HazardState, installGaitShader(), makeStickFigureGeometry(), makeVehicleGeometry(), RoadPath (+20 more)

### Community 32 - "cityeye_algo/traffic.py"
Cohesion: 0.10
Nodes (17): AlgorithmMeta, Artifact, clamp01(), Detection, ChangeParams, SettlementAnalyzer, annotate_image(), Band (+9 more)

### Community 33 - "WorkflowWorkspace.vue"
Cohesion: 0.08
Nodes (21): MonitoringTask, ReviewRecord, WorkOrder, activeOrders, assessments, current, error, eventStore (+13 more)

### Community 34 - "CrowdLayer"
Cohesion: 0.10
Nodes (3): CrowdLayer, PersonType, SpawnType

### Community 35 - "ScenarioWorkspace.vue"
Cohesion: 0.03
Nodes (104): compareScenarioRuns(), createScenarioSession(), createScenarioTemplate(), deleteScenarioTemplate(), generateScenarioReport(), getScenarioTemplateRevisions(), patchScenarioTemplate(), runCurrentScenarioVariants() (+96 more)

### Community 36 - "LLMError"
Cohesion: 0.13
Nodes (17): parsed_task(), report(), test_chat_attaches_seeded_event_context(), test_chat_rejects_invalid_history(), test_chat_without_event_context(), fake_chat(), test_llm_status_availability_is_environment_independent(), test_parse_task_rejects_invalid_length() (+9 more)

### Community 37 - "EventDetail.vue"
Cohesion: 0.09
Nodes (24): assignee, assigneeOptions, busy, confidence, demoDispatch(), dispatchOpen, dispatchTarget, emit (+16 more)

### Community 38 - "AssessmentQueue.vue"
Cohesion: 0.08
Nodes (26): createAssessment(), mergeCandidateEvents(), context, contextLoading, { currentName, load: loadOperator }, distanceMeters(), emit, form (+18 more)

### Community 39 - "DataTypeDistribution.vue"
Cohesion: 0.17
Nodes (13): option, props, statuses, emit, option, props, total, DATA_STATUS_META (+5 more)

### Community 40 - "roadLayer.ts"
Cohesion: 0.09
Nodes (21): cleanRing(), distance(), isFiniteCoord(), lineLength(), lineMidpoint(), LonLat, resampleLine(), ringAreaM2() (+13 more)

### Community 41 - "TrafficSeriesAnalyzer"
Cohesion: 0.16
Nodes (14): network_tpi(), speed_to_tpi(), tpi_level(), TrafficSeriesAnalyzer, _series(), test_csv_missing_column(), test_free_flow_series_not_congested(), test_sample_csv_has_two_peaks() (+6 more)

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
Cohesion: 0.10
Nodes (19): limit(), 0. 通用约定, 11. 城市智能情景推演, 13. 公共支撑, 14. 业务链路, 1. 系统, 4. 统计, 7. 监测数据源 (+11 more)

### Community 48 - "roadGraph.ts"
Cohesion: 0.13
Nodes (10): GraphEdge, GraphLine, GraphPoint, hazardPenalizedCost(), MinHeap, PlannedRoute, pointDistance(), projectOnSegment() (+2 more)

### Community 49 - "CrowdSimulationPanel.vue"
Cohesion: 0.10
Nodes (19): benchmark, busy, clearPeople(), count, dangerRadius, emptyEvacuation, emptyStats, evacuate() (+11 more)

### Community 50 - "numpy"
Cohesion: 0.07
Nodes (43): add_collapse(), add_fire(), add_flood(), add_new_structure(), add_street_lights(), BuildingShape, Corridor, finish() (+35 more)

### Community 51 - "TaskSeriesChart.vue"
Cohesion: 0.10
Nodes (25): BASE, chart, el, props, metrics, metrics, EXTRA_COLORS, extraKeys (+17 more)

### Community 52 - "compilerOptions"
Cohesion: 0.09
Nodes (21): compilerOptions, allowImportingTsExtensions, baseUrl, isolatedModules, jsx, lib, module, moduleDetection (+13 more)

### Community 53 - "types/event.ts"
Cohesion: 0.04
Nodes (56): grade, levelMeta, LEVELS, marker, option, props, emit, LEVELS (+48 more)

### Community 54 - "seed.py"
Cohesion: 0.06
Nodes (35): Base, make_engine(), make_session_factory(), init_data(), AppMeta, AssessmentRecord, AuditLog, DataAsset (+27 more)

### Community 55 - "LandmarkLayer"
Cohesion: 0.22
Nodes (3): Landmark, LandmarkLayer, LANDMARKS

### Community 56 - "llm.py"
Cohesion: 0.13
Nodes (16): get_ctx(), _call_llm(), ChatIn, ChatMessageIn, _distance_m(), _event_data_nature(), _event_view(), llm_status() (+8 more)

### Community 58 - "CityEye 城市虚拟人群仿真模块"
Cohesion: 0.09
Nodes (21): 1.1 选型结论, 1.2 坐标系, 1. 技术融合方案, 2.1 人物模型, 2.2 实例化策略, 2. 模块架构, 3. 关键接口, 4.1 单人行为 (+13 more)

### Community 59 - "Settings"
Cohesion: 0.11
Nodes (18): test_parse_task_retries_one_malformed_model_output(), flaky_parse(), Settings, generate_scenario_report(), HybridReportError, ScenarioReport, main(), _decode_json() (+10 more)

### Community 60 - "assess_settlement"
Cohesion: 0.13
Nodes (12): assess_settlement(), SettlementReport, SettlementThresholds, test_accelerating_settlement_is_warning(), test_change_detection_finds_new_structure(), test_change_detection_ignores_illumination(), test_fast_settlement_is_warning(), test_flat_series_is_normal() (+4 more)

### Community 61 - "CameraController"
Cohesion: 0.15
Nodes (5): CameraController, wait(), FlyOptions, OrbitOptions, DEFAULT_REGION

### Community 62 - "tool_runner.py"
Cohesion: 0.15
Nodes (16): get_demo_event(), list_demo_facilities(), 4. Tool Calling, build_input(), main(), ScriptedClient, ScriptedCompletions, test_execute_known_and_unknown_tool() (+8 more)

### Community 63 - "GeoRepository"
Cohesion: 0.08
Nodes (7): base_road_name(), GeoRepository, is_generic_name(), Road, congestion_curve(), RoadLive, TrafficState

### Community 64 - "roadLayer.ts"
Cohesion: 0.09
Nodes (17): buildingColor(), BuildingLayer, BuildingRecord, extrude(), frameNumberOf(), HEIGHT_STOPS, nextFrame(), polygonsOf() (+9 more)

### Community 65 - "data.py"
Cohesion: 0.17
Nodes (11): DataValidationRecord, asset_to_dict(), auto_check_data_asset(), list_data(), upload_data(), validate_data_asset(), validation_to_dict(), DataValidationCreate (+3 more)

### Community 66 - "OrderBoard.vue"
Cohesion: 0.04
Nodes (58): assessWorkOrderFeedback(), createWorkOrder(), patchWorkOrder(), uploadWorkOrderFeedback(), useWorkOrderResource(), advance(), ATTACHMENT_ACCEPT, ATTACHMENT_SUFFIXES (+50 more)

### Community 67 - "services/scenario.py"
Cohesion: 0.05
Nodes (51): ScenarioResourceReservation, ScenarioSession, ScenarioVersion, _apply_demo_defaults(), _new_id(), _now(), ScenarioService, _timestamp() (+43 more)

### Community 68 - "cityeye"
Cohesion: 0.11
Nodes (17): build, container_name, environment, image, ports, restart, volumes, CITYEYE_DEMO_MODE (+9 more)

### Community 69 - "eventLayer.ts"
Cohesion: 0.13
Nodes (19): Alert, ALWAYS, circlePositions(), clusterBadge(), clusterOutlineInstance(), ellipseInstance(), Item, LABEL_BG (+11 more)

### Community 70 - "SystemManagement.vue"
Cohesion: 0.04
Nodes (67): markAllNotificationsRead(), markNotificationRead(), patchResponsibilityGrid(), patchRuntimeConfig(), accounts, currentId, load(), loaded (+59 more)

### Community 71 - "pytest"
Cohesion: 0.12
Nodes (15): test_select(), test_select_errors(), test_validate_checks_csv_header(), AnalysisFinding, EventOverview, generate_report(), load_report_prompt(), ReportError (+7 more)

### Community 72 - "规格：CityEye 前端渐进式改进（第 1 批）"
Cohesion: 0.12
Nodes (15): resetFilters(), 1. 现状结论（已核实）, 2. 改动清单, 3. 明确不做（本轮）, 4. 验证计划, 5. 风险与回退, R1 表格响应式列断点修正, R2 事件表格空状态增加操作入口 (+7 more)

### Community 73 - "routers/workflow.py"
Cohesion: 0.11
Nodes (35): MonitoringTask, health(), patch_review(), patch_work_order(), revision_to_dict(), ws_endpoint(), ScenarioActionIn, next_id() (+27 more)

### Community 74 - "城市智眼 · 算法说明"
Cohesion: 0.15
Nodes (13): 1. 火灾 · FlameNet-Lite（`fire.py`）, 2.1 TrafficPulse · 时序路况（`traffic.py`）, 2.2 RoadOcc · 航拍路面车辆占有率, 2. 交通, 3.1 SettleWatch · 沉降监测（`building.py`）, 3.2 ChangeScope · 前后时相变化检测, 3. 建筑, 4.1 AquaLevel · 积水监测时序（`flood.py`） (+5 more)

### Community 75 - "EventDrawer.vue"
Cohesion: 0.06
Nodes (47): EventQuery, getEvent(), getEventLogs(), getEvents(), patchEvent(), snapshotEvents(), loadLogs(), ACTION_META (+39 more)

### Community 76 - "城市智眼 · CityEye"
Cohesion: 0.12
Nodes (17): 🔌 API 一览, ✨ 亮点, 🕸️ 代码图谱, 🗺️ 功能导览, 城市智眼 · CityEye, 🚀 快速开始, 📚 数据来源与致谢, 方式一：Docker（推荐，一条命令） (+9 more)

### Community 77 - "test_fire.py"
Cohesion: 0.16
Nodes (9): FireDetector, FireParams, det(), test_plain_city_not_detected(), test_procedural_flame_detected(), test_red_roofs_and_orange_car_not_detected(), test_samples_negative(), test_samples_positive() (+1 more)

### Community 78 - "sys"
Cohesion: 0.09
Nodes (5): city_background(), paint_flame(), rng(), sample(), save()

### Community 79 - "types/scenario.ts"
Cohesion: 0.17
Nodes (10): PREVIOUS_EDGE, RISK_COLOR, ScenarioLayer, WATER_BODY, WATER_EDGE, RoadCollection, ScenarioFrame, ScenarioRisk (+2 more)

### Community 80 - "CityEye 大模型模块压缩交接"
Cohesion: 0.14
Nodes (13): 1. DeepSeek API, 2. CityEye 系统提示词, 3. 自然语言任务解析, 5. 结构化报告, CityEye 大模型模块压缩交接, Git 状态, 下一步, 会话目标 (+5 more)

### Community 81 - "build_geo.py"
Cohesion: 0.17
Nodes (19): build_buildings(), build_pois(), build_roads(), length(), classify(), clip_chain(), dist_m(), district_of() (+11 more)

### Community 82 - "README.md"
Cohesion: 0.18
Nodes (5): cityeye_algo —— 城市智眼算法包, 使用, 测试, 5 分钟路演脚本, 演示备忘

### Community 84 - "devDependencies"
Cohesion: 0.17
Nodes (12): devDependencies, eslint@^9.39.5, prettier@^3.9.10, @types/three@^0.187.0, typescript@~5.6.3, vitest@^2.1.9, vue-tsc@^2.1.10, eslint (+4 more)

### Community 85 - "request"
Cohesion: 0.06
Nodes (57): getBuildingDistricts(), getBuildings(), getFineBuildings(), getPois(), getRoads(), getSpatialFeature(), loadDistrictManifest(), patchSpatialFeature() (+49 more)

### Community 86 - "useDemoTour"
Cohesion: 0.35
Nodes (13): TourCancelled, useDemoTour(), cleanup(), guard(), onKey(), pickActiveEvent(), run(), runHook() (+5 more)

### Community 87 - "scene/types.ts"
Cohesion: 0.19
Nodes (10): BASEMAP_OPTIONS, emit, LAYERS, EventSyncOptions, emit, DEFAULT_LAYERS, EventTypeFilter, LayerKey (+2 more)

### Community 89 - "dependencies"
Cohesion: 0.20
Nodes (10): dependencies, cesium@1.125.0, echarts@^5.6.0, element-plus@^2.9.0, @element-plus/icons-vue@^2.3.1, three@^0.187.0, vue@^3.5.13, vue-router@^4.5.0 (+2 more)

### Community 90 - "routers/support.py"
Cohesion: 0.05
Nodes (23): SampleRepository, create_app(), _audit_writes(), _on_validation(), __getattr__(), _validation_message(), mark_notification_read(), patch_emergency_resource() (+15 more)

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

### Community 100 - "12. 业务闭环"
Cohesion: 0.33
Nodes (6): 12. 业务闭环, `Assessment`, `MonitoringRun`, `MonitoringTask`, `ReviewRecord`, `WorkOrder`

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

### Community 105 - "TrafficPanel.vue"
Cohesion: 0.13
Nodes (17): gauge, groups, level, levelCounts, meta, props, top10, totalRoads (+9 more)

### Community 106 - "AIAnalysis.vue"
Cohesion: 0.09
Nodes (34): jsonBody(), createTask(), getSamples(), prototypeTask(), uploadTask(), dispatchScenarioRun(), confirmDispatch(), openTemplateManage() (+26 more)

### Community 107 - "vite.config.ts"
Cohesion: 0.20
Nodes (7): vite-plugin-static-copy@^2.2.0, vite@^5.4.11, @vitejs/plugin-vue@^5.2.1, srcDir, vite, vite-plugin-static-copy, @vitejs/plugin-vue

### Community 108 - "EventLayer"
Cohesion: 0.19
Nodes (4): beamInstance(), clusterColor(), ellipseFillInstance(), EventLayer

### Community 109 - "argparse"
Cohesion: 0.10
Nodes (24): bounds(), centroid(), compact_json(), district_of(), grid_of(), load_district_segments(), main(), point_in_segments() (+16 more)

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

### Community 132 - "converse"
Cohesion: 0.32
Nodes (3): converse(), FakeClient, test_scenario_agent_normalizes_chinese_numeric_values()

### Community 133 - "useTaskRunner.ts"
Cohesion: 0.35
Nodes (12): 10. WebSocket `/api/ws`, getTask(), isTerminal(), TaskRunnerOptions, useTaskRunner(), apply(), clear(), finalizeElapsed() (+4 more)

### Community 135 - "cesium"
Cohesion: 0.13
Nodes (14): Region, AmbientEffects, beamAppearance(), encode(), f(), lineAppearance(), polylineVS(), radarAppearance() (+6 more)

### Community 139 - "eslint.config.js"
Cohesion: 0.29
Nodes (6): eslint-config-prettier@^9.1.2, eslint-plugin-vue@^9.33.0, typescript-eslint@^8.72.0, eslint-config-prettier, eslint-plugin-vue, typescript-eslint

### Community 142 - "config.py"
Cohesion: 0.26
Nodes (5): _bool(), _float(), _path(), Settings, main()

### Community 144 - "backend/tests/conftest.py"
Cohesion: 0.21
Nodes (4): client(), ctx(), tmp_root(), wait_task()

### Community 145 - "EventTable.vue"
Cohesion: 0.09
Nodes (18): emit, onRowClick(), onSortChange(), props, showAssignee, showSource, SortState, vw (+10 more)

### Community 146 - "AppHeader.vue"
Cohesion: 0.20
Nodes (11): city, conn, { connected }, date, demoTip, everConnected, { info, region, demoMode, load }, now (+3 more)

### Community 147 - "llm_module/__init__.py"
Cohesion: 0.22
Nodes (8): answer_chat(), _build_prompt(), ChatTurn, FakeClient, FakeCompletions, test_chat_includes_history_and_event_context(), test_chat_rejects_empty_history(), test_chat_requires_user_as_last_turn()

### Community 158 - "AnalysisTask"
Cohesion: 0.29
Nodes (7): 6. AI 分析任务, `AnalysisTask`, `GET /api/samples?type=fire` → 示例数据, `GET /api/tasks` → `AnalysisTask[]`（按创建时间倒序）, `GET /api/tasks/{id}` → `AnalysisTask`, `POST /api/tasks`（JSON，兼容原型）, `POST /api/tasks/upload`（multipart）

### Community 160 - "城市智眼业务闭环重构：第一阶段"
Cohesion: 0.25
Nodes (8): API, 公共支撑, 内涝示例闭环, 城市智眼业务闭环重构：第一阶段, 尚未完成, 数据资源画像, 状态机, 迁移与回滚

### Community 170 - "3. 城市三维对象"
Cohesion: 0.29
Nodes (7): 3. 城市三维对象, `GET /api/buildings/fine?district=武昌区` → GeoJSON `FeatureCollection<Polygon>`, `GET /api/buildings` → GeoJSON `FeatureCollection<Polygon>`, `GET /api/buildings/{id}` → 建筑详情, `GET /api/pois` → `[{ id, name, kind: "hospital"|"fire_station"|"police"|"school", longitude, latitude }]`, `GET /api/roads` → GeoJSON `FeatureCollection<LineString>`, `GET/PATCH /api/spatial/{entity_type}/{id}`

## Knowledge Gaps
- **45 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `12. 业务闭环` connect `12. 业务闭环` to `城市智眼 API 契约（v1）`?**
  _High betweenness centrality (0.201) - this node is a cross-community bridge._
- **Are the 50 inferred relationships involving `AppContext` (e.g. with `GeoRepository` and `create_app()`) actually correct?**
  _`AppContext` has 50 INFERRED edges - model-reasoned connections that need verification._
- **Should `ReviewBoard.vue` be split into smaller, more focused modules?**
  _Cohesion score 0.06543385490753911 - nodes in this community are weakly interconnected._
- **Why does `Task` connect `services/tasks.py` to `AppContext`, `12. 业务闭环`, `schemas.py`, `routers/workflow.py`, `seed.py`, `llm.py`, `_EventBuilder`, `routers/support.py`, `services/events.py`?**
  _High betweenness centrality (0.192) - this node is a cross-community bridge._
- **Should `EventDrawer.vue` be split into smaller, more focused modules?**
  _Cohesion score 0.07610993657505286 - nodes in this community are weakly interconnected._
- **Why does ``MonitoringRun`` connect `12. 业务闭环` to `services/tasks.py`?**
  _High betweenness centrality (0.190) - this node is a cross-community bridge._
- **Should `WorkflowPulse.vue` be split into smaller, more focused modules?**
  _Cohesion score 0.12666666666666668 - nodes in this community are weakly interconnected._
