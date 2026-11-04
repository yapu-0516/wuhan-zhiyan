# CityEye 大模型模块

当前实现第一、二阶段：通过 OpenAI 兼容 SDK 调用 DeepSeek，并加载
CityEye 专用系统提示词。该目录不依赖 CityEye 的前端、后端、算法或数据库。

## 安装

在项目根目录运行：

```powershell
.\.venv\Scripts\python.exe -m pip install -r llm_module\requirements.txt
```

## 配置

本地密钥保存在 `llm_module/.env`，该文件已被 Git 忽略。可从
`.env.example` 重新创建配置：

```text
DEEPSEEK_API_KEY=你的密钥
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_TIMEOUT_SECONDS=60
```

## 调用

```powershell
.\.venv\Scripts\python.exe -m llm_module.cli "用一句话介绍 CityEye"
```

也可以传入临时系统提示词：

```powershell
.\.venv\Scripts\python.exe -m llm_module.cli "什么是内涝？" --system "你是城市治理助手，只依据事实回答。"
```

## 测试

离线单元测试不会消耗额度：

```powershell
.\.venv\Scripts\python.exe -m pytest llm_module\tests -q
```

真实 API 连通性测试会产生一次很小的调用：

```powershell
.\.venv\Scripts\python.exe -m llm_module.smoke_test
```

成功时输出“连接成功”。

## 系统提示词测试

系统提示词位于 `prompts/cityeye_system.md`，测试案例位于
`prompt_cases.json`。运行全部案例会产生 4 次低成本模型调用：

```powershell
.\.venv\Scripts\python.exe -m llm_module.run_prompt_cases
```

只运行一个案例：

```powershell
.\.venv\Scripts\python.exe -m llm_module.run_prompt_cases --case fire-missing-details
```

## 自然语言任务解析

`task_parser.py` 将自然语言转换为经过 Pydantic 校验的 JSON。不会调用城市分析工具，
未知地点和时间保持为 `null`。

```powershell
.\.venv\Scripts\python.exe -m llm_module.task_cli "帮我分析一起火灾的影响，重点关注周边医院和道路。"
```

## Tool Calling 验证

`demo_tools.py` 只有两条固定演示记录和两个查询函数，不连接城市数据库或算法。

```powershell
.\.venv\Scripts\python.exe -m llm_module.tool_cli "查询示例事件 DEMO-FIRE-001，并列出江汉路的医院。"
```

输出包含模型回答和实际执行的工具调用记录。无效事件编号、无效 JSON 参数和未知工具
都会作为错误结果返回给模型。

## 结构化研判报告

`report_generator.py` 使用固定示例事件和设施数据生成 Pydantic 严格校验的报告。

```powershell
.\.venv\Scripts\python.exe -m llm_module.report_cli
```

报告包含事件概况、分析目标、已知信息、分析结果、风险判断及依据、处置建议、
数据缺口与不确定性。示例数据不会被表述为真实事件。

## 城市治理问答

`chat.py` 使用 CityEye 系统提示词处理最多 8 轮受控问答，可关联一个现有事件，
把事件数据性质、已知缺口和周边设施作为上下文送入模型。该接口不执行工具，
也不会修改事件状态。

```powershell
.\.venv\Scripts\python.exe -m pytest llm_module\tests\test_chat.py -q
```

前端总览工具条的“AI 问答”已经接入 `/api/llm/chat`，仅在用户发送时调用付费 API。

## 当前范围

- 已实现：DeepSeek API 调用、系统提示词、任务解析、Tool Calling 验证、结构化报告、
  多轮城市治理问答，以及 CityEye 前后端集成。
- 空间推演仍使用明确标记的模拟提供方，不把演示结果表述为真实专业分析。
- 不依赖其他队员提供的代码、数据或接口。
