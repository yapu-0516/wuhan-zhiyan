<script setup lang="ts">
// 任务历史：点击行载入结果面板
import { computed, ref, watch } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { taskStatusMeta, typeMeta } from '@/composables/pages/aiMeta'
import { shortTime } from '@/composables/pages/format'
import { useViewportWidth } from '@/composables/pages/viewport'
import type { AnalysisTask } from '@/types/api'

const props = defineProps<{ tasks: AnalysisTask[]; currentId: string; loading?: boolean }>()
const emit = defineEmits<{
  (e: 'select', t: AnalysisTask): void
  (e: 'refresh'): void
}>()

const vw = useViewportWidth()
const showAlgo = computed(() => vw.value >= 1500)
const showProg = computed(() => vw.value >= 1360)
const page = ref(1)
const pageSize = 6
const rows = computed(() => props.tasks.slice((page.value - 1) * pageSize, page.value * pageSize))
watch(
  () => props.tasks.length,
  (n) => {
    const max = Math.max(1, Math.ceil(n / pageSize))
    if (page.value > max) page.value = max
  }
)

function inputText(t: AnalysisTask): string {
  const first = t.inputs?.[0]?.name
  if (!first) return t.file_count ? `${t.file_count} 个文件` : '示例数据'
  const more = (t.inputs?.length ?? 1) - 1
  return more > 0 ? `${first} 等 ${more + 1} 个` : first
}

function rowClass(p: { row: AnalysisTask }): string {
  return p.row.id === props.currentId ? 'is-current' : ''
}
function onRowClick(row: AnalysisTask) {
  emit('select', row)
}
</script>

<template>
  <section class="cp-panel hist">
    <div class="cp-panel__header">
      <h3 class="cp-panel__title">任务历史</h3>
      <div class="hist__right">
        <span class="cp-panel__sub">共 {{ tasks.length }} 个任务 · 点击行查看结果</span>
        <el-button size="small" :icon="Refresh" :loading="loading" @click="emit('refresh')">刷新</el-button>
      </div>
    </div>

    <el-table
      v-loading="loading && !tasks.length"
      :data="rows"
      row-key="id"
      :row-class-name="rowClass"
      @row-click="onRowClick"
    >
      <template #empty>
        <el-empty :image-size="72" description="还没有分析任务，选择示例数据后点击「开始分析」试试" />
      </template>

      <el-table-column label="任务编号" width="110">
        <template #default="{ row }"
          ><span class="cp-mono hist__id">{{ (row as AnalysisTask).id }}</span></template
        >
      </el-table-column>
      <el-table-column label="类型" width="150">
        <template #default="{ row }">
          <span class="hist__type" :style="{ '--c': typeMeta((row as AnalysisTask).type)?.color ?? '#4fc3f7' }">
            <i class="hist__dot" />
            {{ typeMeta((row as AnalysisTask).type)?.label ?? (row as AnalysisTask).type }}
          </span>
        </template>
      </el-table-column>
      <el-table-column label="输入" min-width="180" show-overflow-tooltip>
        <template #default="{ row }">{{ inputText(row) }}</template>
      </el-table-column>
      <el-table-column v-if="showAlgo" label="算法" min-width="150" show-overflow-tooltip>
        <template #default="{ row }">
          <span v-if="(row as AnalysisTask).algorithm" class="cp-mono hist__algo">
            {{ (row as AnalysisTask).algorithm!.name }} <i>v{{ (row as AnalysisTask).algorithm!.version }}</i>
          </span>
          <span v-else class="hist__na">—</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="108">
        <template #default="{ row }">
          <span class="cp-pill cp-pill--sm" :style="{ '--c': taskStatusMeta((row as AnalysisTask).status).color }">
            <i class="cp-dot" :class="{ 'cp-dot--pulse': taskStatusMeta((row as AnalysisTask).status).pulse }"></i>
            {{ taskStatusMeta((row as AnalysisTask).status).label }}
          </span>
        </template>
      </el-table-column>
      <el-table-column v-if="showProg" label="进度" width="130">
        <template #default="{ row }">
          <div class="hist__prog">
            <span class="cp-bar" :style="{ '--c': (row as AnalysisTask).status === 'failed' ? '#ff6b6b' : '#4fc3f7' }">
              <i
                :style="{
                  width: `${(row as AnalysisTask).status === 'done' ? 100 : ((row as AnalysisTask).progress ?? 0)}%`
                }"
              ></i>
            </span>
            <em
              >{{
                (row as AnalysisTask).status === 'done' ? 100 : Math.round((row as AnalysisTask).progress ?? 0)
              }}%</em
            >
          </div>
        </template>
      </el-table-column>
      <el-table-column label="创建时间" width="140">
        <template #default="{ row }"
          ><span class="hist__time">{{ shortTime((row as AnalysisTask).createdAt) }}</span></template
        >
      </el-table-column>
      <el-table-column label="结论" min-width="260" show-overflow-tooltip>
        <template #default="{ row }">
          <template v-if="(row as AnalysisTask).status === 'done' && (row as AnalysisTask).result">
            <span
              class="cp-pill cp-pill--sm"
              :style="{ '--c': (row as AnalysisTask).result!.detected ? '#ff6b6b' : '#4dd984' }"
              >{{ (row as AnalysisTask).result!.detected ? '检测到异常' : '未发现异常' }}</span
            >
            <span class="hist__sum">{{ (row as AnalysisTask).result!.summary }}</span>
          </template>
          <span v-else-if="(row as AnalysisTask).status === 'failed'" class="hist__err">{{
            (row as AnalysisTask).error || '分析失败'
          }}</span>
          <span v-else class="hist__na">—</span>
        </template>
      </el-table-column>
    </el-table>

    <div v-if="tasks.length > pageSize" class="hist__foot">
      <el-pagination
        background
        small
        layout="prev, pager, next"
        :total="tasks.length"
        :page-size="pageSize"
        :current-page="page"
        @update:current-page="(v: number) => (page = v)"
      />
    </div>
  </section>
