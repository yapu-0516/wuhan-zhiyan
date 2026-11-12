# Graph Report - CityEye  (2026-11-12)

## Corpus Check
- 330 files · ~698,390 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 41 file(s) not represented in the graph (top: .csv 14, .geojson 11, (none) 8)

## Summary
- 4047 nodes · 9842 edges · 175 communities (126 shown, 49 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 593 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `04ba7dc`
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
- TaskInputPanel.vue
- InputError
- numpy
- errMsg
- EventCenter.vue
- services/workflow.py
- useOverview.ts
- WaterLevelAnalyzer
- ask
- DataManagement.vue
- services/tasks.py
- services/drills.py
- report_generator.py
- types/api.ts
- AppContext
- EventCreateDialog.vue
- download_satellite_basemap.py
- services/events.py
- steps
- crowdLayer.ts
- AnalysisResult
- aiMeta.ts
- CrowdLayer
- ScenarioWorkspace.vue
- LLMError
- EventDetail.vue
- EventLayer
- RoadLayer
- roadLayer.ts
- cityeye_algo/traffic.py
- 武汉智眼首批数据集确定方案_dd680806.md
- test_api.py
- SceneApi
- with
- 城市智眼 API 契约（v1）
- roadGraph.ts
- CrowdSimulationPanel.vue
- generate_samples.py
- TaskSeriesChart.vue
- compilerOptions
- scripts
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
- dependencies
- 规格：CityEye 前端渐进式改进（第 1 批）
- main.py
- 城市智眼 · 算法说明
- EventDrawer.vue
- 城市智眼 · CityEye
- test_fire.py
- algorithm/tests/conftest.py
- types/scenario.ts
- CityEye 大模型模块压缩交接
- build_geo.py
- README.md
- AnalysisTask
- devDependencies
- request
- useDemoTour
- AssistantChatPanel.vue
- SourceState
- errMsg
- useTaskRunner.ts
- TrafficPanel.vue
- CityEye 大模型模块
- SceneClock
- CityEye 项目交接说明
- TaskQueue.vue
- 回答格式
- package.json
- compilerOptions
- loadRun
- 系统架构
- manifest.json
- 城市应急演练
- CityEye 界面设计说明
- BuildingSafetyPanel.vue
- AIAnalysis.vue
- .add
- eventLayer.ts
- argparse
- .session
- .prettierrc.json
- 数据库设计
- motion.ts
- vite.config.ts
- 数据集目录
- dev.sh
- manifests/README.md
- basemap/README.md
- demo.sh
- onReady
- TrafficState
- DataStatusChart.vue
- cesium
- export_snapshot.py
- RealtimeHub
- hazard.ts
- eslint.config.js
- cityeye_algo —— 城市智眼算法包
- TaskHistory.vue
- config.py
- load
- 4. 行为与仿真
- DataTypeDistribution.vue
- llm_module/__init__.py
- sys
- Road
- .create
- vitest
- pages/format.ts
- 城市智眼业务闭环重构：第一阶段
- filtered
- syncDrillRun
- onReady
- loadEmergencyResources

## God Nodes (most connected - your core abstractions)
1. `AppContext` - 154 edges
2. `request()` - 98 edges
3. `CrowdLayer` - 73 edges
4. `select()` - 69 edges
5. `vue` - 68 edges
6. `get()` - 56 edges
7. `not_found()` - 55 edges
8. `now()` - 50 edges
9. `jsonBody()` - 44 edges
10. `errMsg()` - 44 edges

## Surprising Connections (you probably didn't know these)
- `3. 关键接口` --references--> `CrowdLayer`  [INFERRED]
  docs/crowd-simulation.md → frontend/src/components/scene/crowd/crowdLayer.ts
- ``MonitoringRun`` --references--> `Task`  [INFERRED]
  docs/api.md → backend/app/models.py
- ``DataItem`` --references--> `DataItem`  [INFERRED]
  docs/api.md → frontend/src/types/api.ts
- ``Assessment`` --references--> `Assessment`  [INFERRED]
  docs/api.md → frontend/src/types/workflow.ts
- `关键约束` --references--> `_call_llm()`  [INFERRED]
  llm_module/HANDOFF.md → backend/app/routers/llm.py

## Import Cycles
- 3-file cycle: `algorithm/cityeye_algo/__init__.py -> algorithm/cityeye_algo/registry.py -> algorithm/cityeye_algo/building.py -> algorithm/cityeye_algo/__init__.py`
- 3-file cycle: `algorithm/cityeye_algo/__init__.py -> algorithm/cityeye_algo/registry.py -> algorithm/cityeye_algo/fire.py -> algorithm/cityeye_algo/__init__.py`
- 3-file cycle: `algorithm/cityeye_algo/__init__.py -> algorithm/cityeye_algo/registry.py -> algorithm/cityeye_algo/flood.py -> algorithm/cityeye_algo/__init__.py`
- 3-file cycle: `algorithm/cityeye_algo/__init__.py -> algorithm/cityeye_algo/registry.py -> algorithm/cityeye_algo/traffic.py -> algorithm/cityeye_algo/__init__.py`

## Communities (175 total, 49 thin omitted)

### Community 0 - "ReviewBoard.vue"
Cohesion: 0.06
Nodes (37): applyReviewToTemplate(), createReview(), getReviewCases(), getReviewDraft(), reviewExportUrl(), updateReview(), applyBusy, applyRule() (+29 more)

### Community 1 - "EventDrawer.vue"
Cohesion: 0.09
Nodes (25): evidence, evidence, activeAnn, annotated, color, confPct, detected, detections (+17 more)

### Community 2 - "WorkflowPulse.vue"
Cohesion: 0.06
Nodes (46): autoCheckDataAsset(), getDataList(), getDataStats(), getDataValidations(), uploadData(), qs(), getAssessments(), getMonitoringRuns() (+38 more)

### Community 3 - "@element-plus/icons-vue"
Cohesion: 0.06
Nodes (33): isDrill, route, { sidebarCollapsed }, props, rows, aiItems, { calm, demoEventIds }, displayActive (+25 more)

### Community 5 - "Dashboard.vue"
Cohesion: 0.03
Nodes (55): BASEMAP_OPTIONS, emit, LAYERS, emit, DEFAULT_LAYERS, LayerKey, LayerVisibility, TourState (+47 more)

### Community 6 - "EmergencyDrill.vue"
Cohesion: 0.04
Nodes (48): accent, actionText, active, activeExits, bottleneckExit, closedRoads, completed, crowdStats (+40 more)

### Community 7 - "schemas.py"
Cohesion: 0.05
Nodes (75): dispatch_scenario_run(), AccountOut, AlgorithmInfoOut, AlgorithmOut, AnalysisTaskOut, AssessmentContextOut, AssessmentOut, AuditLogOut (+67 more)

### Community 8 - "api/workflow.ts"
Cohesion: 0.06
Nodes (52): createAssessment(), getAssessmentContext(), mergeCandidateEvents(), context, contextLoading, { currentName, load: loadOperator }, distanceMeters(), emit (+44 more)

### Community 9 - "BuildingSafetyPanel.vue"
Cohesion: 0.05
Nodes (38): getBuilding(), BASE, chart, el, props, bProps, CATEGORY, chart (+30 more)

### Community 10 - "CesiumViewer.vue"
Cohesion: 0.05
Nodes (56): active, alarmBuildingIds(), api, bindInteraction(), bindRenderErrorRecovery(), chooseDistrict(), closePanels(), containerRef (+48 more)

### Community 12 - "TaskInputPanel.vue"
Cohesion: 0.09
Nodes (24): findRiskBuilding(), allowedExt, createEvent, emit, fileList, latitude, loadingSamples, loadSamples() (+16 more)

### Community 13 - "InputError"
Cohesion: 0.12
Nodes (10): damped_holt(), fmt_t(), median_step_minutes(), moving_average(), parse_times(), read_table(), rolling_mad_z(), runs_where() (+2 more)

### Community 14 - "numpy"
Cohesion: 0.09
Nodes (27): blur(), box_mean(), box_sum(), closing(), dilate(), erode(), label_components(), load_rgb() (+19 more)

### Community 15 - "errMsg"
Cohesion: 0.09
Nodes (28): generateEventReport(), parseTaskText(), busy, error, KIND_META, offline, props, report (+20 more)

### Community 16 - "EventCenter.vue"
Cohesion: 0.04
Nodes (51): emit, onRowClick(), onSortChange(), props, showAssignee, showSource, SortState, vw (+43 more)

### Community 17 - "services/workflow.py"
Cohesion: 0.09
Nodes (46): health(), apply_review_to_template(), assess_work_order_feedback(), list_review_cases(), list_reviews(), post_assessment(), post_monitoring_run(), post_monitoring_task() (+38 more)

### Community 18 - "useOverview.ts"
Cohesion: 0.12
Nodes (27): metrics, { calm, demoEventIds }, { connected, lastMessageAt }, displayStats, lastUpdate, MODE_LABEL, pad(), { stats, events, revision } (+19 more)

### Community 19 - "WaterLevelAnalyzer"
Cohesion: 0.17
Nodes (11): FloodThresholds, WaterLevelAnalyzer, WaterSegmenter, WaterSegParams, _storm(), test_csv_samples(), test_light_rain_not_detected(), test_rainstorm_detected_with_lag() (+3 more)

### Community 20 - "ask"
Cohesion: 0.15
Nodes (12): main(), ask(), _client(), LLMError, main(), FakeClient, FakeCompletions, settings() (+4 more)

### Community 21 - "DataManagement.vue"
Cohesion: 0.03
Nodes (49): ANALYSIS_META, analysisFilter, analysisOptions, analyzableCount, autoChecking, averageQuality, byType, { currentName, load: loadOperator } (+41 more)

### Community 22 - "services/tasks.py"
Cohesion: 0.06
Nodes (34): bad_request(), DataAsset, DataValidationRecord, asset_to_dict(), auto_check_data_asset(), data_stats(), _default_validation_notes(), list_data() (+26 more)

### Community 23 - "services/drills.py"
Cohesion: 0.21
Nodes (12): ScenarioRunRecord, get_drill_run(), list_drill_runs(), patch_drill_run(), post_drill_review(), post_drill_run(), DrillRunCreate, DrillRunPatch (+4 more)

### Community 24 - "report_generator.py"
Cohesion: 0.18
Nodes (13): AnalysisFinding, CityEventReport, EventOverview, generate_report(), load_report_prompt(), ReportError, RiskAssessment, FakeClient (+5 more)

### Community 25 - "types/api.ts"
Cohesion: 0.09
Nodes (29): EventQuery, option, props, broken, emit, KIND, EventCluster, connect() (+21 more)

### Community 26 - "AppContext"
Cohesion: 0.04
Nodes (77): select(), AppContext, get_ctx(), init_data(), ScenarioTemplate, ScenarioTemplateRevision, building_detail(), buildings() (+69 more)

### Community 27 - "EventCreateDialog.vue"
Cohesion: 0.05
Nodes (48): createEvent(), apiState, getSystemInfo(), resetDemo(), city, conn, { connected }, date (+40 more)

### Community 28 - "download_satellite_basemap.py"
Cohesion: 0.17
Nodes (11): BBox, build_parser(), crop_window(), download_tile(), lat_to_tile_y(), lon_to_tile_x(), main(), parse_bbox() (+3 more)

### Community 29 - "services/events.py"
Cohesion: 0.06
Nodes (18): lifespan(), get_event(), get_logs(), list_events(), patch_event(), post_event(), merge_candidates(), EventPatch (+10 more)

### Community 30 - "steps"
Cohesion: 0.05
Nodes (39): defaults, runs-on, steps, concurrency, cancel-in-progress, group, run, environment (+31 more)

### Community 31 - "crowdLayer.ts"
Cohesion: 0.13
Nodes (19): CrowdPerson, EXIT_CAPACITIES, EXIT_LABELS, HazardState, installGaitShader(), makeStickFigureGeometry(), makeVehicleGeometry(), RoadPath (+11 more)

### Community 32 - "AnalysisResult"
Cohesion: 0.06
Nodes (25): AlgorithmMeta, AnalysisResult, Analyzer, _clean_metric(), Detection, InputError, FireDetector, FireParams (+17 more)

### Community 33 - "aiMeta.ts"
Cohesion: 0.12
Nodes (19): active, color, failed, percent, props, running, status, STEP_DESC (+11 more)

### Community 35 - "ScenarioWorkspace.vue"
Cohesion: 0.03
Nodes (57): scenarioExportUrl(), affectedCounts, businessEvents, busy, classLabel(), comparison, currentFrame, currentRadius (+49 more)

### Community 36 - "LLMError"
Cohesion: 0.17
Nodes (12): report(), test_chat_attaches_seeded_event_context(), test_chat_rejects_invalid_history(), test_chat_without_event_context(), fake_chat(), test_llm_status_availability_is_environment_independent(), test_parse_task_rejects_invalid_length(), test_report_marks_citizen_input_unverified() (+4 more)

### Community 37 - "EventDetail.vue"
Cohesion: 0.08
Nodes (26): getEventLogs(), assignee, assigneeOptions, busy, confidence, demoDispatch(), dispatchOpen, dispatchTarget (+18 more)

### Community 38 - "EventLayer"
Cohesion: 0.19
Nodes (4): beamInstance(), clusterColor(), ellipseFillInstance(), EventLayer

### Community 39 - "RoadLayer"
Cohesion: 0.13
Nodes (5): alphaOf(), flowSpeedByte(), RoadLayer, RoadRecord, Road

### Community 40 - "roadLayer.ts"
Cohesion: 0.22
Nodes (15): ellipseInstance(), cleanRing(), distance(), isFiniteCoord(), lineLength(), lineMidpoint(), resampleLine(), ringAreaM2() (+7 more)

### Community 41 - "cityeye_algo/traffic.py"
Cohesion: 0.09
Nodes (18): Artifact, clamp01(), SettlementAnalyzer, annotate_image(), Band, Bars, Chart, font() (+10 more)

### Community 43 - "武汉智眼首批数据集确定方案_dd680806.md"
Cohesion: 0.07
Nodes (26): 01　火灾与烟雾：D-Fire, 02　航拍车辆：VisDrone2019-DET, 03　建筑灾前灾后：xBD / xView2, 04　获取顺序、登记与验收, 05　武汉本地数据补充, 05　武汉本地数据补充（续）, 05　武汉本地数据补充（续）, 5.1　UAV-OBB：含武汉道路的车辆数据 (+18 more)

### Community 44 - "test_api.py"
Cohesion: 0.05
Nodes (3): test_data_list_stats_upload(), test_events_list_shape_and_order(), test_stats_overview()

### Community 45 - "SceneApi"
Cohesion: 0.07
Nodes (7): BasemapController, GLOBE_BASE_COLOR, STYLE, SceneApi, BasemapConfig, BasemapKey, BASEMAPS

### Community 46 - "with"
Cohesion: 0.09
Nodes (25): name, runs-on, steps, run, defaults, name, runs-on, steps (+17 more)

### Community 47 - "城市智眼 API 契约（v1）"
Cohesion: 0.04
Nodes (42): _rule_triggered(), limit(), 0. 通用约定, 11. 城市智能情景推演, 12. 业务闭环, 13. 公共支撑, 14. 业务链路, 15. 应急演练 (+34 more)

### Community 48 - "roadGraph.ts"
Cohesion: 0.11
Nodes (10): GraphEdge, GraphLine, GraphPoint, hazardPenalizedCost(), MinHeap, PlannedRoute, pointDistance(), projectOnSegment() (+2 more)

### Community 49 - "CrowdSimulationPanel.vue"
Cohesion: 0.10
Nodes (19): benchmark, busy, clearPeople(), count, dangerRadius, emptyEvacuation, emptyStats, evacuate() (+11 more)

### Community 50 - "generate_samples.py"
Cohesion: 0.06
Nodes (43): add_collapse(), add_fire(), add_flood(), add_new_structure(), add_street_lights(), BuildingShape, Corridor, finish() (+35 more)

### Community 51 - "TaskSeriesChart.vue"
Cohesion: 0.12
Nodes (21): metrics, metrics, EXTRA_COLORS, extraKeys, MAIN_NAME, option, props, Series (+13 more)

### Community 52 - "compilerOptions"
Cohesion: 0.09
Nodes (21): compilerOptions, allowImportingTsExtensions, baseUrl, isolatedModules, jsx, lib, module, moduleDetection (+13 more)

### Community 53 - "scripts"
Cohesion: 0.18
Nodes (11): scripts, build, dev, format, format:check, lint, lint:fix, preview (+3 more)

### Community 54 - "seed.py"
Cohesion: 0.05
Nodes (46): Base, make_engine(), make_session_factory(), is_generic_name(), AppMeta, AssessmentRecord, AuditLog, EmergencyResource (+38 more)

### Community 55 - "LandmarkLayer"
Cohesion: 0.20
Nodes (4): Landmark, LandmarkLayer, LANDMARKS, cesium

### Community 56 - "llm.py"
Cohesion: 0.21
Nodes (13): _call_llm(), ChatIn, ChatMessageIn, _distance_m(), _event_data_nature(), _event_view(), llm_status(), _load_event_context() (+5 more)

### Community 58 - "CityEye 城市虚拟人群仿真模块"
Cohesion: 0.12
Nodes (16): 1.1 选型结论, 1.2 坐标系, 1. 技术融合方案, 2.1 人物模型, 2.2 实例化策略, 2. 模块架构, 3. 关键接口, 5. 分阶段实现清单 (+8 more)

### Community 59 - "Settings"
Cohesion: 0.08
Nodes (24): parsed_task(), test_parse_task_retries_one_malformed_model_output(), flaky_parse(), test_parse_task_route_and_provider_error(), fake_parse(), Settings, converse(), generate_scenario_report() (+16 more)

### Community 60 - "assess_settlement"
Cohesion: 0.10
Nodes (17): assess_settlement(), ChangeDetector, ChangeParams, SettlementReport, SettlementThresholds, test_accelerating_settlement_is_warning(), test_change_detection_finds_new_structure(), test_change_detection_ignores_illumination() (+9 more)

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
Cohesion: 0.16
Nodes (16): patchScenarioTemplate(), saveScenarioTemplateEdit(), SCENARIO_LABEL, ScenarioComparison, ScenarioDataClass, ScenarioMessage, ScenarioParameters, ScenarioPerson (+8 more)

### Community 66 - "OrderBoard.vue"
Cohesion: 0.04
Nodes (62): getEmergencyResources(), assessWorkOrderFeedback(), createWorkOrder(), patchWorkOrder(), uploadWorkOrderFeedback(), useWorkOrderResource(), advance(), ATTACHMENT_ACCEPT (+54 more)

### Community 67 - "services/scenario.py"
Cohesion: 0.06
Nodes (41): agent_output(), test_compare_does_not_require_current_parameters(), test_demo_auto_run_fills_assumptions_and_builds_three_variants(), test_scenario_can_start_from_event_and_export_affected_objects(), test_scenario_missing_parameters_are_reported(), test_scenario_session_and_run(), test_selected_scenario_can_become_traceable_work_orders(), API (+33 more)

### Community 68 - "cityeye"
Cohesion: 0.11
Nodes (17): build, container_name, environment, image, ports, restart, volumes, CITYEYE_DEMO_MODE (+9 more)

### Community 69 - "Monitoring.vue"
Cohesion: 0.04
Nodes (43): props, shown, props, rate, ringOffset, rows, sources, totals (+35 more)

### Community 70 - "SystemManagement.vue"
Cohesion: 0.04
Nodes (69): getSpatialFeature(), getSupportAccounts(), markAllNotificationsRead(), markNotificationRead(), patchResponsibilityGrid(), patchRuntimeConfig(), accounts, currentId (+61 more)

### Community 71 - "dependencies"
Cohesion: 0.20
Nodes (10): dependencies, cesium@1.125.0, echarts@^5.6.0, element-plus@^2.9.0, @element-plus/icons-vue@^2.3.1, three@^0.187.0, vue@^3.5.13, vue-router@^4.5.0 (+2 more)

### Community 72 - "规格：CityEye 前端渐进式改进（第 1 批）"
Cohesion: 0.12
Nodes (15): resetFilters(), 1. 现状结论（已核实）, 2. 改动清单, 3. 明确不做（本轮）, 4. 验证计划, 5. 风险与回退, R1 表格响应式列断点修正, R2 事件表格空状态增加操作入口 (+7 more)

### Community 73 - "main.py"
Cohesion: 0.05
Nodes (20): create_app(), _audit_writes(), _on_validation(), __getattr__(), _validation_message(), stats_overview(), export_graph(), graph() (+12 more)

### Community 74 - "城市智眼 · 算法说明"
Cohesion: 0.20
Nodes (10): 1. 火灾 · FlameNet-Lite（`fire.py`）, 2.1 TrafficPulse · 时序路况（`traffic.py`）, 2.2 RoadOcc · 航拍路面车辆占有率, 2. 交通, 4.1 AquaLevel · 积水监测时序（`flood.py`）, 4.2 AquaSeg · 积水影像分割, 4. 内涝, 5. 示例数据上的实测结果 (+2 more)

### Community 75 - "EventDrawer.vue"
Cohesion: 0.06
Nodes (46): getEvents(), patchEvent(), snapshotEvents(), props, rows, total, ACTION_META, ASSIGNEES (+38 more)

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
Cohesion: 0.17
Nodes (10): PREVIOUS_EDGE, RISK_COLOR, ScenarioLayer, WATER_BODY, WATER_EDGE, RoadCollection, ScenarioFrame, ScenarioRisk (+2 more)

### Community 80 - "CityEye 大模型模块压缩交接"
Cohesion: 0.14
Nodes (13): 1. DeepSeek API, 2. CityEye 系统提示词, 3. 自然语言任务解析, 5. 结构化报告, CityEye 大模型模块压缩交接, Git 状态, 下一步, 会话目标 (+5 more)

### Community 81 - "build_geo.py"
Cohesion: 0.17
Nodes (19): build_buildings(), build_pois(), build_roads(), length(), classify(), clip_chain(), dist_m(), district_of() (+11 more)

### Community 83 - "AnalysisTask"
Cohesion: 0.22
Nodes (10): 10. WebSocket `/api/ws`, 6. AI 分析任务, `AnalysisTask`, `GET /api/samples?type=fire` → 示例数据, `GET /api/tasks` → `AnalysisTask[]`（按创建时间倒序）, `GET /api/tasks/{id}` → `AnalysisTask`, `POST /api/tasks`（JSON，兼容原型）, `POST /api/tasks/upload`（multipart） (+2 more)

### Community 84 - "devDependencies"
Cohesion: 0.18
Nodes (11): devDependencies, eslint@^9.39.5, prettier@^3.9.10, @types/three@^0.187.0, typescript@~5.6.3, vue-tsc@^2.1.10, eslint, prettier (+3 more)

### Community 85 - "request"
Cohesion: 0.06
Nodes (60): validateDataAsset(), createDrillRun(), getDrillRuns(), updateDrillRun(), getBuildingDistricts(), getBuildings(), getFineBuildings(), getPois() (+52 more)

### Community 86 - "useDemoTour"
Cohesion: 0.19
Nodes (20): getEvent(), triggerScenario(), ensureEvent(), TourFocus, DemoTourContext, DemoTourHooks, TourCancelled, useDemoTour() (+12 more)

### Community 87 - "AssistantChatPanel.vue"
Cohesion: 0.11
Nodes (16): chatWithAssistant(), AnswerBlock, busy, canSend, dataType, emit, error, input (+8 more)

### Community 89 - "errMsg"
Cohesion: 0.11
Nodes (20): compareScenarioRuns(), createScenarioTemplate(), deleteScenarioTemplate(), generateScenarioReport(), getScenarioTemplateRevisions(), actionLabel(), loadLogs(), submit() (+12 more)

### Community 90 - "useTaskRunner.ts"
Cohesion: 0.51
Nodes (9): getTask(), isTerminal(), useTaskRunner(), apply(), clear(), finalizeElapsed(), poll(), stopTimers() (+1 more)

### Community 91 - "TrafficPanel.vue"
Cohesion: 0.17
Nodes (15): gauge, groups, level, levelCounts, meta, props, top10, totalRoads (+7 more)

### Community 92 - "CityEye 大模型模块"
Cohesion: 0.17
Nodes (11): CityEye 大模型模块, Tool Calling 验证, 城市治理问答, 安装, 当前范围, 测试, 系统提示词测试, 结构化研判报告 (+3 more)

### Community 94 - "CityEye 项目交接说明"
Cohesion: 0.25
Nodes (7): 1. 接手后先做什么, 2. 已纳入云端的关键数据, 3. 数据再生成顺序, 4. 当前功能边界, 5. 验证, 6. 不应提交的内容, CityEye 项目交接说明

### Community 95 - "TaskQueue.vue"
Cohesion: 0.04
Nodes (56): createMonitoringTask(), createTaskTemplate(), deleteTaskTemplate(), executeMonitoringTask(), getTaskTemplateRevisions(), getTaskTemplates(), patchMonitoringTask(), patchTaskTemplate() (+48 more)

### Community 97 - "回答格式"
Cohesion: 0.18
Nodes (10): CityEye 城市治理助手, 信息使用规则, 信息缺口, 分析, 回答格式, 安全规则, 已知信息, 建议 (+2 more)

### Community 98 - "package.json"
Cohesion: 0.25
Nodes (7): description, name, overrides, @cesium/widgets, private, type, version

### Community 99 - "compilerOptions"
Cohesion: 0.20
Nodes (9): compilerOptions, allowSyntheticDefaultImports, composite, module, moduleResolution, outDir, skipLibCheck, strict (+1 more)

### Community 100 - "loadRun"
Cohesion: 0.14
Nodes (18): createScenarioSession(), runCurrentScenarioVariants(), sendScenarioMessage(), applyPeople(), demoStart(), demoStop(), emit, ensureLayer() (+10 more)

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
Cohesion: 0.25
Nodes (8): CityEye 界面设计说明, 各页面问题, 应急演练页, 方向, 本轮调整, 真实城市视图中的事件层级, 设计边界, 验证

### Community 105 - "BuildingSafetyPanel.vue"
Cohesion: 0.05
Nodes (38): grade, levelMeta, LEVELS, marker, option, props, emit, LEVELS (+30 more)

### Community 106 - "AIAnalysis.vue"
Cohesion: 0.09
Nodes (26): meta, meta, meta, typeMeta(), algorithms, center, curMeta, info (+18 more)

### Community 108 - "eventLayer.ts"
Cohesion: 0.05
Nodes (48): 2. 事件, `CityEvent`, `EventLog`, `GET /api/events/{id}` → `CityEvent`（404 不存在）, `GET /api/events/{id}/logs` → `EventLog[]`（按时间正序）, `PATCH /api/events/{id}`, `POST /api/events`（人工上报 / 市民上报）, activeCount (+40 more)

### Community 109 - "argparse"
Cohesion: 0.13
Nodes (20): bounds(), centroid(), compact_json(), district_of(), grid_of(), load_district_segments(), main(), point_in_segments() (+12 more)

### Community 110 - ".session"
Cohesion: 0.12
Nodes (19): not_found(), ScenarioResourceReservation, assessment_context(), delete_task_template(), export_review(), get_monitoring_task(), get_work_order(), patch_monitoring_task() (+11 more)

### Community 112 - ".prettierrc.json"
Cohesion: 0.29
Nodes (6): arrowParens, endOfLine, printWidth, semi, singleQuote, trailingComma

### Community 113 - "数据库设计"
Cohesion: 0.50
Nodes (3): ER 图, 数据库设计, 种子数据（`backend/app/seed.py`）

### Community 114 - "motion.ts"
Cohesion: 0.18
Nodes (9): dampHeading(), densitySpeedFactor(), REACTION_DELAY_SEC, sampleRange(), sampleReactionDelay(), sampleWalkSpeed(), serviceExitQueue(), trafficSpeedFactor() (+1 more)

### Community 115 - "vite.config.ts"
Cohesion: 0.25
Nodes (7): vite-plugin-static-copy@^2.2.0, vite@^5.4.11, @vitejs/plugin-vue@^5.2.1, srcDir, vite, vite-plugin-static-copy, @vitejs/plugin-vue

### Community 116 - "数据集目录"
Cohesion: 0.50
Nodes (3): 当前数据, 数据集目录, 目录约定

### Community 131 - "onReady"
Cohesion: 0.39
Nodes (12): crowd(), dispatchResponse(), populateCalmCity(), pushTimeline(), queueDrillSync(), refreshStats(), removeIncidentGraphic(), resetDrill() (+4 more)

### Community 132 - "TrafficState"
Cohesion: 0.23
Nodes (3): congestion_curve(), RoadLive, TrafficState

### Community 133 - "DataStatusChart.vue"
Cohesion: 0.27
Nodes (8): option, props, statuses, DATA_STATUS_META, DATA_STATUSES, DATA_TYPE_META, DATA_TYPES, dataStatusMeta()

### Community 135 - "cesium"
Cohesion: 0.14
Nodes (16): Region, beamAppearance(), buildingAppearance(), buildingVS(), encode(), f(), lineAppearance(), polylineVS() (+8 more)

### Community 136 - "export_snapshot.py"
Cohesion: 0.11
Nodes (8): client(), ctx(), tmp_root(), wait_task(), test_building_spatial_properties_can_be_maintained(), dump(), main(), main()

### Community 138 - "hazard.ts"
Cohesion: 0.36
Nodes (7): HAZARD_PROFILES, HazardProfile, hazardProfile(), hazardRadiusAt(), requiresPedestrianEvacuation(), smoothstep(), canEvacuate

### Community 139 - "eslint.config.js"
Cohesion: 0.29
Nodes (6): eslint-config-prettier@^9.1.2, eslint-plugin-vue@^9.33.0, typescript-eslint@^8.72.0, eslint-config-prettier, eslint-plugin-vue, typescript-eslint

### Community 140 - "cityeye_algo —— 城市智眼算法包"
Cohesion: 0.40
Nodes (3): cityeye_algo —— 城市智眼算法包, 使用, 测试

### Community 141 - "TaskHistory.vue"
Cohesion: 0.18
Nodes (9): emit, onRowClick(), page, props, rows, showAlgo, showProg, vw (+1 more)

### Community 142 - "config.py"
Cohesion: 0.26
Nodes (5): _bool(), _float(), _path(), Settings, main()

### Community 144 - "load"
Cohesion: 0.25
Nodes (8): autoCheck(), doUpload(), load(), loadValidations(), openDetail(), refresh(), reloadDetail(), submitValidation()

### Community 145 - "4. 行为与仿真"
Cohesion: 0.40
Nodes (5): 4.1 单人行为, 4.2 批量生成, 4.3 聚集与疏散, 4.4 Demo 级动态风险场, 4. 行为与仿真

### Community 146 - "DataTypeDistribution.vue"
Cohesion: 0.40
Nodes (5): emit, option, props, total, dataTypeMeta()

### Community 147 - "llm_module/__init__.py"
Cohesion: 0.14
Nodes (11): test_select(), test_select_errors(), test_validate_checks_csv_header(), answer_chat(), _build_prompt(), ChatTurn, FakeClient, FakeCompletions (+3 more)

### Community 151 - "sys"
Cohesion: 0.13
Nodes (4): load_system_prompt(), main(), test_cases_cover_all_supported_event_types(), test_prompt_contains_required_guardrails()

### Community 157 - "vitest"
Cohesion: 0.33
Nodes (3): vitest@^2.1.9, DRILL_SEEDS, vitest

### Community 158 - "pages/format.ts"
Cohesion: 0.20
Nodes (17): timeCost, fmtBytes(), fmtDuration(), fmtNum(), hexA(), isCsvUrl(), p2(), parseTs() (+9 more)

### Community 160 - "城市智眼业务闭环重构：第一阶段"
Cohesion: 0.29
Nodes (7): API, 公共支撑, 城市智眼业务闭环重构：第一阶段, 尚未完成, 数据资源画像, 状态机, 迁移与回滚

### Community 162 - "filtered"
Cohesion: 0.67
Nodes (3): filtered, matchesRadius(), timestampValue()

### Community 164 - "syncDrillRun"
Cohesion: 0.29
Nodes (7): createDrillReview(), drillMetrics(), drillSummary(), numberMetric(), renderIncident(), restoreDrillRun(), syncDrillRun()

### Community 171 - "onReady"
Cohesion: 0.29
Nodes (7): getDrillRun(), getScenarioSession(), eventToDrillSeed(), onReady(), radiusForType(), scenarioToDrillSeed(), setSimulationSpeed()

## Knowledge Gaps
- **49 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does ``MonitoringRun`` connect `城市智眼 API 契约（v1）` to `seed.py`?**
  _High betweenness centrality (0.202) - this node is a cross-community bridge._
- **Are the 48 inferred relationships involving `AppContext` (e.g. with `GeoRepository` and `_require_demo()`) actually correct?**
  _`AppContext` has 48 INFERRED edges - model-reasoned connections that need verification._
- **Should `ReviewBoard.vue` be split into smaller, more focused modules?**
  _Cohesion score 0.05647840531561462 - nodes in this community are weakly interconnected._
- **Why does `Task` connect `seed.py` to `schemas.py`, `城市智眼 API 契约（v1）`, `services/workflow.py`, `services/tasks.py`, `llm.py`, `AppContext`, `services/events.py`?**
  _High betweenness centrality (0.201) - this node is a cross-community bridge._
- **Should `EventDrawer.vue` be split into smaller, more focused modules?**
  _Cohesion score 0.08620689655172414 - nodes in this community are weakly interconnected._
- **Should `WorkflowPulse.vue` be split into smaller, more focused modules?**
  _Cohesion score 0.05725490196078432 - nodes in this community are weakly interconnected._
- **Should `@element-plus/icons-vue` be split into smaller, more focused modules?**
  _Cohesion score 0.05656565656565657 - nodes in this community are weakly interconnected._
