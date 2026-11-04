# CityEye 大模型模块压缩交接

## 会话目标

用户是武汉大学遥感专业大一学生，希望在 CityEye 中独立完成大模型与智能体基础模块。
要求使用成熟、简单、低成本的 Python 方案，按阶段验证，不依赖其他队员提供算法、数据、
接口或调试。当前阶段不修改真实城市分析算法，不接入真实 GIS/数据库，也不做团队联调。

项目路径：

`C:\Users\Wangyingpu\Desktop\武汉智眼\CityEye`

## 已完成

### 1. DeepSeek API

- 使用 OpenAI 兼容 SDK 调用 `https://api.deepseek.com` 的 `deepseek-chat`。
- `client.py::ask()` 支持系统提示词、温度、最大 token 和 JSON response_format。
- 处理认证失败、限流、连接失败、HTTP 状态错误和空回答。
- 真实 API 调用返回“连接成功”。
- 密钥只在 `llm_module/.env`，已由仓库 `.gitignore` 忽略；其他文件未发现密钥。
- `.env.example` 提供无密钥模板。

### 2. CityEye 系统提示词

- 文件：`llm_module/prompts/cityeye_system.md`
- 案例：`llm_module/prompt_cases.json`
- 覆盖火灾、交通、建筑安全、内涝。
- 强制区分事实、推断、未知信息；禁止编造地点、数值、医院、道路和风险等级。
- 4 个真实模型案例均符合要求，信息不足时会主动询问。

### 3. 自然语言任务解析

- 文件：`llm_module/task_parser.py`
- 提示词：`llm_module/prompts/task_parser_system.md`
- Pydantic 模型：`ParsedTask`
- 输出字段：`event_type`、`analysis_targets`、`location`、`event_time`、
  `extracted_facts`、`missing_information`、`needs_clarification`。
- 缺地点/时间时输出 `null`；非法 JSON 和未知枚举值会被拒绝。
- 实测“帮我分析一起火灾……”得到 `fire`、3 个分析目标、地点/时间为 `null`。

### 4. Tool Calling

- 文件：`llm_module/tool_runner.py`
- 固定工具：`llm_module/demo_tools.py`
- 工具：`get_demo_event`、`list_demo_facilities`
- 已真实验证模型主动调用两个工具、读取结果并回答。
- 无效事件编号会返回工具错误，模型如实说明未找到。
- 无效 JSON 参数和未知工具也会作为错误返回模型。

### 5. 结构化报告

- 文件：`llm_module/report_generator.py`
- 提示词：`llm_module/prompts/report_system.md`
- Pydantic 模型：`CityEventReport`
- 包含事件概况、分析目标、已知信息、事实/推断/未知、风险依据、建议、数据缺口。
- 实测示例事件报告正确标注“示例数据，不代表真实事件”，风险等级为 `unknown`。

## 新增的前后端桥接（已完成真实联调）

- `backend/app/routers/llm.py`
  - `GET /api/llm/status`：只检查密钥配置，不调用模型。
  - `POST /api/llm/parse-task`：调用 `parse_task`。
  - `POST /api/llm/chat`：最多 8 轮受控治理问答，可关联事件并携带数据性质、信息缺口和设施。
  - `POST /api/llm/report`：按事件 ID取现有事件及 1 km 内 POI、200 m 内道路后生成报告。
- `frontend/src/api/llm.ts`
- `frontend/src/types/llm.ts`
- `frontend/src/components/pages/TaskParsePanel.vue`
- `frontend/src/components/pages/EventReport.vue`
- `frontend/src/components/pages/AssistantChatPanel.vue`
- 总览工具条新增“AI 解析”，事件详情新增“AI 研判报告”。
- 总览工具条新增“AI 问答”，支持关联当前选中事件的多轮追问。
- 模型只在用户点击时调用，前端超时 90 秒。
- 事件报告不再统一标记为“真实监测事件”。后端按分析任务来源、示例标记、市民上报和
  合成/模拟描述判定数据性质，并在模型返回后覆盖报告中的 `data_classification` 与
  `event_overview.data_type`，避免模型误写。

## 当前验证状态

- `llm_module` 离线测试：21 passed。
- 后端、LLM、情景引擎联合离线测试：68 passed。
- 算法测试：53 passed。
- 前端 Vitest：29 passed。
- 前端生产构建：成功。
- DeepSeek 真实调用：API、提示词、任务解析、Tool Calling、报告均成功。
- 2026-10-31 已完成浏览器端“前端 → 后端 LLM 路由 → DeepSeek”真实点击联调：
  - “AI 解析”正确识别火灾、分析目标、地点、缺失信息；
  - “AI 问答”完成两轮连续对话，并按标题、段落正确呈现回答；
  - 事件详情成功生成结构化研判报告；
  - 演示事件报告显示“模拟器数据，不代表真实事件”，风险无法判断时保持 `unknown`；
  - 浏览器无控制台 error。
- `backend/tests/test_llm_api.py` 已覆盖状态检查、参数校验、一次自动重试、演示/市民上报
  数据性质、问答上下文、404 与模型服务 503。
- “AI 问答”在 390×844 视口验证无页面横向溢出，对话框完整落在视口内。

## Git 状态

- 云端最新提交：`acba433`，仓库为私有。
- 当前未提交：
  - 新增 `llm_module/`
  - 新增前后端 LLM 桥接文件
  - 修改 `backend/app/main.py`
  - 修改 `frontend/src/api/http.ts`
  - 修改 `frontend/src/components/dashboard/SceneToolbar.vue`
  - 修改 `frontend/src/components/pages/EventDrawer.vue`
  - 修改 `frontend/src/views/Dashboard.vue`
- `llm_module/.env` 不在 Git 状态中，已确认忽略。

## 关键约束

- 不开发火灾/交通/建筑/内涝分析算法。
- 不训练视觉模型。
- 不编造真实事件、地图、距离、风险数值或接口。
- 不提前开发依赖 B 同学算法的适配器。
- 前端不能直接持有 DeepSeek Key，只能调用自有后端。
- `/api/llm/report` 和 `/api/llm/chat` 均按任务来源、示例标记和上报来源保守判定数据性质，
  不得把演示事件表述为真实监测事件。
- `_call_llm` 遇到无效 JSON 会重试一次，因此该请求可能产生两次计费。
- 密钥曾在聊天中明文出现，上线或共享前应轮换。

## 下一步

1. 上线或共享前轮换曾在聊天中明文出现过的 API Key。
2. 复核未提交改动并提交；不要在未验证前把演示事件说成真实数据。

## 常用命令

```powershell
.\.venv\Scripts\python.exe -m pytest llm_module\tests -q
.\.venv\Scripts\python.exe -m llm_module.smoke_test
.\.venv\Scripts\python.exe -m llm_module.run_prompt_cases
.\.venv\Scripts\python.exe -m llm_module.task_cli "帮我分析一起火灾的影响"
.\.venv\Scripts\python.exe -m llm_module.tool_cli "查询示例事件 DEMO-FIRE-001"
.\.venv\Scripts\python.exe -m llm_module.report_cli
```
