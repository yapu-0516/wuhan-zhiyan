<script setup lang="ts">
// 事件列表表格（纯展示）：排序 / 分页 / 新事件高亮由父级 EventCenter 控制
import { computed } from 'vue'
import { Location, Document } from '@element-plus/icons-vue'
import type { CityEvent } from '@/types/event'
import { EVENT_STATUS_COLOR, EVENT_STATUS_LABEL, EVENT_TYPE_META, SEVERITY_META, SOURCE_META } from '@/types/event'
import { pct100, shortTime } from '@/composables/pages/format'
import { useViewportWidth } from '@/composables/pages/viewport'

export interface SortState {
  prop: 'timestamp' | 'severity' | 'confidence'
  order: 'ascending' | 'descending'
}

const props = defineProps<{
  rows: CityEvent[]
  total: number
  page: number
  pageSize: number
  sort: SortState
  /** 实时到达 / 更新的事件高亮：id → 'new' | 'updated' */
  flash: Record<string, 'new' | 'updated'>
  loading?: boolean
}>()

const emit = defineEmits<{
  (e: 'update:page', v: number): void
  (e: 'update:pageSize', v: number): void
  (e: 'sort', v: SortState): void
  (e: 'open', row: CityEvent): void
  (e: 'locate', row: CityEvent): void
}>()

function rowClass(p: { row: CityEvent }): string {
  const k = props.flash[p.row.id]
  return k ? `is-${k}` : ''
}

function onRowClick(row: CityEvent) {
  emit('open', row)
}

function onSortChange(p: { prop?: string; order?: 'ascending' | 'descending' | null }) {
  // 取消排序时回退为"时间倒序"
  if (!p.order || !p.prop) {
    emit('sort', { prop: 'timestamp', order: 'descending' })
    return
  }
  if (p.prop === 'timestamp' || p.prop === 'severity' || p.prop === 'confidence') {
    emit('sort', { prop: p.prop, order: p.order })
  }
}

const vw = useViewportWidth()
const showSource = computed(() => vw.value >= 1500)
const showAssignee = computed(() => vw.value >= 1360)

const sevText = (e: CityEvent) => SEVERITY_META[e.severity].label.replace(/^\S+\s/, '')
const confColor = (c: number) => (c >= 0.85 ? '#4dd984' : c >= 0.6 ? '#4fc3f7' : '#f0c050')
</script>

