# Graph Report - CityEye  (2026-11-11)

## Corpus Check
- 324 files · ~693,932 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 41 file(s) not represented in the graph (top: .csv 14, .geojson 11, (none) 8)

## Summary
- 3952 nodes · 9627 edges · 160 communities (117 shown, 43 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 696 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `12a6394`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- ReviewBoard.vue
- EventDrawer.vue
- routers/scenario.py
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
- pathlib
- icons.ts
- Monitoring.vue
- AppContext
- TaskProgress.vue
- download_satellite_basemap.py
- now
- steps
- crowdLayer.ts
- cityeye_algo/traffic.py
- WorkflowWorkspace.vue
- CrowdLayer
- ScenarioWorkspace.vue
- loadRun
- EventDetail.vue
- AssessmentQueue.vue
- DataTypeDistribution.vue
- roadLayer.ts
- useCityEvents.ts
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
- LLMError
- assess_settlement
- CameraController
- tool_runner.py
- GeoRepository
- roadLayer.ts
- types/scenario.ts
- OrderBoard.vue
- services/scenario.py
- cityeye
- algorithm/tests/conftest.py
- SystemManagement.vue
- test_registry.py
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
- AssistantChatPanel.vue
- package.json
- request
- CityEvent
- Region
- 4. 行为与仿真
- @element-plus/icons-vue
- routers/support.py
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
- building.ts
- AIAnalysis.vue
- eventLayer.ts
- argparse
- .prettierrc.json
- 数据库设计
- 数据集目录
- dev.sh
- manifests/README.md
- basemap/README.md
- demo.sh
- pages/format.ts
- useTaskRunner.ts
- cesium
- .create
- config.py
- export_snapshot.py
- TaskHistory.vue
- AppHeader.vue
- Settings
- Simulator
- errMsg
- AnalysisTask
- 城市智眼业务闭环重构：第一阶段
- SampleRepository
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
- `3. 关键接口` --references--> `CrowdLayer`  [INFERRED]
  docs/crowd-simulation.md → frontend/src/components/scene/crowd/crowdLayer.ts
- ``DataItem`` --references--> `DataItem`  [INFERRED]
  docs/api.md → frontend/src/types/api.ts
- ``MonitoringRun`` --references--> `Task`  [INFERRED]
  docs/api.md → backend/app/models.py
- `3.1 SettleWatch · 沉降监测（`building.py`）` --references--> `SettlementThresholds`  [INFERRED]
  docs/algorithms.md → algorithm/cityeye_algo/building.py
- ``Assessment`` --references--> `Assessment`  [INFERRED]
  docs/api.md → frontend/src/types/workflow.ts

## Import Cycles
- 3-file cycle: `algorithm/cityeye_algo/__init__.py -> algorithm/cityeye_algo/registry.py -> algorithm/cityeye_algo/building.py -> algorithm/cityeye_algo/__init__.py`
- 3-file cycle: `algorithm/cityeye_algo/__init__.py -> algorithm/cityeye_algo/registry.py -> algorithm/cityeye_algo/fire.py -> algorithm/cityeye_algo/__init__.py`
- 3-file cycle: `algorithm/cityeye_algo/__init__.py -> algorithm/cityeye_algo/registry.py -> algorithm/cityeye_algo/flood.py -> algorithm/cityeye_algo/__init__.py`
- 3-file cycle: `algorithm/cityeye_algo/__init__.py -> algorithm/cityeye_algo/registry.py -> algorithm/cityeye_algo/traffic.py -> algorithm/cityeye_algo/__init__.py`

## Communities (160 total, 43 thin omitted)

### Community 0 - "ReviewBoard.vue"
Cohesion: 0.06
Nodes (35): applyReviewToTemplate(), createReview(), getReviewCases(), getReviewDraft(), reviewExportUrl(), updateReview(), applyBusy, applyRule() (+27 more)

### Community 1 - "EventDrawer.vue"
Cohesion: 0.09
Nodes (24): evidence, evidence, activeAnn, annotated, color, confPct, detected, detections (+16 more)

### Community 2 - "routers/scenario.py"
Cohesion: 0.11
Nodes (23): rng(), ScenarioTemplate, compare_runs(), create_session(), create_template(), delete_template(), export_run(), get_run() (+15 more)

### Community 3 - "@element-plus/icons-vue"
Cohesion: 0.06
Nodes (28): isDrill, route, { sidebarCollapsed }, props, rows, geometry, props, aiItems (+20 more)

### Community 5 - "Dashboard.vue"
Cohesion: 0.04
Nodes (49): resetDemo(), askAssistantDemo(), assistantDemoQuestion, assistantOpen, assistantRef, autoTrack, basemap, { calm: calmBaseline, demoEventIds, enterCalmBaseline, revealAnomalies, setDemoEventIds } (+41 more)

### Community 6 - "EmergencyDrill.vue"
Cohesion: 0.05
Nodes (59): HAZARD_PROFILES, HazardProfile, hazardProfile(), hazardRadiusAt(), requiresPedestrianEvacuation(), smoothstep(), accent, actionText (+51 more)

### Community 7 - "schemas.py"
Cohesion: 0.05
Nodes (83): TaskTemplateRevision, assess_work_order_feedback(), patch_monitoring_task(), patch_task_template(), patch_work_order(), post_assessment(), post_monitoring_run(), post_monitoring_task() (+75 more)

### Community 8 - "api/workflow.ts"
Cohesion: 0.06
Nodes (49): EventQuery, activeOrders, activeTasks, assessments, dataItems, dataStats, items, loading (+41 more)

### Community 9 - "BuildingSafetyPanel.vue"
Cohesion: 0.05
Nodes (43): echarts@^5.6.0, getBuilding(), BASE, chart, el, props, option, props (+35 more)

### Community 10 - "CesiumViewer.vue"
Cohesion: 0.05
Nodes (56): active, alarmBuildingIds(), api, bindInteraction(), bindRenderErrorRecovery(), chooseDistrict(), closePanels(), containerRef (+48 more)

### Community 12 - "AIAnalysis.vue"
Cohesion: 0.09
Nodes (24): findRiskBuilding(), allowedExt, createEvent, emit, fileList, latitude, loadingSamples, loadSamples() (+16 more)

### Community 13 - "InputError"
Cohesion: 0.09
Nodes (13): InputError, damped_holt(), fmt_t(), median_step_minutes(), moving_average(), parse_times(), read_header(), read_table() (+5 more)

### Community 14 - "numpy"
Cohesion: 0.10
Nodes (26): clamp01(), blur(), box_mean(), box_sum(), closing(), dilate(), erode(), label_components() (+18 more)

### Community 15 - "errMsg"
Cohesion: 0.09
Nodes (28): generateEventReport(), parseTaskText(), busy, error, KIND_META, offline, props, report (+20 more)

### Community 16 - "EventCenter.vue"
Cohesion: 0.05
Nodes (42): todayPrefix(), activeOnly, applyQuery(), createVisible, diffFlash(), drawerId, drawerOpen, FILTER_KEYS (+34 more)

### Community 17 - "scene/types.ts"
Cohesion: 0.11
Nodes (19): BASEMAP_OPTIONS, emit, LAYERS, BasemapController, GLOBE_BASE_COLOR, STYLE, emit, DEFAULT_LAYERS (+11 more)

### Community 18 - "useOverview.ts"
Cohesion: 0.12
Nodes (29): metrics, { calm, demoEventIds }, { connected, lastMessageAt }, displayStats, lastUpdate, MODE_LABEL, pad(), { stats, events, revision } (+21 more)

### Community 19 - "WaterLevelAnalyzer"
Cohesion: 0.24
Nodes (9): FloodThresholds, WaterLevelAnalyzer, Bars, _storm(), test_csv_samples(), test_light_rain_not_detected(), test_rainstorm_detected_with_lag(), test_rising_series_forecast_without_rain() (+1 more)

### Community 20 - "ask"
Cohesion: 0.12
Nodes (14): main(), ask(), _client(), converse(), main(), FakeClient, FakeCompletions, settings() (+6 more)

### Community 21 - "DataManagement.vue"
Cohesion: 0.03
Nodes (72): autoCheckDataAsset(), getDataList(), getDataStats(), getDataValidations(), uploadData(), validateDataAsset(), patchEmergencyResource(), DataItem (+64 more)

### Community 22 - "services/tasks.py"
Cohesion: 0.08
Nodes (23): bad_request(), Task, upload_data(), _check_type(), _parse_float(), post_task(), upload_task(), _optional_coordinate() (+15 more)

### Community 23 - "pathlib"
Cohesion: 0.08
Nodes (17): AlgorithmMeta, AnalysisResult, Analyzer, Artifact, _clean_metric(), Detection, FireDetector, FireParams (+9 more)

### Community 24 - "icons.ts"
Cohesion: 0.13
Nodes (14): cache, emojiSupported(), EVENT_GLYPH, eventIcon(), POI_COLOR, POI_EMOJI, POI_GLYPH, poiIcon() (+6 more)

### Community 25 - "Monitoring.vue"
Cohesion: 0.04
Nodes (57): triggerScenario(), props, shown, props, rate, ringOffset, rows, sources (+49 more)

### Community 26 - "AppContext"
Cohesion: 0.06
Nodes (75): select(), AppContext, not_found(), NotificationRecord, data_stats(), list_data(), list_data_validations(), get_event() (+67 more)

### Community 27 - "TaskProgress.vue"
Cohesion: 0.12
Nodes (19): active, color, failed, percent, props, running, status, STEP_DESC (+11 more)

### Community 28 - "download_satellite_basemap.py"
Cohesion: 0.17
Nodes (11): BBox, build_parser(), crop_window(), download_tile(), lat_to_tile_y(), lon_to_tile_x(), main(), parse_bbox() (+3 more)

### Community 29 - "now"
Cohesion: 0.11
Nodes (13): list_events(), patch_event(), post_event(), merge_candidates(), EventPatch, add_log(), apply_patch(), create_event() (+5 more)

### Community 30 - "steps"
Cohesion: 0.05
Nodes (39): defaults, runs-on, steps, concurrency, cancel-in-progress, group, run, environment (+31 more)

### Community 31 - "crowdLayer.ts"
Cohesion: 0.10
Nodes (28): CrowdPerson, EXIT_CAPACITIES, EXIT_LABELS, HazardState, installGaitShader(), makeStickFigureGeometry(), makeVehicleGeometry(), RoadPath (+20 more)

### Community 32 - "cityeye_algo/traffic.py"
Cohesion: 0.08
Nodes (25): SettlementAnalyzer, annotate_image(), Band, Chart, font(), HLine, Line, Marker (+17 more)

### Community 33 - "WorkflowWorkspace.vue"
Cohesion: 0.10
Nodes (18): activeOrders, assessments, current, error, eventStore, loading, orders, props (+10 more)

### Community 34 - "CrowdLayer"
Cohesion: 0.10
Nodes (3): CrowdLayer, PersonType, SpawnType

### Community 35 - "ScenarioWorkspace.vue"
Cohesion: 0.03
Nodes (57): scenarioExportUrl(), affectedCounts, businessEvents, busy, classLabel(), comparison, currentFrame, currentRadius (+49 more)

### Community 36 - "loadRun"
Cohesion: 0.14
Nodes (18): createScenarioSession(), runCurrentScenarioVariants(), sendScenarioMessage(), applyPeople(), demoStart(), demoStop(), emit, ensureLayer() (+10 more)

### Community 37 - "EventDetail.vue"
Cohesion: 0.08
Nodes (26): getEventLogs(), assignee, assigneeOptions, busy, confidence, demoDispatch(), dispatchOpen, dispatchTarget (+18 more)

### Community 38 - "AssessmentQueue.vue"
Cohesion: 0.09
Nodes (22): createAssessment(), mergeCandidateEvents(), context, contextLoading, { currentName, load: loadOperator }, distanceMeters(), emit, form (+14 more)

### Community 39 - "DataTypeDistribution.vue"
Cohesion: 0.17
Nodes (13): option, props, statuses, emit, option, props, total, DATA_STATUS_META (+5 more)

### Community 40 - "roadLayer.ts"
Cohesion: 0.10
Nodes (21): ellipseInstance(), distance(), hashByte(), isFiniteCoord(), lineLength(), lineMidpoint(), LonLat, resampleLine() (+13 more)

### Community 41 - "useCityEvents.ts"
Cohesion: 0.15
Nodes (12): mergeCandidate(), lastCreated, revision, state, upsert(), useCityEvents(), loadFromApi(), setEvents() (+4 more)

### Community 43 - "武汉智眼首批数据集确定方案_dd680806.md"
Cohesion: 0.07
Nodes (26): 01　火灾与烟雾：D-Fire, 02　航拍车辆：VisDrone2019-DET, 03　建筑灾前灾后：xBD / xView2, 04　获取顺序、登记与验收, 05　武汉本地数据补充, 05　武汉本地数据补充（续）, 05　武汉本地数据补充（续）, 5.1　UAV-OBB：含武汉道路的车辆数据 (+18 more)

### Community 44 - "test_api.py"
Cohesion: 0.05
Nodes (4): test_data_list_stats_upload(), test_events_list_shape_and_order(), test_stats_overview(), test_due_periodic_task_runs_and_is_rescheduled()

### Community 46 - "with"
Cohesion: 0.09
Nodes (25): name, runs-on, steps, run, defaults, name, runs-on, steps (+17 more)

### Community 47 - "城市智眼 API 契约（v1）"
Cohesion: 0.10
Nodes (19): limit(), 0. 通用约定, 11. 城市智能情景推演, 13. 公共支撑, 14. 业务链路, 1. 系统, 4. 统计, 7. 监测数据源 (+11 more)

### Community 48 - "roadGraph.ts"
Cohesion: 0.12
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

### Community 53 - "types/event.ts"
Cohesion: 0.06
Nodes (36): activeCount, activeEvents, emit, fresh, list, now, props, sorted (+28 more)

### Community 54 - "seed.py"
Cohesion: 0.05
Nodes (42): Base, _audit_writes(), init_data(), AppMeta, AssessmentRecord, AuditLog, DataAsset, DataValidationRecord (+34 more)

### Community 55 - "LandmarkLayer"
Cohesion: 0.22
Nodes (3): Landmark, LandmarkLayer, LANDMARKS

### Community 56 - "llm.py"
Cohesion: 0.21
Nodes (13): _call_llm(), ChatIn, ChatMessageIn, _distance_m(), _event_data_nature(), _event_view(), llm_status(), _load_event_context() (+5 more)

### Community 58 - "CityEye 城市虚拟人群仿真模块"
Cohesion: 0.12
Nodes (16): 1.1 选型结论, 1.2 坐标系, 1. 技术融合方案, 2.1 人物模型, 2.2 实例化策略, 2. 模块架构, 3. 关键接口, 5. 分阶段实现清单 (+8 more)

### Community 59 - "LLMError"
Cohesion: 0.07
Nodes (32): parsed_task(), report(), test_chat_attaches_seeded_event_context(), test_chat_rejects_invalid_history(), test_chat_without_event_context(), fake_chat(), test_llm_status_availability_is_environment_independent(), test_parse_task_rejects_invalid_length() (+24 more)

### Community 60 - "assess_settlement"
Cohesion: 0.12
Nodes (14): assess_settlement(), ChangeDetector, ChangeParams, SettlementReport, SettlementThresholds, test_accelerating_settlement_is_warning(), test_change_detection_finds_new_structure(), test_change_detection_ignores_illumination() (+6 more)

### Community 61 - "CameraController"
Cohesion: 0.16
Nodes (4): CameraController, wait(), FlyOptions, OrbitOptions

### Community 62 - "tool_runner.py"
Cohesion: 0.15
Nodes (16): get_demo_event(), list_demo_facilities(), 4. Tool Calling, build_input(), main(), ScriptedClient, ScriptedCompletions, test_execute_known_and_unknown_tool() (+8 more)

### Community 63 - "GeoRepository"
Cohesion: 0.08
Nodes (7): base_road_name(), GeoRepository, is_generic_name(), Road, congestion_curve(), RoadLive, TrafficState

### Community 64 - "roadLayer.ts"
Cohesion: 0.09
Nodes (18): buildingColor(), BuildingLayer, BuildingRecord, extrude(), frameNumberOf(), HEIGHT_STOPS, nextFrame(), polygonsOf() (+10 more)

### Community 65 - "types/scenario.ts"
Cohesion: 0.19
Nodes (14): SCENARIO_LABEL, ScenarioComparison, ScenarioDataClass, ScenarioMessage, ScenarioParameters, ScenarioPerson, ScenarioReport, ScenarioRun (+6 more)

### Community 66 - "OrderBoard.vue"
Cohesion: 0.04
Nodes (50): assessWorkOrderFeedback(), createWorkOrder(), patchWorkOrder(), uploadWorkOrderFeedback(), useWorkOrderResource(), advance(), availableAssessments, availableResources (+42 more)

### Community 67 - "services/scenario.py"
Cohesion: 0.05
Nodes (51): ScenarioResourceReservation, ScenarioSession, ScenarioVersion, _apply_demo_defaults(), _new_id(), _now(), ScenarioService, _timestamp() (+43 more)

### Community 68 - "cityeye"
Cohesion: 0.11
Nodes (17): build, container_name, environment, image, ports, restart, volumes, CITYEYE_DEMO_MODE (+9 more)

### Community 69 - "algorithm/tests/conftest.py"
Cohesion: 0.25
Nodes (4): city_background(), paint_flame(), sample(), save()

### Community 70 - "SystemManagement.vue"
Cohesion: 0.03
Nodes (71): getSpatialFeature(), patchSpatialFeature(), markAllNotificationsRead(), markNotificationRead(), patchResponsibilityGrid(), patchRuntimeConfig(), accounts, currentId (+63 more)

### Community 71 - "test_registry.py"
Cohesion: 0.29
Nodes (3): test_select(), test_select_errors(), test_validate_checks_csv_header()

### Community 72 - "规格：CityEye 前端渐进式改进（第 1 批）"
Cohesion: 0.12
Nodes (15): resetFilters(), 1. 现状结论（已核实）, 2. 改动清单, 3. 明确不做（本轮）, 4. 验证计划, 5. 风险与回退, R1 表格响应式列断点修正, R2 事件表格空状态增加操作入口 (+7 more)

### Community 73 - "routers/workflow.py"
Cohesion: 0.10
Nodes (40): MonitoringTask, ScenarioRunRecord, WorkOrder, auto_check_data_asset(), validate_data_asset(), validation_to_dict(), template_revision_to_dict(), health() (+32 more)

### Community 74 - "城市智眼 · 算法说明"
Cohesion: 0.11
Nodes (16): cityeye_algo —— 城市智眼算法包, 使用, 测试, 1. 火灾 · FlameNet-Lite（`fire.py`）, 2.1 TrafficPulse · 时序路况（`traffic.py`）, 2.2 RoadOcc · 航拍路面车辆占有率, 2. 交通, 3.1 SettleWatch · 沉降监测（`building.py`） (+8 more)

### Community 75 - "EventDrawer.vue"
Cohesion: 0.07
Nodes (23): ACTION_META, ASSIGNEES, copyCoord(), currentId, emit, event, fetched, fetching (+15 more)

### Community 76 - "城市智眼 · CityEye"
Cohesion: 0.12
Nodes (17): 🔌 API 一览, ✨ 亮点, 🕸️ 代码图谱, 🗺️ 功能导览, 城市智眼 · CityEye, 🚀 快速开始, 📚 数据来源与致谢, 方式一：Docker（推荐，一条命令） (+9 more)

### Community 77 - "test_fire.py"
Cohesion: 0.19
Nodes (7): det(), test_plain_city_not_detected(), test_procedural_flame_detected(), test_red_roofs_and_orange_car_not_detected(), test_samples_negative(), test_samples_positive(), test_smoke_scored_on_sample_with_plume()

### Community 78 - "sys"
Cohesion: 0.13
Nodes (4): load_system_prompt(), main(), test_cases_cover_all_supported_event_types(), test_prompt_contains_required_guardrails()

### Community 79 - "types/scenario.ts"
Cohesion: 0.19
Nodes (9): PREVIOUS_EDGE, RISK_COLOR, ScenarioLayer, WATER_BODY, WATER_EDGE, ScenarioFrame, ScenarioRisk, ScenarioType (+1 more)

### Community 80 - "CityEye 大模型模块压缩交接"
Cohesion: 0.14
Nodes (13): 1. DeepSeek API, 2. CityEye 系统提示词, 3. 自然语言任务解析, 5. 结构化报告, CityEye 大模型模块压缩交接, Git 状态, 下一步, 会话目标 (+5 more)

### Community 81 - "build_geo.py"
Cohesion: 0.17
Nodes (19): build_buildings(), build_pois(), build_roads(), length(), classify(), clip_chain(), dist_m(), district_of() (+11 more)

### Community 83 - "AssistantChatPanel.vue"
Cohesion: 0.11
Nodes (16): chatWithAssistant(), AnswerBlock, busy, canSend, dataType, emit, error, input (+8 more)

### Community 84 - "package.json"
Cohesion: 0.05
Nodes (44): three@^0.187.0, vite-plugin-static-copy@^2.2.0, description, devDependencies, eslint@^9.39.5, eslint-config-prettier@^9.1.2, eslint-plugin-vue@^9.33.0, prettier@^3.9.10 (+36 more)

### Community 85 - "request"
Cohesion: 0.06
Nodes (70): vitest@^2.1.9, createEvent(), getEvents(), patchEvent(), snapshotEvents(), getBuildingDistricts(), getBuildings(), getFineBuildings() (+62 more)

### Community 86 - "CityEvent"
Cohesion: 0.13
Nodes (27): 2. 事件, `CityEvent`, `EventLog`, `GET /api/events/{id}` → `CityEvent`（404 不存在）, `GET /api/events/{id}/logs` → `EventLog[]`（按时间正序）, `PATCH /api/events/{id}`, `POST /api/events`（人工上报 / 市民上报）, getEvent() (+19 more)

### Community 88 - "4. 行为与仿真"
Cohesion: 0.40
Nodes (5): 4.1 单人行为, 4.2 批量生成, 4.3 聚集与疏散, 4.4 Demo 级动态风险场, 4. 行为与仿真

### Community 89 - "@element-plus/icons-vue"
Cohesion: 0.08
Nodes (22): dependencies, cesium@1.125.0, element-plus@^2.9.0, @element-plus/icons-vue@^2.3.1, vue@^3.5.13, vue-router@^4.5.0, checking, props (+14 more)

### Community 90 - "routers/support.py"
Cohesion: 0.07
Nodes (9): get_ctx(), asset_to_dict(), _require_demo(), reset(), scenario(), random_site(), human_size(), fmt_minute() (+1 more)

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
Nodes (54): createMonitoringTask(), createTaskTemplate(), deleteTaskTemplate(), executeMonitoringTask(), getTaskTemplateRevisions(), getTaskTemplates(), patchMonitoringTask(), patchTaskTemplate() (+46 more)

### Community 97 - "回答格式"
Cohesion: 0.18
Nodes (10): CityEye 城市治理助手, 信息使用规则, 信息缺口, 分析, 回答格式, 安全规则, 已知信息, 建议 (+2 more)

### Community 98 - "EventCreateDialog.vue"
Cohesion: 0.12
Nodes (19): bbox, center, emit, FALLBACK_CENTER, form, formRef, FormState, loadRegion() (+11 more)

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

### Community 105 - "building.ts"
Cohesion: 0.07
Nodes (34): grade, levelMeta, LEVELS, marker, option, props, gauge, groups (+26 more)

### Community 106 - "AIAnalysis.vue"
Cohesion: 0.09
Nodes (26): meta, meta, meta, typeMeta(), algorithms, center, curMeta, info (+18 more)

### Community 108 - "eventLayer.ts"
Cohesion: 0.07
Nodes (31): priorityEvents, ALWAYS, beamInstance(), circlePositions(), clusterBadge(), clusterColor(), clusterOutlineInstance(), ellipseFillInstance() (+23 more)

### Community 109 - "argparse"
Cohesion: 0.13
Nodes (20): bounds(), centroid(), compact_json(), district_of(), grid_of(), load_district_segments(), main(), point_in_segments() (+12 more)

### Community 112 - ".prettierrc.json"
Cohesion: 0.29
Nodes (6): arrowParens, endOfLine, printWidth, semi, singleQuote, trailingComma

### Community 113 - "数据库设计"
Cohesion: 0.50
Nodes (3): ER 图, 数据库设计, 种子数据（`backend/app/seed.py`）

### Community 116 - "数据集目录"
Cohesion: 0.50
Nodes (3): 当前数据, 数据集目录, 目录约定

### Community 132 - "pages/format.ts"
Cohesion: 0.27
Nodes (13): timeCost, fmtBytes(), fmtDuration(), fmtNum(), hexA(), isCsvUrl(), p2(), parseTs() (+5 more)

### Community 133 - "useTaskRunner.ts"
Cohesion: 0.39
Nodes (10): getTask(), isTerminal(), useTaskRunner(), apply(), clear(), finalizeElapsed(), poll(), stopTimers() (+2 more)

### Community 135 - "cesium"
Cohesion: 0.13
Nodes (14): Region, AmbientEffects, beamAppearance(), encode(), f(), lineAppearance(), polylineVS(), radarAppearance() (+6 more)

### Community 137 - ".create"
Cohesion: 0.09
Nodes (5): make_engine(), make_session_factory(), envelope(), RealtimeHub, SourceState

### Community 142 - "config.py"
Cohesion: 0.26
Nodes (5): _bool(), _float(), _path(), Settings, main()

### Community 144 - "export_snapshot.py"
Cohesion: 0.11
Nodes (8): client(), ctx(), tmp_root(), wait_task(), test_building_spatial_properties_can_be_maintained(), dump(), main(), main()

### Community 145 - "TaskHistory.vue"
Cohesion: 0.20
Nodes (8): emit, onRowClick(), page, props, rows, showAlgo, showProg, vw

### Community 146 - "AppHeader.vue"
Cohesion: 0.20
Nodes (11): city, conn, { connected }, date, demoTip, everConnected, { info, region, demoMode, load }, now (+3 more)

### Community 147 - "Settings"
Cohesion: 0.10
Nodes (23): answer_chat(), _build_prompt(), ChatTurn, Settings, generate_report(), ReportError, FakeClient, FakeCompletions (+15 more)

### Community 148 - "Simulator"
Cohesion: 0.07
Nodes (9): create_app(), lifespan(), _on_validation(), __getattr__(), _validation_message(), Simulator, test_lifecycle_advances_and_respects_state_machine(), test_patrol_creates_events_only_on_detection() (+1 more)

### Community 151 - "errMsg"
Cohesion: 0.10
Nodes (21): compareScenarioRuns(), createScenarioTemplate(), deleteScenarioTemplate(), generateScenarioReport(), getScenarioTemplateRevisions(), patchScenarioTemplate(), actionLabel(), loadLogs() (+13 more)

### Community 158 - "AnalysisTask"
Cohesion: 0.22
Nodes (10): 10. WebSocket `/api/ws`, 6. AI 分析任务, `AnalysisTask`, `GET /api/samples?type=fire` → 示例数据, `GET /api/tasks` → `AnalysisTask[]`（按创建时间倒序）, `GET /api/tasks/{id}` → `AnalysisTask`, `POST /api/tasks`（JSON，兼容原型）, `POST /api/tasks/upload`（multipart） (+2 more)

### Community 160 - "城市智眼业务闭环重构：第一阶段"
Cohesion: 0.25
Nodes (8): API, 公共支撑, 内涝示例闭环, 城市智眼业务闭环重构：第一阶段, 尚未完成, 数据资源画像, 状态机, 迁移与回滚

### Community 170 - "3. 城市三维对象"
Cohesion: 0.29
Nodes (7): 3. 城市三维对象, `GET /api/buildings/fine?district=武昌区` → GeoJSON `FeatureCollection<Polygon>`, `GET /api/buildings` → GeoJSON `FeatureCollection<Polygon>`, `GET /api/buildings/{id}` → 建筑详情, `GET /api/pois` → `[{ id, name, kind: "hospital"|"fire_station"|"police"|"school", longitude, latitude }]`, `GET /api/roads` → GeoJSON `FeatureCollection<LineString>`, `GET/PATCH /api/spatial/{entity_type}/{id}`

## Knowledge Gaps
- **43 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Task` connect `services/tasks.py` to `12. 业务闭环`, `schemas.py`, `routers/workflow.py`, `Simulator`, `seed.py`, `llm.py`, `_EventBuilder`, `AppContext`?**
  _High betweenness centrality (0.202) - this node is a cross-community bridge._
- **Are the 66 inferred relationships involving `AppContext` (e.g. with `GeoRepository` and `create_app()`) actually correct?**
  _`AppContext` has 66 INFERRED edges - model-reasoned connections that need verification._
- **Should `ReviewBoard.vue` be split into smaller, more focused modules?**
  _Cohesion score 0.06153846153846154 - nodes in this community are weakly interconnected._
- **Why does `12. 业务闭环` connect `12. 业务闭环` to `城市智眼 API 契约（v1）`?**
  _High betweenness centrality (0.201) - this node is a cross-community bridge._
- **Should `EventDrawer.vue` be split into smaller, more focused modules?**
  _Cohesion score 0.08994708994708994 - nodes in this community are weakly interconnected._
- **Why does ``MonitoringRun`` connect `12. 业务闭环` to `services/tasks.py`?**
  _High betweenness centrality (0.200) - this node is a cross-community bridge._
- **Should `routers/scenario.py` be split into smaller, more focused modules?**
  _Cohesion score 0.11051693404634581 - nodes in this community are weakly interconnected._
