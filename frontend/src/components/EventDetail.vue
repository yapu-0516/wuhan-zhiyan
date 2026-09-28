<script setup lang="ts">
// 阶段8：事件详情浮层
// 点击三维场景中的事件后弹出，展示事件编号/类型/置信度/状态/时间。
// 数据来自 useCityEvents 的 CityEvent，元信息用 EVENT_TYPE_META / EVENT_STATUS_LABEL。
// "查看详情" 按钮在第3周前端原型阶段仅做提示，不伪造后续流程。
import type { CityEvent } from '@/types/event'
import { EVENT_TYPE_META, EVENT_STATUS_LABEL } from '@/types/event'
import { ElMessage } from 'element-plus'

defineProps<{ event: CityEvent }>()
const emit = defineEmits<{ (e: 'close'): void }>()

const meta = (e: CityEvent) => EVENT_TYPE_META[e.event_type]

function viewDetail() {
  // 第3周前端原型阶段：事件详情深度处理流程待后续阶段接入
  ElMessage.info('当前为第3周前端原型，事件详情深度处理将在后续阶段接入')
}
</script>

<template>
  <div class="event-detail">
    <div class="event-detail__title">
      <span class="event-detail__icon">{{ meta(event).icon }}</span>
      <span>{{ event.name }}</span>
      <span class="event-detail__type-tag" :style="{ color: meta(event).color, borderColor: meta(event).color }">
        {{ meta(event).label }}
      </span>
    </div>
    <dl class="event-detail__body">
      <div><dt>事件编号</dt><dd>{{ event.id }}</dd></div>
      <div><dt>类型</dt><dd>{{ meta(event).label }}</dd></div>
      <div><dt>置信度</dt><dd>{{ Math.round(event.confidence * 100) }}%</dd></div>
      <div><dt>状态</dt><dd>{{ EVENT_STATUS_LABEL[event.status] }}</dd></div>
      <div><dt>时间</dt><dd>{{ event.timestamp }}</dd></div>
      <div><dt>位置</dt><dd>{{ event.longitude.toFixed(4) }}, {{ event.latitude.toFixed(4) }}</dd></div>
    </dl>
    <div class="event-detail__actions">
      <button class="event-detail__btn event-detail__btn--primary" @click="viewDetail">查看详情</button>
      <button class="event-detail__btn" @click="emit('close')">关闭</button>
    </div>
  </div>
</template>

<style scoped>
.event-detail {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 260px;
  padding: 16px;
  background: rgba(16, 22, 44, 0.9);
  border: 1px solid rgba(123, 179, 255, 0.35);
  border-radius: 8px;
  color: #e6edf7;
  font-size: 13px;
  backdrop-filter: blur(6px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.45);
  z-index: 10;
}
.event-detail__title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 12px;
  color: #e6edf7;
}
.event-detail__icon {
  font-size: 18px;
}
.event-detail__type-tag {
  margin-left: auto;
  font-size: 11px;
  padding: 2px 8px;
  border: 1px solid;
  border-radius: 10px;
  font-weight: 400;
}
.event-detail__body {
  margin: 0 0 14px;
  display: grid;
  gap: 8px;
}
.event-detail__body > div {
  display: grid;
  grid-template-columns: 64px 1fr;
  gap: 8px;
  align-items: baseline;
}
.event-detail__body dt {
  color: #8b97b3;
  margin: 0;
}
.event-detail__body dd {
  margin: 0;
  color: #e6edf7;
}
.event-detail__actions {
  display: flex;
  gap: 8px;
}
.event-detail__btn {
  flex: 1;
  padding: 7px 0;
  background: transparent;
  border: 1px solid rgba(123, 179, 255, 0.4);
  border-radius: 4px;
  color: #7fb3ff;
  cursor: pointer;
  font-size: 12px;
}
.event-detail__btn:hover {
  background: rgba(123, 179, 255, 0.12);
}
.event-detail__btn--primary {
  background: rgba(123, 179, 255, 0.18);
  border-color: rgba(123, 179, 255, 0.6);
}
</style>
