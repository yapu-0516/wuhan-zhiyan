<script setup lang="ts">
// 离线 / 静态演示模式提示条：apiState.mode !== 'live' 时显示，可手动探测后端是否恢复
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { apiState, retryConnection } from '@/api/http'

const props = defineProps<{
  /** 补充说明，例如"处置操作仅在本地生效" */
  detail?: string
}>()

const checking = ref(false)

const text = computed(() =>
  apiState.mode === 'mock'
    ? '静态演示模式：当前展示导出的数据快照，不连接后端。'
    : '离线演示模式：后端服务未连接，当前展示数据快照；上报、上传、AI 分析等写入类功能不可用。'
)

async function retry() {
  checking.value = true
  try {
    const r = await retryConnection()
    if (r.ok) {
      ElMessage.success('后端已恢复连接，正在刷新数据…')
      window.location.reload()
    } else {
      ElMessage.warning(`仍无法连接后端：${r.error ?? '未知错误'}`)
    }
  } finally {
    checking.value = false
  }
}
</script>

<template>
  <div v-if="apiState.mode !== 'live'" class="mode-banner" role="status">
    <span class="mode-banner__dot"></span>
    <span class="mode-banner__text">{{ text }}{{ props.detail ? ` ${props.detail}` : '' }}</span>
    <button v-if="apiState.mode === 'offline'" type="button" class="mode-banner__retry" :disabled="checking" @click="retry">
      {{ checking ? '连接中…' : '重试连接' }}
    </button>
    <span class="mode-banner__tag">{{ apiState.mode === 'mock' ? 'MOCK' : 'OFFLINE' }}</span>
  </div>
</template>

<style scoped>
.mode-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
  padding: 7px 14px;
  border-radius: 8px;
  font-size: 12.5px;
  color: #f6d78a;
  background: linear-gradient(90deg, rgba(240, 192, 80, 0.14), rgba(240, 192, 80, 0.04));
  border: 1px solid rgba(240, 192, 80, 0.32);
}
.mode-banner__dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #f0c050;
  box-shadow: 0 0 8px #f0c050;
  flex: none;
}
.mode-banner__text {
  flex: 1;
  min-width: 0;
}
.mode-banner__retry {
  flex: none;
  height: 24px;
  padding: 0 10px;
  border-radius: 4px;
  border: 1px solid rgba(240, 192, 80, 0.5);
  background: rgba(240, 192, 80, 0.12);
  color: #f6d78a;
  font-size: 12px;
  cursor: pointer;
  transition:
    background 0.15s ease,
    border-color 0.15s ease;
}
.mode-banner__retry:hover:not(:disabled) {
  background: rgba(240, 192, 80, 0.22);
  border-color: rgba(240, 192, 80, 0.8);
}
.mode-banner__retry:disabled {
  opacity: 0.6;
  cursor: default;
}
.mode-banner__tag {
  flex: none;
  font-size: 10px;
  letter-spacing: 1.5px;
  padding: 1px 7px;
  border-radius: 4px;
  border: 1px solid rgba(240, 192, 80, 0.45);
  color: #f0c050;
}
</style>
