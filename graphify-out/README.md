# CityEye Graphify 代码知识图谱

生成时间：2026-11-06
代码基线：当前演示工作区

## 图谱规模

- 3092 个节点
- 7201 条边（6765 条 EXTRACTED，436 条 INFERRED）
- 136 个社区
- 267 个代码文件
- 0 个外部模型 Token

## 产物

- `graph.html`：可离线打开的交互式图谱
- `CALLFLOW.html`：按模块生成的调用流程与 Mermaid 架构图
- `GRAPH_REPORT.md`：图谱审计、核心枢纽、跨社区连接与建议问题
- `graph.json`：可供后续查询或 GraphRAG 使用的持久化图谱
- `community_labels.json`：136 个社区的中文标签
- `obsidian/`：Obsidian Vault 和 `graph.canvas`

## 查询

```powershell
graphify query "城市情景推演从自然语言到三维回放经过哪些模块" --budget 2000
graphify explain "AppContext"
graphify path "parse_task" "CrowdLayer" --undirected
graphify affected "AppContext"
```

代码变化后可增量更新，不需要调用大模型：

```powershell
graphify update .
```

## 当前范围

本次以本地 AST 代码抽取为主，覆盖 `frontend`、`backend`、`llm_module`、
`scenario_engine`、`algorithm`、`data` 和 `scripts`。文档与演示图片未做语义抽取，
因此不计入 Token 成本；`database/schema.sql` 因缺少 Graphify 的 SQL 解析插件未入图。

`CALLFLOW.html` 的 Mermaid 渲染脚本引用公共 CDN；`graph.html` 本身可直接离线打开。