<template>
  <div class="etable">
    <div class="etable__body">
      <el-table
        v-loading="loading"
        :data="rows"
        height="100%"
        :default-sort="{ prop: sort.prop, order: sort.order }"
        :row-class-name="rowClass"
        row-key="id"
        @row-click="onRowClick"
        @sort-change="onSortChange"
      >
        <template #empty>
          <el-empty :image-size="84" description="没有符合条件的事件，试试调整筛选条件" />
        </template>

        <el-table-column label="编号" width="88" fixed>
          <template #default="{ row }">
            <span class="cp-mono eid">{{ row.id }}</span>
          </template>
        </el-table-column>

        <el-table-column label="类型" width="108">
          <template #default="{ row }">
            <span class="etype" :style="{ '--c': EVENT_TYPE_META[(row as CityEvent).event_type].color }">
              <span class="etype__icon">{{ EVENT_TYPE_META[(row as CityEvent).event_type].icon }}</span>
              {{ EVENT_TYPE_META[(row as CityEvent).event_type].label }}
            </span>
          </template>
        </el-table-column>

        <el-table-column label="事件名称" min-width="240" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="ename">
              <span class="ename__t">{{ (row as CityEvent).name }}</span>
              <span class="ename__a">{{ (row as CityEvent).district }} · {{ (row as CityEvent).address }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="等级" prop="severity" width="120" sortable="custom">
          <template #default="{ row }">
            <span class="sev" :style="{ '--c': SEVERITY_META[(row as CityEvent).severity].color }">
              <b>{{ SEVERITY_META[(row as CityEvent).severity].short }}</b>{{ sevText(row) }}
            </span>
          </template>
        </el-table-column>

        <el-table-column v-if="showSource" label="来源" width="124">
          <template #default="{ row }">
            <span class="esrc">
              <span>{{ SOURCE_META[(row as CityEvent).source]?.icon ?? '📌' }}</span>
              {{ SOURCE_META[(row as CityEvent).source]?.label ?? (row as CityEvent).source }}
            </span>
          </template>
        </el-table-column>

        <el-table-column label="置信度" prop="confidence" width="116" sortable="custom">
          <template #default="{ row }">
            <div class="conf" :style="{ '--c': confColor((row as CityEvent).confidence) }">
              <span class="conf__n">{{ pct100((row as CityEvent).confidence) }}%</span>
              <span class="cp-bar"><i :style="{ width: `${pct100((row as CityEvent).confidence)}%` }"></i></span>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="状态" width="104">
          <template #default="{ row }">
            <span class="cp-pill cp-pill--sm" :style="{ '--c': EVENT_STATUS_COLOR[(row as CityEvent).status] }">
              <i class="cp-dot" :class="{ 'cp-dot--pulse': (row as CityEvent).status === 'pending' }"></i>
              {{ EVENT_STATUS_LABEL[(row as CityEvent).status] }}
            </span>
          </template>
        </el-table-column>

        <el-table-column label="发现时间" prop="timestamp" width="132" sortable="custom">
          <template #default="{ row }">
            <span class="etime">{{ shortTime((row as CityEvent).timestamp) }}</span>
          </template>
        </el-table-column>

        <el-table-column v-if="showAssignee" label="处置单位" min-width="170" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="(row as CityEvent).assignee" class="eassign">{{ (row as CityEvent).assignee }}</span>
            <span v-else class="eassign eassign--none">尚未指派</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="150" fixed="right" align="center">
          <template #default="{ row }">
            <div class="eops">
              <button class="eops__btn" type="button" title="在三维场景中定位" @click.stop="emit('locate', row)">
                <el-icon><Location /></el-icon>定位
              </button>
              <button class="eops__btn" type="button" title="查看详情与处置" @click.stop="emit('open', row)">
                <el-icon><Document /></el-icon>详情
              </button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="etable__foot">
      <span class="etable__total">共 <b>{{ total }}</b> 条事件</span>
      <el-pagination
        background
        layout="sizes, prev, pager, next"
        :total="total"
        :current-page="page"
        :page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        popper-class="cp-popper"
        @update:current-page="(v: number) => emit('update:page', v)"
        @update:page-size="(v: number) => emit('update:pageSize', v)"
      />
    </div>
  </div>
</template>

<style scoped>
.etable {
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  height: 100%;
  min-height: 0;
}
.etable__body {
  position: relative;
  flex: 1 1 auto;
  min-height: 0;
}
.etable__body :deep(.el-table) {
  position: absolute;
  inset: 0;
}
.etable__body :deep(.el-table__row) {
  cursor: pointer;
}
.etable__foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 16px;
  border-top: 1px solid rgba(64, 120, 180, 0.16);
  flex-wrap: wrap;
}
.etable__total {
  font-size: 12.5px;
  color: var(--ce-text-dim, #8aa3c4);
}
.etable__total b {
  color: var(--ce-accent, #4fc3f7);
  font-weight: 600;
  padding: 0 2px;
}
.eid {
  font-size: 12.5px;
  color: #a9cdf0;
}
.etype {
  --c: #4fc3f7;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  color: var(--c);
}
.etype__icon {
  font-size: 16px;
  filter: drop-shadow(0 0 6px color-mix(in srgb, var(--c) 55%, transparent));
}
.ename {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  line-height: 1.35;
}
.ename__t {
  color: #e6f0ff;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ename__a {
  font-size: 12px;
  color: var(--ce-text-dim, #8aa3c4);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.sev {
  --c: #4fc3f7;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 22px;
  padding: 0 9px 0 4px;
  border-radius: 6px;
  font-size: 12px;
  color: var(--c);
  background: color-mix(in srgb, var(--c) 13%, transparent);
  border: 1px solid color-mix(in srgb, var(--c) 40%, transparent);
}
.sev b {
  display: inline-grid;
  place-items: center;
  min-width: 18px;
  height: 16px;
  padding: 0 3px;
  border-radius: 4px;
  font-size: 11px;
  color: #06101f;
  background: var(--c);
}
.esrc {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #b9cdec;
  font-size: 12.5px;
}
.conf {
  --c: #4fc3f7;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding-right: 6px;
}
.conf__n {
  font-size: 12px;
  line-height: 1;
  color: var(--c);
  font-variant-numeric: tabular-nums;
}
.etime {
  font-size: 12.5px;
  color: #b9cdec;
  font-variant-numeric: tabular-nums;
}
.eassign {
  font-size: 12.5px;
  color: #b9cdec;
}
.eassign--none {
  color: #5d748f;
}
.eops {
  display: inline-flex;
  gap: 4px;
}
.eops__btn {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 3px 7px;
  white-space: nowrap;
  border: 1px solid transparent;
  border-radius: 5px;
  background: transparent;
  color: var(--ce-accent, #4fc3f7);
  font-size: 12.5px;
  cursor: pointer;
  transition: all 0.15s;
}
.eops__btn:hover {
  border-color: rgba(79, 195, 247, 0.45);
  background: rgba(79, 195, 247, 0.12);
  box-shadow: 0 0 10px rgba(79, 195, 247, 0.25);
}

/* 实时到达 / 更新高亮 */
.etable__body :deep(tr.is-new > td.el-table__cell) {
  animation: row-flash-new 4s ease-out;
}
.etable__body :deep(tr.is-updated > td.el-table__cell) {
  animation: row-flash-upd 3s ease-out;
}
@keyframes row-flash-new {
  0%,
  35% {
    background-color: #1b4568;
    box-shadow: inset 0 1px 0 rgba(79, 195, 247, 0.9), inset 0 -1px 0 rgba(79, 195, 247, 0.9);
  }
  100% {
    background-color: #0e172c;
    box-shadow: none;
  }
}
@keyframes row-flash-upd {
  0%,
  30% {
    background-color: #3a3520;
  }
  100% {
    background-color: #0e172c;
  }
}
@media (prefers-reduced-motion: reduce) {
  .etable__body :deep(tr.is-new > td.el-table__cell),
  .etable__body :deep(tr.is-updated > td.el-table__cell) {
    animation: none;
    background-color: #123456;
  }
}
</style>
