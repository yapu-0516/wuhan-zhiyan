# 规格：CityEye 前端渐进式改进（第 1 批）

> 原则：在现有 Vue 3 + TS + Cesium + Element Plus 项目上做最小、可回退的增量修改；不新增依赖、不改路由、不改数据接口、不动 Cesium 场景与数据源。

## 1. 现状结论（已核实）

- 项目可运行：`frontend` 下 `npm run dev -- --port 5173` 已启动，`http://localhost:5173` 返回 200。
- 基线质量：`npm run typecheck`、`npm run lint` 当前均通过。
- 后端未安装 FastAPI 依赖，本轮验证在 **offline 快照模式**（`public/snapshot`）下进行；live 模式无法验证。
- 已确认的真实问题（有代码/算术依据）：
  1. 事件中心表格在 1366–1720 视口列宽合计 > 内容宽，出现横向滚动，表头与内容错位。
  2. 数据管理表格在 1366–1440 视口轻微横向溢出。
  3. 事件中心筛选无结果时只有提示文字，无任何恢复操作。
  4. AI 分析页副标题与页面内 hero 区文案完全重复。
  5. Dashboard 实时事件流列表项仅支持鼠标点击，键盘不可达，全站无统一焦点环。

## 2. 改动清单

### R1 表格响应式列断点修正

**文件 A：`frontend/src/components/pages/EventTable.vue`（第 55–56 行）**

```ts
const showSource = computed(() => vw.value >= 1760)   // 原 1500
const showAssignee = computed(() => vw.value >= 1500) // 原 1360
```

依据（内容宽 ≈ 视口宽 − 侧栏 200 − 页面内边距 ≈ 40）：

| 可见列组合 | 合计宽 |
| --- | --- |
| 基础列（编号 88 + 类型 108 + 名称 min 240 + 等级 120 + 置信度 116 + 状态 104 + 时间 132 + 操作 150） | 1058 |
| + 处置单位 170 | 1228 |
| + 来源 124 | 1352 |

- 1366（内容宽≈1126）→ 隐藏两列：1058，可容纳。
- 1440（≈1200）→ 隐藏两列：1058，可容纳（原 1228 溢出 28px）。
- 1500（≈1260）→ 显示处置单位 1228，可容纳。
- 1760（≈1520）→ 显示来源 1352，可容纳。
- 1920（≈1680）→ 全列显示，与现有截图一致。

**文件 B：`frontend/src/views/DataManagement.vue`（第 21–22 行）**

```ts
const showFormat = computed(() => vw.value >= 1600) // 原 1500
const showMore = computed(() => vw.value >= 1400)   // 原 1360
```

依据：基础列 906（名称 min 260 + 类型 130 + 大小 110 + 时间 150 + 状态 106 + 操作 150）；+来源 140、记录数 96 → 1142；+格式 104 → 1246。

- 1366（≈1126）→ 隐藏 → 906，可容纳（原 1142 溢出 16px）。
- 1440（≈1200）→ 显示来源+记录数 1142，可容纳。
- 1600（≈1360）→ 再显示格式 1246，可容纳。
- 1920 → 全列显示，无变化。

不采用「压缩事件名称 min-width」方案：会牺牲名称可读性，且收益不一致。

### R2 事件表格空状态增加操作入口

**文件 A：`frontend/src/components/pages/EventTable.vue`**

- Props 增加 `hasFilter?: boolean`（默认为 `false`）。
- Emits 增加 `(e: 'reset'): void`、`(e: 'create'): void`。
- `#empty` 插槽改为在 `description` 之外通过默认插槽提供按钮：

```vue
<template #empty>
  <el-empty :image-size="84" description="没有符合条件的事件">
    <div class="etable__empty">
      <el-button v-if="hasFilter" size="small" :icon="RefreshLeft" @click="emit('reset')">清除筛选</el-button>
      <el-button size="small" type="primary" @click="emit('create')">上报事件</el-button>
    </div>
  </el-empty>
</template>
```

