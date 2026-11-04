<script setup lang="ts">
// 任务进度：提交 → 预处理 → 模型推理 → 后处理 → 完成，附进度条与耗时
import { computed } from 'vue'
import { fmtDuration } from '@/composables/pages/format'
import { STEP_TITLES, stepActive, taskStatusMeta, typeMeta } from '@/composables/pages/aiMeta'
import type { AnalysisTask } from '@/types/api'

const props = defineProps<{
  task: AnalysisTask
  elapsedMs: number
  /** 轮询超时仍未结束 */
  stalled?: boolean
}>()

const meta = computed(() => typeMeta(props.task.type))
const color = computed(() => meta.value?.color ?? '#4fc3f7')
const status = computed(() => taskStatusMeta(props.task.status))
const active = computed(() => stepActive(props.task))
const failed = computed(() => props.task.status === 'failed')
const running = computed(() => props.task.status === 'running' || props.task.status === 'pending')
const percent = computed(() => (props.task.status === 'done' ? 100 : Math.max(0, Math.min(100, Math.round(props.task.progress ?? 0)))))

const STEP_DESC = ['任务已提交，等待调度', '读取并规范化输入数据', '算法推理中', '生成标注与指标', '分析完成']
const tip = computed(() => {
  if (failed.value) return '分析失败'
  if (props.task.status === 'pending') return '任务排队中，等待算法服务调度…'
  return `${STEP_TITLES[Math.min(active.value, STEP_TITLES.length - 1)]}：${STEP_DESC[Math.min(active.value, STEP_DESC.length - 1)]}`
})
</script>

<template>
  <section class="prog cp-panel" :style="{ '--c': color }">
    <header class="prog__head">
      <span class="prog__icon"><i /></span>
      <div class="prog__who">
        <b>{{ meta?.label ?? task.type }}</b>
        <span class="cp-mono">{{ task.id }}</span>
        <template v-if="task.algorithm">
          <i>·</i>
          <span class="prog__algo">{{ task.algorithm.name }} v{{ task.algorithm.version }}</span>
        </template>
      </div>
      <span class="cp-pill" :style="{ '--c': status.color }">
        <i class="cp-dot" :class="{ 'cp-dot--pulse': status.pulse }"></i>{{ status.label }}
      </span>
      <span class="prog__time cp-mono">⏱ {{ fmtDuration(elapsedMs) }}</span>
    </header>

    <el-steps :active="active" align-center :process-status="failed ? 'error' : 'process'" finish-status="success" class="prog__steps">
      <el-step v-for="s in STEP_TITLES" :key="s" :title="s" />
    </el-steps>

    <el-progress
      :percentage="percent"
      :stroke-width="10"
      :striped="running"
      :striped-flow="running"
      :duration="2"
      :color="failed ? '#ff6b6b' : color"
      :status="failed ? 'exception' : task.status === 'done' ? 'success' : undefined"
    />
    <p class="prog__tip" :class="{ 'is-bad': failed }">{{ tip }}</p>

    <el-alert v-if="failed" type="error" :closable="false" show-icon :title="task.error || '算法执行失败，请检查输入数据格式后重试'" />
    <el-alert
      v-else-if="stalled"
      type="warning"
      :closable="false"
      show-icon
      title="任务耗时较长，已停止自动刷新；可在下方「任务历史」中查看最新状态。"
    />
  </section>
</template>

<style scoped>
.prog {
  --c: #4fc3f7;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px 20px 18px;
  border-color: color-mix(in srgb, var(--c) 40%, transparent);
}
.prog__head {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px 12px;
}
.prog__icon {
  display: grid;
  place-items: center;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: var(--c);
}
.prog__who {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 4px 8px;
  font-size: 12.5px;
  color: #8aa3c4;
}
.prog__who b {
  font-size: 15px;
  color: #f0f6ff;
}
.prog__who i {
  font-style: normal;
  color: #3e546f;
}
.prog__algo {
  color: var(--c);
}
.prog__time {
  font-size: 13px;
  color: #c9dbf5;
}
.prog__steps :deep(.el-step__head.is-process),
.prog__steps :deep(.el-step__title.is-process) {
  color: var(--c);
  border-color: var(--c);
}
.prog__steps :deep(.el-step__head.is-finish),
.prog__steps :deep(.el-step__title.is-finish) {
  color: #4dd984;
  border-color: #4dd984;
}
.prog__steps :deep(.el-step__head.is-wait),
.prog__steps :deep(.el-step__title.is-wait) {
  color: #4d6384;
  border-color: #33465f;
}
.prog__steps :deep(.el-step__line) {
  background-color: rgba(64, 120, 180, 0.25);
}
.prog__tip {
  margin: -6px 0 0;
  font-size: 13px;
  color: #9db4d2;
}
.prog__tip.is-bad {
  color: #ff8f8f;
}
</style>
