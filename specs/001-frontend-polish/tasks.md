# 任务清单：CityEye 前端渐进式改进（第 1 批）

对应规格：[spec.md](./spec.md)

## 实施任务

- [x] T1 `frontend/src/components/pages/EventTable.vue`
  - [x] `showAssignee` 断点 1360 → 1500，`showSource` 断点 1500 → 1760（第 55–56 行）
  - [x] Props 增加 `hasFilter?: boolean`；Emits 增加 `reset`、`create`
  - [x] `#empty` 插槽改为 `el-empty` + 默认插槽按钮（清除筛选 / 上报事件）
  - [x] 导入 `RefreshLeft` 图标；新增 `.etable__empty` 样式
- [x] T2 `frontend/src/views/EventCenter.vue`
  - [x] `EventTable` 绑定 `:has-filter="hasFilter"`、`@reset="resetFilters"`、`@create="createVisible = true"`
- [x] T3 `frontend/src/views/DataManagement.vue`
  - [x] `showMore` 断点 1360 → 1400，`showFormat` 断点 1500 → 1600（第 21–22 行）
- [x] T4 `frontend/src/views/AIAnalysis.vue`
  - [x] 第 185 行 `PageShell` 的 `hint` 改为流程说明，移除与 hero 重复的 `curMeta.blurb`
- [x] T5 `frontend/src/components/dashboard/LiveFeed.vue`
  - [x] 列表项增加 `role="button"`、`tabindex="0"`、`aria-label`、`keydown.enter/space` 定位
- [x] T6 `frontend/src/assets/styles/main.css`
  - [x] 末尾追加键盘 `:focus-visible` 焦点环规则

## 验证任务

- [x] V1 `npm run typecheck` 通过（vue-tsc -b，退出码 0）
- [x] V2 `npm run lint` 通过（eslint .，退出码 0）
- [x] V3 `npm run build` 成功（3496 modules，17.75s）
- [x] V4 事件中心 @1440×900：可见 8 列（编号/类型/名称/等级/置信度/状态/发现时间/操作），无横向滚动；@1920×1080：额外显示「来源」「处置单位」，无横向滚动
- [x] V5 事件中心空状态：搜索无结果时出现「清除筛选」「上报事件」；清除筛选恢复列表；上报事件打开对话框
- [x] V6 Dashboard：`role=button`/`tabindex=0`/`aria-label` 已生效，无控制台 error，1440×900 下左右 HUD 与事件流无遮挡；Enter 触发定位未实测（浏览器工具视口固定 625×419，HUD 自动收起）
- [x] V7 数据管理 @1440：可见 8 列（名称/类型/来源/大小/记录数/获取时间/状态/操作），无横向滚动；@1920 全列显示
- [x] V8 `/ai-analysis/fire` 副标题为流程说明、与 hero 文案不重复；`/monitoring` 与其余 AI 子页无异常

## 已知限制

- 625×419 这类极窄视口下，数据管理表格仍会出现横向滚动（列宽下限合计 > 可用宽度），非本次改动引入。
- 后端未安装 FastAPI 依赖，live 模式未验证；本轮全部验证在 offline 快照模式下完成。
