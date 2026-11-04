# CityEye 城市智能情景推演

## 实现边界

本模块负责自然语言理解、情景参数、版本、推演编排、时间帧展示、人群动画和报告。
以下能力只接收外部结果，不在本模块重写：

- 道路封闭、最短路和疏散路线规划
- 受影响路段专业计算
- 积水、交通流和火势物理模型
- 应急资源专业查询

当前使用 `MockScenarioProvider`，所有结果均标记为 `simulated`，仅用于流程和界面验证。

## 架构

```text
自然语言
  → DeepSeek Scenario Agent
  → ScenarioService（校验、演示默认值、版本）
  → MockScenarioProvider（未来可替换外部提供方）
  → 常规 / 不利 / 干预三套 ScenarioRun
  → Cesium 区域/道路 + Three.js 人群 + Vue 时间轴
  → ScenarioReport
```

后端：

- `scenario_engine/models.py`：参数、时间帧、运行结果和对比模型
- `scenario_engine/simulator.py`：明确标注的模拟提供方
- `scenario_engine/compare.py`：确定性差异计算
- `llm_module/scenario_agent.py`：自然语言到受控动作
- `llm_module/scenario_report.py`：结构化推演报告
- `backend/app/services/scenario.py`：会话、版本、运行和报告编排
- `backend/app/routers/scenario.py`：HTTP API

前端：

- `frontend/src/components/pages/ScenarioWorkspace.vue`：对话、参数、时间轴、对比和报告
- `frontend/src/components/scene/scenario/scenarioLayer.ts`：Cesium 风险区域与道路
- `frontend/src/components/scene/crowd/crowdLayer.ts`：Three.js 人群逐帧状态
- `frontend/src/api/scenario.ts`
- `frontend/src/types/scenario.ts`

## 交互与状态

Agent 只输出四类动作：

- `update`：新增或修改当前情景参数
- `run`：运行当前完整版本
- `compare`：对比两个已有运行
- `clarify`：信息不足时追问

参数不足时后端再次执行 Pydantic 校验，不能仅依赖模型自行判断。

前端一句话入口使用 `auto_run=true` 的演示模式。地点和事件类型必须可识别，
其余缺失参数由后端填入并在回复中列明：开始时间、持续时间、降雨强度、火灾规模、
人口规模、响应延迟和人口时段。缺地点时不做猜测，转为追问。

完整参数会自动生成三个确定性分支：

- 常规响应：使用补全后的基础参数；
- 不利响应：增加响应延迟、封闭出口和暴露人口；未显式指定的降雨、火灾半径或拥堵等级会向不利方向变化；
- 提前干预：缩短响应延迟、减少封闭出口，并降低未显式指定的危险强度。

每次参数修改生成新的不可变版本。原始版本保留，通过两次运行进行对比。

## API

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/api/scenario/status` | 模型与提供方状态 |
| POST | `/api/scenario/sessions` | 创建会话 |
| GET | `/api/scenario/sessions/{id}` | 获取会话、版本和最近结果 |
| POST | `/api/scenario/sessions/{id}/messages` | 自然语言更新/运行/对比；`auto_run=true` 自动补全并生成三方案 |
| POST | `/api/scenario/sessions/{id}/runs` | 运行当前版本 |
| POST | `/api/scenario/sessions/{id}/runs/variants` | 重跑当前版本并返回三套可能结果 |
| GET | `/api/scenario/runs/{id}` | 获取时间帧 |
| POST | `/api/scenario/sessions/{id}/compare` | 比较两次运行 |
| POST | `/api/scenario/runs/{id}/report` | 生成结构化报告 |

## 数据性质

| 标记 | 含义 |
|---|---|
| `real` | 真实观测数据 |
| `professional_analysis` | 其他专业模块提供的分析结果 |
| `simulated` | 明确标注的模拟结果 |
| `llm_inference` | 大模型基于已知信息的推断 |
| `unknown` | 来源或结论未知 |

当前三场景数值和人员轨迹均为 `simulated`。报告不会被描述为真实预测。

## 三场景

- 强降水与内涝：降雨强度、持续时间、积水深度和风险区域随时间变化。
- 交通拥堵：拥堵程度、持续时间和 TPI 时间帧；修改参数后创建版本并对比。
- 火灾：危险半径、人员数量和疏散时间帧；最多模拟 500 名人员。

三场景现在都会返回人员逐帧位置：火灾和内涝生成疏散过程，交通拥堵生成周边驻留人员，
用于展示事件对城市场景的空间影响。所有人数、位置和状态仍明确标记为模拟数据。

## 三维联动

- Cesium：危险区多边形（兼容圆形）、受影响道路高亮、风险颜色和镜头定位。
- Three.js：`setFramePeople` 将后端时间帧中的经纬度同步到实例化火柴人。
- Vue：播放、暂停、重置、时间轴拖动、指标和对比。

播放器只播放后端返回的时间帧，不生成写死动画。

风险区域优先使用外部提供方返回的 `polygon`，前端直接绘制 Cesium Polygon；
未提供多边形时继续兼容 `radius_m` 圆形区域。

模拟火灾人员移动包含：

- 2—6 条模拟走廊及每分钟通行容量；
- 未获准进入走廊的人员保持排队；
- 逐帧位置按 1.4 米最小间距做一次确定性分离；
- 拥挤排队和人员疏散数量写入帧指标。

这些是轻量演示机制，不是道路通行能力分析或踩踏模型。

## 外部提供方预留

后续空间分析模块需要提供：

- `zones`：经纬度、半径或多边形、风险级别
- `affected_building_ids`
- `affected_road_ids`
- `evacuation_paths`
- `frames` 或可按时段推算的时间序列
- `provider`、`data_classification`、`limitations`

当前 `MockScenarioProvider` 可直接替换，无需改前端协议。

## 验证

- 情景引擎测试：模拟帧、缺少参数、参数归一化和对比
- 后端测试：会话创建、自然语言运行、缺少参数追问、一句话自动补全和三方案生成
- 真实 DeepSeek：内涝创建、修改持续时间和再运行、版本对比、报告
- 真实 DeepSeek 一句话：自动补齐暴雨参数，返回 300 人、6 个时间帧和三套方案
- 浏览器：三方案卡片、参数卡片、时间轴、地图联动和报告展示
