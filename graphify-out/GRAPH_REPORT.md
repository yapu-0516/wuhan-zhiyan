# Graph Report - CityEye  (2026-11-09)

## Corpus Check
- 272 files · ~145,961 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 31 file(s) not represented in the graph (top: .csv 14, (none) 8, .geojson 4)

## Summary
- 3163 nodes · 7304 edges · 151 communities (120 shown, 31 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 406 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `bae976bf`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- generate_samples.py
- EventDrawer.vue
- EventDrawer.vue
- types/api.ts
- scenario_engine/models.py
- Dashboard.vue
- EmergencyDrill.vue
- EventTable.vue
- AnalysisResult
- BuildingSafetyPanel.vue
- CesiumViewer.vue
- TaskInputPanel.vue
- services/events.py
- numpy
- AssistantChatPanel.vue
- EventCenter.vue
- scene/types.ts
- useOverview.ts
- select
- LLMError
- DataManagement.vue
- routers/tasks.py
- EventDrawer.vue
- TrafficPanel.vue
- vue
- AppContext
- schemas.py
- download_satellite_basemap.py
- main.py
- steps
- crowdLayer.ts
- tool_runner.py
- build_geo.py
- CrowdLayer
- ScenarioWorkspace.vue
- eventLayer.ts
- EventDetail.vue
- TrafficSeriesAnalyzer
- types/event.ts
- roadLayer.ts
- build_wuhan_buildings.py
- test_llm_api.py
- 武汉智眼首批数据集确定方案_dd680806.md
- test_api.py
- SceneApi
- with
- 城市智眼 API 契约（v1）
- roadGraph.ts
- CrowdSimulationPanel.vue
- AssistantChatPanel.vue
- building.ts
- compilerOptions
- pytest
- report_generator.py
- Simulator
- llm.py
- _EventBuilder
- CityEye 城市虚拟人群仿真模块
- parse_task
- TaskSeriesChart.vue
- CameraController
- argparse
- GeoRepository
- buildingLayer.ts
- BasemapKey
- ScenarioParameters
- config.py
- cityeye
- AIAnalysis.vue
- SampleRepository
- types/scenario.ts
- 规格：CityEye 前端渐进式改进（第 1 批）
- select
- 城市智眼 · 算法说明
- scenario_agent.py
- 城市智眼 · CityEye
- test_fire.py
- numpy
- types/scenario.ts
- CityEye 大模型模块压缩交接
- backend/tests/conftest.py
- README.md
- numpy
- Settings
- Monitoring.vue
- useDemoTour
- AnalysisResult
- package.json
- scene/geo.ts
- LandmarkLayer
- CityEye 大模型模块
- CityEye 城市智能情景推演
- .session
- .lonLatToLocal
- EChart.vue
- 回答格式
- services/scenario.py
- compilerOptions
- building.ts
- 系统架构
- SceneRenderer
- 城市应急演练
- CityEye 界面设计说明
- AppHeader.vue
- test_registry.py
- pathlib
- pages/format.ts
- 3. 城市三维对象
- 2. 改动清单
- export_snapshot.py
- .prettierrc.json
- 数据库设计
- Region
- TaskProgress.vue
- 数据集目录
- dev.sh
- manifests/README.md
- basemap/README.md
- demo.sh
- BuildingPanel.vue
- 4. 行为与仿真
- EventCreateDialog.vue
- env.d.ts
- test_scenario_agent.py
- todayPrefix
- timeutil.py
- shaders.ts
- SensorPanel.vue
- useTaskRunner.ts
- diffFlash
- applyQuery
- ExternalAnalysisUnavailable
- filterQuery

## God Nodes (most connected - your core abstractions)
1. `AppContext` - 77 edges
2. `CrowdLayer` - 73 edges
3. `vue` - 59 edges
4. `LLMError` - 45 edges
5. `Settings` - 43 edges
6. `request()` - 39 edges
7. `AnalysisResult` - 37 edges
8. `EventType` - 34 edges
9. `CityEvent` - 33 edges
10. `select()` - 31 edges

## Surprising Connections (you probably didn't know these)
- `3. 关键接口` --references--> `CrowdLayer`  [INFERRED]
  docs/crowd-simulation.md → frontend/src/components/scene/crowd/crowdLayer.ts
- `3.1 SettleWatch · 沉降监测（`building.py`）` --references--> `SettlementThresholds`  [INFERRED]
  docs/algorithms.md → algorithm/cityeye_algo/building.py
- `外部提供方预留` --references--> `MockScenarioProvider`  [INFERRED]
  docs/scenario-simulation.md → scenario_engine/simulator.py
- `实现边界` --references--> `MockScenarioProvider`  [INFERRED]
  docs/scenario-simulation.md → scenario_engine/simulator.py
- `关键约束` --references--> `_call_llm()`  [INFERRED]
  llm_module/HANDOFF.md → backend/app/routers/llm.py

## Import Cycles
- 3-file cycle: `algorithm/cityeye_algo/__init__.py -> algorithm/cityeye_algo/registry.py -> algorithm/cityeye_algo/building.py -> algorithm/cityeye_algo/__init__.py`
- 3-file cycle: `algorithm/cityeye_algo/__init__.py -> algorithm/cityeye_algo/registry.py -> algorithm/cityeye_algo/fire.py -> algorithm/cityeye_algo/__init__.py`
- 3-file cycle: `algorithm/cityeye_algo/__init__.py -> algorithm/cityeye_algo/registry.py -> algorithm/cityeye_algo/flood.py -> algorithm/cityeye_algo/__init__.py`
- 3-file cycle: `algorithm/cityeye_algo/__init__.py -> algorithm/cityeye_algo/registry.py -> algorithm/cityeye_algo/traffic.py -> algorithm/cityeye_algo/__init__.py`

## Communities (151 total, 31 thin omitted)

### Community 0 - "generate_samples.py"
Cohesion: 0.15
Nodes (20): finish(), grade(), anchor(), ar_noise(), building_by_name(), building_pick(), building_samples(), diurnal_congestion() (+12 more)

### Community 1 - "EventDrawer.vue"
Cohesion: 0.09
Nodes (25): evidence, evidence, activeAnn, annotated, color, confPct, detected, detections (+17 more)

### Community 2 - "EventDrawer.vue"
Cohesion: 0.07
Nodes (16): Base, make_engine(), make_session_factory(), is_generic_name(), init_data(), AppMeta, DataAsset, ScenarioRunRecord (+8 more)

### Community 3 - "types/api.ts"
Cohesion: 0.08
Nodes (26): option, props, broken, emit, KIND, connect(), connected, Handler (+18 more)

### Community 4 - "scenario_engine/models.py"
Cohesion: 0.16
Nodes (11): ImpactZone, PeopleState, ScenarioDraft, ScenarioFrame, ScenarioRun, SpatialAnalysisProvider, _ambient_people(), _evacuation_people() (+3 more)

### Community 5 - "Dashboard.vue"
Cohesion: 0.04
Nodes (46): resetDemo(), askAssistantDemo(), assistantDemoQuestion, assistantOpen, assistantRef, autoTrack, basemap, { calm: calmBaseline, demoEventIds, enterCalmBaseline, revealAnomalies, setDemoEventIds } (+38 more)

### Community 6 - "EmergencyDrill.vue"
Cohesion: 0.05
Nodes (59): HAZARD_PROFILES, HazardProfile, hazardProfile(), hazardRadiusAt(), requiresPedestrianEvacuation(), smoothstep(), accent, actionText (+51 more)

### Community 7 - "EventTable.vue"
Cohesion: 0.09
Nodes (18): emit, onRowClick(), onSortChange(), props, showAssignee, showSource, SortState, vw (+10 more)

### Community 8 - "AnalysisResult"
Cohesion: 0.12
Nodes (14): assess_settlement(), ChangeDetector, ChangeParams, SettlementReport, SettlementThresholds, test_accelerating_settlement_is_warning(), test_change_detection_finds_new_structure(), test_change_detection_ignores_illumination() (+6 more)

### Community 9 - "BuildingSafetyPanel.vue"
Cohesion: 0.08
Nodes (21): BASE, chart, el, props, bProps, CATEGORY, chart, counts (+13 more)

### Community 10 - "CesiumViewer.vue"
Cohesion: 0.05
Nodes (56): getBuildingDistricts(), active, alarmBuildingIds(), api, bindInteraction(), bindRenderErrorRecovery(), chooseDistrict(), closePanels() (+48 more)

### Community 12 - "TaskInputPanel.vue"
Cohesion: 0.08
Nodes (30): findRiskBuilding(), allowedExt, createEvent, emit, fileList, latitude, loadingSamples, longitude (+22 more)

### Community 13 - "services/events.py"
Cohesion: 0.10
Nodes (17): Event, EventLog, get_event(), get_logs(), patch_event(), post_event(), EventPatch, add_log() (+9 more)

### Community 14 - "numpy"
Cohesion: 0.09
Nodes (26): blur(), box_mean(), box_sum(), closing(), dilate(), erode(), label_components(), load_rgb() (+18 more)

### Community 15 - "AssistantChatPanel.vue"
Cohesion: 0.08
Nodes (34): chatWithAssistant(), generateEventReport(), llmRequest(), parseTaskText(), select(), busy, error, KIND_META (+26 more)

### Community 16 - "EventCenter.vue"
Cohesion: 0.05
Nodes (29): activeOnly, createVisible, drawerId, drawerOpen, FILTER_KEYS, flash, hasFilter, keyword (+21 more)

### Community 17 - "scene/types.ts"
Cohesion: 0.21
Nodes (9): BASEMAP_OPTIONS, emit, LAYERS, emit, DEFAULT_LAYERS, LayerKey, LayerVisibility, TourFocus (+1 more)

### Community 18 - "useOverview.ts"
Cohesion: 0.12
Nodes (28): metrics, { calm, demoEventIds }, { connected, lastMessageAt }, displayStats, lastUpdate, MODE_LABEL, pad(), { stats, events, revision } (+20 more)

### Community 19 - "select"
Cohesion: 0.10
Nodes (13): InputError, damped_holt(), fmt_t(), median_step_minutes(), moving_average(), parse_times(), read_header(), read_table() (+5 more)

### Community 20 - "LLMError"
Cohesion: 0.13
Nodes (13): main(), ask(), _client(), LLMError, main(), FakeClient, FakeCompletions, settings() (+5 more)

### Community 21 - "DataManagement.vue"
Cohesion: 0.06
Nodes (32): uploadData(), emit, byType, derivedByType, doUpload(), filtered, keyword, list (+24 more)

### Community 22 - "routers/tasks.py"
Cohesion: 0.11
Nodes (19): bad_request(), Task, upload_data(), _check_type(), get_task(), list_tasks(), _parse_float(), post_task() (+11 more)

### Community 23 - "EventDrawer.vue"
Cohesion: 0.07
Nodes (28): getEvent(), ACTION_META, actionLabel(), ASSIGNEES, copyCoord(), currentId, emit, ensureEvent() (+20 more)

### Community 24 - "TrafficPanel.vue"
Cohesion: 0.15
Nodes (16): gauge, groups, level, levelCounts, meta, props, top10, totalRoads (+8 more)

### Community 25 - "vue"
Cohesion: 0.05
Nodes (34): dependencies, element-plus@^2.9.0, @element-plus/icons-vue@^2.3.1, vue@^3.5.13, vue-router@^4.5.0, isDrill, route, { sidebarCollapsed } (+26 more)

### Community 26 - "AppContext"
Cohesion: 0.13
Nodes (25): AppContext, get_ctx(), not_found(), building_detail(), buildings(), fine_building_districts(), fine_buildings(), pois() (+17 more)

### Community 27 - "schemas.py"
Cohesion: 0.11
Nodes (31): _require_demo(), reset(), scenario(), AlgorithmInfoOut, AlgorithmOut, AnalysisTaskOut, BuildingDetailOut, BuildingMonitoringOut (+23 more)

### Community 28 - "download_satellite_basemap.py"
Cohesion: 0.17
Nodes (11): BBox, build_parser(), crop_window(), download_tile(), lat_to_tile_y(), lon_to_tile_x(), main(), parse_bbox() (+3 more)

### Community 29 - "main.py"
Cohesion: 0.06
Nodes (6): create_app(), _on_validation(), __getattr__(), _validation_message(), envelope(), RealtimeHub

### Community 30 - "steps"
Cohesion: 0.05
Nodes (38): defaults, runs-on, steps, concurrency, cancel-in-progress, group, run, environment (+30 more)

### Community 31 - "crowdLayer.ts"
Cohesion: 0.09
Nodes (29): three@^0.187.0, CrowdPerson, EXIT_CAPACITIES, EXIT_LABELS, HazardState, installGaitShader(), makeStickFigureGeometry(), makeVehicleGeometry() (+21 more)

### Community 32 - "tool_runner.py"
Cohesion: 0.16
Nodes (15): get_demo_event(), list_demo_facilities(), build_input(), main(), ScriptedClient, ScriptedCompletions, test_execute_known_and_unknown_tool(), test_invalid_tool_arguments_are_returned_to_model() (+7 more)

### Community 33 - "build_geo.py"
Cohesion: 0.17
Nodes (19): build_buildings(), build_pois(), build_roads(), length(), classify(), clip_chain(), dist_m(), district_of() (+11 more)

### Community 35 - "ScenarioWorkspace.vue"
Cohesion: 0.06
Nodes (43): createScenarioSession(), sendScenarioMessage(), applyPeople(), busy, classLabel(), comparison, currentFrame, currentRadius (+35 more)

### Community 36 - "eventLayer.ts"
Cohesion: 0.08
Nodes (23): Alert, ALWAYS, beamInstance(), circlePositions(), clusterBadge(), clusterColor(), clusterOutlineInstance(), ellipseFillInstance() (+15 more)

### Community 37 - "EventDetail.vue"
Cohesion: 0.08
Nodes (26): getEventLogs(), assignee, assigneeOptions, busy, confidence, demoDispatch(), dispatchOpen, dispatchTarget (+18 more)

### Community 38 - "TrafficSeriesAnalyzer"
Cohesion: 0.25
Nodes (11): network_tpi(), tpi_level(), TrafficSeriesAnalyzer, _series(), test_csv_missing_column(), test_free_flow_series_not_congested(), test_sample_csv_has_two_peaks(), test_short_dip_below_min_duration_ignored() (+3 more)

### Community 39 - "types/event.ts"
Cohesion: 0.06
Nodes (54): 2. 事件, `CityEvent`, `EventLog`, `GET /api/events`, `GET /api/events/{id}` → `CityEvent`（404 不存在）, `GET /api/events/{id}/logs` → `EventLog[]`（按时间正序）, `PATCH /api/events/{id}`, `POST /api/events`（人工上报 / 市民上报） (+46 more)

### Community 40 - "roadLayer.ts"
Cohesion: 0.11
Nodes (14): LonLat, alphaOf(), flowSpeedByte(), LEVEL_COLORS, linesOf(), RoadLayer, RoadPart, RoadRecord (+6 more)

### Community 41 - "build_wuhan_buildings.py"
Cohesion: 0.28
Nodes (9): bounds(), centroid(), compact_json(), district_of(), grid_of(), load_district_segments(), main(), point_in_segments() (+1 more)

### Community 42 - "test_llm_api.py"
Cohesion: 0.11
Nodes (16): parsed_task(), report(), test_chat_attaches_seeded_event_context(), test_chat_rejects_invalid_history(), test_chat_without_event_context(), fake_chat(), test_llm_status_availability_is_environment_independent(), test_parse_task_rejects_invalid_length() (+8 more)

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
Nodes (21): 0. 通用约定, 10. WebSocket `/api/ws`, 11. 城市智能情景推演, 1. 系统, 4. 统计, 5. 数据资产, 7. 监测数据源, 8. 演示控制（demo_mode=true 时可用） (+13 more)

### Community 48 - "roadGraph.ts"
Cohesion: 0.13
Nodes (10): GraphEdge, GraphLine, GraphPoint, hazardPenalizedCost(), MinHeap, PlannedRoute, pointDistance(), projectOnSegment() (+2 more)

### Community 49 - "CrowdSimulationPanel.vue"
Cohesion: 0.10
Nodes (19): benchmark, busy, clearPeople(), count, dangerRadius, emptyEvacuation, emptyStats, evacuate() (+11 more)

### Community 50 - "AssistantChatPanel.vue"
Cohesion: 0.11
Nodes (15): AnswerBlock, busy, canSend, dataType, emit, error, input, linked (+7 more)

### Community 51 - "building.ts"
Cohesion: 0.13
Nodes (14): cache, emojiSupported(), EVENT_GLYPH, eventIcon(), POI_COLOR, POI_EMOJI, POI_GLYPH, poiIcon() (+6 more)

### Community 52 - "compilerOptions"
Cohesion: 0.09
Nodes (21): compilerOptions, allowImportingTsExtensions, baseUrl, isolatedModules, jsx, lib, module, moduleDetection (+13 more)

### Community 53 - "pytest"
Cohesion: 0.11
Nodes (15): AnalysisResult, FloodThresholds, WaterLevelAnalyzer, WaterSegmenter, WaterSegParams, Bars, _storm(), test_csv_samples() (+7 more)

### Community 54 - "report_generator.py"
Cohesion: 0.18
Nodes (13): AnalysisFinding, CityEventReport, EventOverview, generate_report(), load_report_prompt(), ReportError, RiskAssessment, FakeClient (+5 more)

### Community 55 - "Simulator"
Cohesion: 0.10
Nodes (8): lifespan(), health(), random_site(), Simulator, now(), test_lifecycle_advances_and_respects_state_machine(), test_patrol_creates_events_only_on_detection(), test_traffic_tick_and_events()

### Community 56 - "llm.py"
Cohesion: 0.21
Nodes (13): _call_llm(), ChatIn, ChatMessageIn, _distance_m(), _event_data_nature(), _event_view(), llm_status(), _load_event_context() (+5 more)

### Community 58 - "CityEye 城市虚拟人群仿真模块"
Cohesion: 0.12
Nodes (16): 1.1 选型结论, 1.2 坐标系, 1. 技术融合方案, 2.1 人物模型, 2.2 实例化策略, 2. 模块架构, 3. 关键接口, 5. 分阶段实现清单 (+8 more)

### Community 59 - "parse_task"
Cohesion: 0.14
Nodes (17): test_parse_task_retries_one_malformed_model_output(), flaky_parse(), Settings, generate_scenario_report(), HybridReportError, ScenarioReport, main(), _decode_json() (+9 more)

### Community 60 - "TaskSeriesChart.vue"
Cohesion: 0.12
Nodes (21): metrics, metrics, EXTRA_COLORS, extraKeys, MAIN_NAME, option, props, Series (+13 more)

### Community 61 - "CameraController"
Cohesion: 0.15
Nodes (5): CameraController, wait(), FlyOptions, OrbitOptions, DEFAULT_REGION

### Community 62 - "argparse"
Cohesion: 0.24
Nodes (10): distance_m(), district_in_text(), main(), merge(), search(), valid_name(), main(), parse_bbox() (+2 more)

### Community 63 - "GeoRepository"
Cohesion: 0.09
Nodes (6): base_road_name(), GeoRepository, Road, congestion_curve(), RoadLive, TrafficState

### Community 64 - "buildingLayer.ts"
Cohesion: 0.10
Nodes (15): buildingColor(), BuildingLayer, BuildingRecord, extrude(), frameNumberOf(), HEIGHT_STOPS, nextFrame(), polygonsOf() (+7 more)

### Community 65 - "BasemapKey"
Cohesion: 0.21
Nodes (9): BasemapController, GLOBE_BASE_COLOR, STYLE, BasemapConfig, BasemapKey, BASEMAPS, CESIUM_ION_TOKEN, DEFAULT_BASEMAP (+1 more)

### Community 66 - "ScenarioParameters"
Cohesion: 0.23
Nodes (8): missing_fields(), ScenarioParameters, MockScenarioProvider, test_chinese_parameter_values_are_normalized(), test_fire_people_progress_and_compare(), test_flood_frames_are_marked_simulated(), test_flood_missing_information(), test_traffic_frames_use_requested_level()

### Community 67 - "config.py"
Cohesion: 0.26
Nodes (5): _bool(), _float(), _path(), Settings, main()

### Community 68 - "cityeye"
Cohesion: 0.11
Nodes (17): build, container_name, environment, image, ports, restart, volumes, CITYEYE_DEMO_MODE (+9 more)

### Community 69 - "AIAnalysis.vue"
Cohesion: 0.10
Nodes (28): jsonBody(), nowString(), createTask(), getSamples(), prototypeTask(), uploadTask(), algorithms, center (+20 more)

### Community 71 - "types/scenario.ts"
Cohesion: 0.13
Nodes (18): ApiError, compareScenarioRuns(), generateScenarioReport(), runCurrentScenarioVariants(), scenarioRequest(), compare(), makeReport(), runAgain() (+10 more)

### Community 72 - "规格：CityEye 前端渐进式改进（第 1 批）"
Cohesion: 0.18
Nodes (9): 1. 现状结论（已核实）, 3. 明确不做（本轮）, 4. 验证计划, 5. 风险与回退, 规格：CityEye 前端渐进式改进（第 1 批）, 任务清单：CityEye 前端渐进式改进（第 1 批）, 实施任务, 已知限制 (+1 more)

### Community 73 - "select"
Cohesion: 0.15
Nodes (4): select(), list_events(), source_to_dict(), SourceState

### Community 74 - "城市智眼 · 算法说明"
Cohesion: 0.15
Nodes (13): 1. 火灾 · FlameNet-Lite（`fire.py`）, 2.1 TrafficPulse · 时序路况（`traffic.py`）, 2.2 RoadOcc · 航拍路面车辆占有率, 2. 交通, 3.1 SettleWatch · 沉降监测（`building.py`）, 3.2 ChangeScope · 前后时相变化检测, 3. 建筑, 4.1 AquaLevel · 积水监测时序（`flood.py`） (+5 more)

### Community 75 - "scenario_agent.py"
Cohesion: 0.23
Nodes (7): agent_output(), test_compare_does_not_require_current_parameters(), test_demo_auto_run_fills_assumptions_and_builds_three_variants(), test_scenario_missing_parameters_are_reported(), test_scenario_session_and_run(), converse(), ScenarioAgentOutput

### Community 76 - "城市智眼 · CityEye"
Cohesion: 0.12
Nodes (17): 🔌 API 一览, ✨ 亮点, 🕸️ 代码图谱, 🗺️ 功能导览, 城市智眼 · CityEye, 🚀 快速开始, 📚 数据来源与致谢, 方式一：Docker（推荐，一条命令） (+9 more)

### Community 77 - "test_fire.py"
Cohesion: 0.16
Nodes (9): FireDetector, FireParams, det(), test_plain_city_not_detected(), test_procedural_flame_detected(), test_red_roofs_and_orange_car_not_detected(), test_samples_negative(), test_samples_positive() (+1 more)

### Community 78 - "numpy"
Cohesion: 0.17
Nodes (14): add_collapse(), add_fire(), add_flood(), add_new_structure(), add_street_lights(), _gradient(), ip_dilate(), _point_in_poly() (+6 more)

### Community 79 - "types/scenario.ts"
Cohesion: 0.18
Nodes (9): PREVIOUS_EDGE, RISK_COLOR, ScenarioLayer, WATER_BODY, WATER_EDGE, ScenarioFrame, ScenarioRisk, ScenarioType (+1 more)

### Community 80 - "CityEye 大模型模块压缩交接"
Cohesion: 0.13
Nodes (14): 1. DeepSeek API, 2. CityEye 系统提示词, 3. 自然语言任务解析, 4. Tool Calling, 5. 结构化报告, CityEye 大模型模块压缩交接, Git 状态, 下一步 (+6 more)

### Community 81 - "backend/tests/conftest.py"
Cohesion: 0.23
Nodes (4): client(), ctx(), tmp_root(), wait_task()

### Community 82 - "README.md"
Cohesion: 0.15
Nodes (5): cityeye_algo —— 城市智眼算法包, 使用, 测试, 5 分钟路演脚本, 演示备忘

### Community 83 - "numpy"
Cohesion: 0.19
Nodes (5): city_background(), paint_flame(), rng(), sample(), save()

### Community 84 - "Settings"
Cohesion: 0.15
Nodes (12): answer_chat(), _build_prompt(), ChatTurn, load_system_prompt(), main(), FakeClient, FakeCompletions, test_chat_includes_history_and_event_context() (+4 more)

### Community 85 - "Monitoring.vue"
Cohesion: 0.06
Nodes (53): getDataList(), getDataStats(), getBuildings(), getFineBuildings(), getPois(), getRoads(), ApiMode, apiState (+45 more)

### Community 86 - "useDemoTour"
Cohesion: 0.35
Nodes (13): TourCancelled, useDemoTour(), cleanup(), guard(), onKey(), pickActiveEvent(), run(), runHook() (+5 more)

### Community 87 - "AnalysisResult"
Cohesion: 0.16
Nodes (5): Analyzer, _clean_metric(), run(), _run_batch(), validate()

### Community 88 - "package.json"
Cohesion: 0.05
Nodes (45): echarts@^5.6.0, vite-plugin-static-copy@^2.2.0, description, devDependencies, eslint@^9.39.5, eslint-config-prettier@^9.1.2, eslint-plugin-vue@^9.33.0, prettier@^3.9.10 (+37 more)

### Community 89 - "scene/geo.ts"
Cohesion: 0.54
Nodes (7): cleanRing(), distance(), isFiniteCoord(), lineLength(), lineMidpoint(), resampleLine(), ringAreaM2()

### Community 90 - "LandmarkLayer"
Cohesion: 0.18
Nodes (5): cesium@1.125.0, Landmark, LandmarkLayer, LANDMARKS, cesium

### Community 92 - "CityEye 大模型模块"
Cohesion: 0.17
Nodes (11): CityEye 大模型模块, Tool Calling 验证, 城市治理问答, 安装, 当前范围, 测试, 系统提示词测试, 结构化研判报告 (+3 more)

### Community 93 - "CityEye 城市智能情景推演"
Cohesion: 0.20
Nodes (10): API, CityEye 城市智能情景推演, 三场景, 三维联动, 交互与状态, 外部提供方预留, 实现边界, 数据性质 (+2 more)

### Community 94 - ".session"
Cohesion: 0.24
Nodes (7): ScenarioSession, _apply_demo_defaults(), _new_id(), _now(), ScenarioService, _timestamp(), ScenarioAgentError

### Community 96 - "EChart.vue"
Cohesion: 0.17
Nodes (13): option, props, statuses, emit, option, props, total, DATA_STATUS_META (+5 more)

### Community 97 - "回答格式"
Cohesion: 0.18
Nodes (10): CityEye 城市治理助手, 信息使用规则, 信息缺口, 分析, 回答格式, 安全规则, 已知信息, 建议 (+2 more)

### Community 98 - "services/scenario.py"
Cohesion: 0.33
Nodes (4): ScenarioVersion, compare_runs(), _risk_rank(), ScenarioComparison

### Community 99 - "compilerOptions"
Cohesion: 0.20
Nodes (9): compilerOptions, allowSyntheticDefaultImports, composite, module, moduleResolution, outDir, skipLibCheck, strict (+1 more)

### Community 100 - "building.ts"
Cohesion: 0.09
Nodes (23): grade, levelMeta, LEVELS, marker, option, props, emit, LEVELS (+15 more)

### Community 101 - "系统架构"
Cohesion: 0.22
Nodes (8): 1. 总体架构, 2.1 实时事件闭环, 2.2 AI 分析任务, 2. 关键数据流, 3. 三维场景设计, 4. 运行模式, 5. 扩展点, 系统架构

### Community 102 - "SceneRenderer"
Cohesion: 0.14
Nodes (9): BuildingShape, Corridor, _jitter(), procedural_buildings(), project_buildings(), Projector, SceneRenderer, base_scene() (+1 more)

### Community 103 - "城市应急演练"
Cohesion: 0.25
Nodes (7): Demo 演示增强, 事件种子, 交互闭环, 入口与实现, 城市应急演练, 定位, 数据边界

### Community 104 - "CityEye 界面设计说明"
Cohesion: 0.25
Nodes (8): CityEye 界面设计说明, 各页面问题, 应急演练页, 方向, 本轮调整, 真实城市视图中的事件层级, 设计边界, 验证

### Community 105 - "AppHeader.vue"
Cohesion: 0.20
Nodes (11): city, conn, { connected }, date, demoTip, everConnected, { info, region, demoMode, load }, now (+3 more)

### Community 106 - "test_registry.py"
Cohesion: 0.29
Nodes (3): test_select(), test_select_errors(), test_validate_checks_csv_header()

### Community 107 - "pathlib"
Cohesion: 0.10
Nodes (18): AlgorithmMeta, Artifact, clamp01(), Detection, SettlementAnalyzer, algorithms(), file_kind(), annotate_image() (+10 more)

### Community 108 - "pages/format.ts"
Cohesion: 0.27
Nodes (13): timeCost, fmtBytes(), fmtDuration(), fmtNum(), hexA(), isCsvUrl(), p2(), parseTs() (+5 more)

### Community 109 - "3. 城市三维对象"
Cohesion: 0.33
Nodes (6): 3. 城市三维对象, `GET /api/buildings/fine?district=武昌区` → GeoJSON `FeatureCollection<Polygon>`, `GET /api/buildings` → GeoJSON `FeatureCollection<Polygon>`, `GET /api/buildings/{id}` → 建筑详情, `GET /api/pois` → `[{ id, name, kind: "hospital"|"fire_station"|"police"|"school", longitude, latitude }]`, `GET /api/roads` → GeoJSON `FeatureCollection<LineString>`

### Community 110 - "2. 改动清单"
Cohesion: 0.33
Nodes (6): resetFilters(), 2. 改动清单, R1 表格响应式列断点修正, R2 事件表格空状态增加操作入口, R3 AI 分析页去除重复副标题, R4 Dashboard 事件流键盘可达 + 统一焦点环

### Community 111 - "export_snapshot.py"
Cohesion: 0.22
Nodes (3): dump(), main(), main()

### Community 112 - ".prettierrc.json"
Cohesion: 0.29
Nodes (6): arrowParens, endOfLine, printWidth, semi, singleQuote, trailingComma

### Community 113 - "数据库设计"
Cohesion: 0.40
Nodes (4): ER 图, 数据库设计, 种子数据（`backend/app/seed.py`）, 表说明

### Community 115 - "TaskProgress.vue"
Cohesion: 0.12
Nodes (18): meta, active, color, failed, meta, percent, props, running (+10 more)

### Community 116 - "数据集目录"
Cohesion: 0.50
Nodes (3): 当前数据, 数据集目录, 目录约定

### Community 131 - "BuildingPanel.vue"
Cohesion: 0.13
Nodes (16): getBuilding(), b, CATEGORY, chartOption, detail, emit, error, HEIGHT_SOURCE (+8 more)

### Community 132 - "4. 行为与仿真"
Cohesion: 0.40
Nodes (5): 4.1 单人行为, 4.2 批量生成, 4.3 聚集与疏散, 4.4 Demo 级动态风险场, 4. 行为与仿真

### Community 133 - "EventCreateDialog.vue"
Cohesion: 0.09
Nodes (33): createEvent(), getEvents(), patchEvent(), snapshotEvents(), qs(), bbox, center, emit (+25 more)

### Community 135 - "env.d.ts"
Cohesion: 0.40
Nodes (4): ImportMeta, ImportMetaEnv, *.vue, Window

### Community 137 - "todayPrefix"
Cohesion: 0.50
Nodes (4): todayPrefix(), filtered, kpis, todayCount

### Community 139 - "timeutil.py"
Cohesion: 0.13
Nodes (11): asset_to_dict(), data_stats(), list_data(), stats_overview(), ws_endpoint(), overview(), safety_score(), human_size() (+3 more)

### Community 140 - "shaders.ts"
Cohesion: 0.10
Nodes (18): Region, AmbientEffects, beamAppearance(), buildingAppearance(), buildingVS(), encode(), f(), LINE_VERTEX_FORMAT (+10 more)

### Community 141 - "SensorPanel.vue"
Cohesion: 0.09
Nodes (18): props, shown, props, rate, ringOffset, rows, sources, totals (+10 more)

### Community 142 - "useTaskRunner.ts"
Cohesion: 0.20
Nodes (18): 6. AI 分析任务, `AnalysisTask`, `GET /api/samples?type=fire` → 示例数据, `GET /api/tasks` → `AnalysisTask[]`（按创建时间倒序）, `GET /api/tasks/{id}` → `AnalysisTask`, `POST /api/tasks`（JSON，兼容原型）, `POST /api/tasks/upload`（multipart）, getTask() (+10 more)

### Community 143 - "diffFlash"
Cohesion: 0.50
Nodes (4): diffFlash(), mark(), onCreated(), refresh()

### Community 144 - "applyQuery"
Cohesion: 1.00
Nodes (3): applyQuery(), initialType(), queryText()

## Knowledge Gaps
- **31 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `CityEye 城市虚拟人群仿真模块` connect `CityEye 城市虚拟人群仿真模块` to `README.md`, `4. 行为与仿真`?**
  _High betweenness centrality (0.218) - this node is a cross-community bridge._
- **Are the 43 inferred relationships involving `AppContext` (e.g. with `GeoRepository` and `TrafficState`) actually correct?**
  _`AppContext` has 43 INFERRED edges - model-reasoned connections that need verification._
- **Should `EventDrawer.vue` be split into smaller, more focused modules?**
  _Cohesion score 0.08620689655172414 - nodes in this community are weakly interconnected._
- **Why does `CrowdLayer` connect `CrowdLayer` to `EmergencyDrill.vue`, `CesiumViewer.vue`, `roadGraph.ts`, `CrowdSimulationPanel.vue`, `CityEye 城市虚拟人群仿真模块`, `.evacuate`, `crowdLayer.ts`, `.lonLatToLocal`?**
  _High betweenness centrality (0.216) - this node is a cross-community bridge._
- **Are the 16 inferred relationships involving `LLMError` (e.g. with `_call_llm()` and `llm_status()`) actually correct?**
  _`LLMError` has 16 INFERRED edges - model-reasoned connections that need verification._
- **Should `EventDrawer.vue` be split into smaller, more focused modules?**
  _Cohesion score 0.07337662337662337 - nodes in this community are weakly interconnected._
- **Why does `create_event()` connect `services/events.py` to `EventDrawer.vue`, `useTaskRunner.ts`, `SampleRepository`, `Simulator`?**
  _High betweenness centrality (0.206) - this node is a cross-community bridge._