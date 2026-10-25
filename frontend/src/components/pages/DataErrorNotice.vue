<script setup lang="ts">
// 数据加载失败提示：区分“空数据”与“加载失败”，并提供重试入口
defineProps<{ message: string; busy?: boolean }>()
defineEmits<{ (e: 'retry'): void }>()
</script>

<template>
  <div class="den" role="alert">
    <span class="den__dot" />
    <span class="den__text">事件数据加载失败：{{ message }}</span>
    <button type="button" class="den__btn" :disabled="busy" @click="$emit('retry')">
      {{ busy ? '重试中…' : '重试' }}
    </button>
  </div>
</template>

<style scoped>
.den {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 7px 12px;
  border-radius: 8px;
  font-size: 12.5px;
  color: #ffb4a2;
  background: linear-gradient(90deg, rgba(255, 107, 107, 0.14), rgba(255, 107, 107, 0.04));
  border: 1px solid rgba(255, 107, 107, 0.38);
}
.den__dot {
  flex: none;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #ff6b6b;
  box-shadow: 0 0 8px #ff6b6b;
}
.den__text {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.den__btn {
  flex: none;
  height: 24px;
  padding: 0 10px;
  border-radius: 4px;
  border: 1px solid rgba(255, 107, 107, 0.5);
  background: rgba(255, 107, 107, 0.12);
  color: #ffb4a2;
  font-size: 12px;
  cursor: pointer;
  transition:
    background 0.15s ease,
    border-color 0.15s ease;
}
.den__btn:hover:not(:disabled) {
  background: rgba(255, 107, 107, 0.22);
  border-color: rgba(255, 107, 107, 0.8);
}
.den__btn:disabled {
  opacity: 0.6;
  cursor: default;
}
</style>