</template>

<style scoped>
.hist__right {
  display: flex;
  align-items: center;
  gap: 12px;
}
.hist :deep(.el-table__row) {
  cursor: pointer;
}
.hist :deep(tr.is-current > td.el-table__cell) {
  background: rgba(79, 195, 247, 0.1) !important;
  box-shadow: inset 0 0 0 0 transparent;
}
.hist :deep(tr.is-current > td.el-table__cell:first-child) {
  box-shadow: inset 3px 0 0 var(--ce-accent, #4fc3f7);
}
.hist__id {
  color: #a9cdf0;
  font-size: 12.5px;
}
.hist__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}
.hist__type {
  --c: #4fc3f7;
  color: var(--c);
  font-weight: 600;
}
.hist__algo {
  font-size: 12.5px;
  color: #b9cdec;
}
.hist__algo i {
  font-style: normal;
  color: #6f89aa;
}
.hist__prog {
  display: flex;
  align-items: center;
  gap: 8px;
}
.hist__prog .cp-bar {
  flex: 1;
}
.hist__prog em {
  width: 34px;
  font-style: normal;
  font-size: 11.5px;
  text-align: right;
  color: #8aa3c4;
  font-variant-numeric: tabular-nums;
}
.hist__time {
  font-size: 12.5px;
  color: #b9cdec;
  font-variant-numeric: tabular-nums;
}
.hist__sum {
  margin-left: 8px;
  font-size: 12.5px;
  color: #a9bdd9;
}
.hist__err {
  font-size: 12.5px;
  color: #ff8f8f;
}
.hist__na {
  color: #5d748f;
}
.hist__foot {
  display: flex;
  justify-content: flex-end;
  padding: 10px 16px;
  border-top: 1px solid rgba(64, 120, 180, 0.16);
}
</style>