- 新增图标导入 `RefreshLeft`（`@element-plus/icons-vue`，项目已有依赖）。
- 样式追加 `.etable__empty { display:flex; gap:8px; justify-content:center; }`。

**文件 B：`frontend/src/views/EventCenter.vue`（第 389–399 行 `EventTable` 处）**

```vue
<EventTable
  ...
  :has-filter="hasFilter"
  @reset="resetFilters"
  @create="createVisible = true"
/>
```

复用现有 `resetFilters()`（第 198 行）与 `createVisible` / `EventCreateDialog`（第 403 行），不新增业务逻辑。

### R3 AI 分析页去除重复副标题

**文件：`frontend/src/views/AIAnalysis.vue`（第 185 行）**

```vue
<PageShell :title="curMeta.label" hint="选择分析场景与数据 → 配置参数并运行 → 查看结果与历史记录"
```

保留 hero 内的 `curMeta.label` / `curMeta.blurb`（承担场景说明），仅让管理页副标题承担流程指引，消除同屏重复。

### R4 Dashboard 事件流键盘可达 + 统一焦点环

**文件 A：`frontend/src/components/dashboard/LiveFeed.vue`（第 57–64 行 `<li>`）**

```vue
<li
  ...
  role="button"
  tabindex="0"
  :aria-label="`定位事件：${e.name}`"
  @click="emit('locate', e.id)"
  @keydown.enter.prevent="emit('locate', e.id)"
  @keydown.space.prevent="emit('locate', e.id)"
>
```

不改动现有 `TransitionGroup`、`is-new/is-sel/is-done` 状态与样式。

**文件 B：`frontend/src/assets/styles/main.css`（文件末尾追加）**

```css
/* 键盘焦点环：仅在键盘导航时显示，避免鼠标点击出现描边 */
button:focus-visible,
a:focus-visible,
[role='button']:focus-visible,
[tabindex]:focus-visible {
  outline: 2px solid var(--ce-accent, #4fc3f7);
  outline-offset: 2px;
}
```

## 3. 明确不做（本轮）

- **离线快照“今日”语义**：Dashboard 用快照 `today=9`，事件中心按真实当天推导为 0，两者矛盾。修复方式涉及产品定义（是否以 `snapshot.updated_at` 日期作为“当日”），属语义变更，不在本批自主实施。
- **合并 `src/utils/format.ts` 与 `src/composables/pages/format.ts`**：收益低、调用面广，不做。
- **任何 Cesium 场景、图层、数据源、接口、路由、依赖变更**：不做。
- 未新增页面/组件/依赖，未删除任何现有功能。

## 4. 验证计划

1. `npm run typecheck` 通过。
2. `npm run lint` 通过。
3. `npm run build` 成功。
4. 浏览器验证（dev server 5173，offline 快照模式）：
   - `/event-center` @1440×900：无横向滚动，无「处置单位 / 来源」列；@1920×1080：两列均显示。
   - `/event-center` 空状态：出现「清除筛选 / 上报事件」，点击分别恢复列表、打开上报对话框。
   - `/dashboard` @1920/1440：事件流可用 Tab 聚焦，Enter 触发定位；焦点环可见；HUD 面板无遮挡。
   - `/data-management` @1366/1440：无横向滚动；@1920 列数量不减少。
   - `/ai-analysis/fire`：副标题为流程说明，hero 文案保留。
5. 回归观察：`/monitoring`、其余 AI 子页无异常。

## 5. 风险与回退

- 断点上调后，1366–1760 视口会少显示 1–2 个次要列；信息仍可在详情抽屉查看。回退只需还原 4 个阈值。
- `el-empty` 默认插槽在 Element Plus 2.9 支持，用于追加按钮，不替换描述文案。
- 所有改动均为局部样式/断点/插槽与 ARIA 属性，无数据流变更，可独立回退。
