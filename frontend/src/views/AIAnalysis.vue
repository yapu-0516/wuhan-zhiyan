<script setup lang="ts">
// AI 智能分析 —— 阶段10/11
// 第3周仅做 UI：分析类型选择 / 数据上传 / 开始分析按钮。
// 点击"开始分析"经 API 接口层 createTask 提交，第3周返回 prototype 状态，
// 据此提示原型阶段，不伪造 AI 分析结果。
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { UploadUserFile } from 'element-plus'
import { createTask } from '@/api/task'

const analysisTypes = [
  { key: 'fire', label: '火灾识别', icon: '🔥' },
  { key: 'traffic', label: '交通拥堵分析', icon: '🚗' },
  { key: 'building', label: '建筑异常检测', icon: '🏢' }
]

const selectedType = ref('')
const fileList = ref<UploadUserFile[]>([])
const submitting = ref(false)

async function startAnalysis() {
  if (!selectedType.value) {
    ElMessage.warning('请先选择分析类型')
    return
  }
  if (fileList.value.length === 0) {
    ElMessage.warning('请先选择待分析数据')
    return
  }
  submitting.value = true
  try {
    const task = await createTask(selectedType.value, fileList.value.length)
    // 第3周原型：createTask 返回 prototype 状态，提示接口后续接入，不伪造结果
    if (task.status === 'prototype') {
      ElMessage.info('当前为第3周前端原型，AI分析接口将在后续阶段接入')
    }
  } catch (e: any) {
    ElMessage.error(e?.message || '提交分析任务失败')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="page">
    <h2 class="page-title">AI 智能分析</h2>
    <p class="page-hint">选择分析类型与待分析数据，启动 AI 智能识别。</p>

    <h3 class="section-title">分析类型</h3>
    <div class="type-buttons">
      <button
        v-for="t in analysisTypes"
        :key="t.key"
        class="type-btn"
        :class="{ 'is-active': selectedType === t.key }"
        @click="selectedType = t.key"
      >
        <span class="type-icon">{{ t.icon }}</span>
        <span>{{ t.label }}</span>
      </button>
    </div>

    <h3 class="section-title">数据上传</h3>
    <el-upload
      v-model:file-list="fileList"
      :auto-upload="false"
      drag
      multiple
      class="upload-area"
    >
      <el-icon class="upload-icon"><UploadFilled /></el-icon>
      <div class="upload-text">点击或拖拽文件到此</div>
      <template #tip>
        <div class="upload-tip">支持影像 / 视频 / 三维模型等空间数据</div>
      </template>
    </el-upload>

    <div class="action-bar">
      <button class="start-btn" :disabled="submitting" @click="startAnalysis">
        {{ submitting ? '提交中…' : '开始分析' }}
      </button>
    </div>

    <p class="mock-tip">⚠️ 当前为第3周前端原型，AI 分析接口将在后续阶段接入，不伪造分析结果。</p>
  </div>
</template>

<style scoped>
.page {
  padding: 24px 32px;
  color: var(--ce-text);
  height: 100%;
  overflow: auto;
}
.page-title {
  margin: 0 0 10px;
  font-size: 22px;
  letter-spacing: 2px;
}
.page-hint {
  margin: 0 0 22px;
  color: var(--ce-text-dim);
  font-size: 13px;
}
.section-title {
  margin: 0 0 14px;
  font-size: 16px;
  font-weight: 500;
}
.type-buttons {
  display: flex;
  gap: 12px;
  margin-bottom: 26px;
  flex-wrap: wrap;
}
.type-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  background: rgba(16, 22, 44, 0.6);
  border: 1px solid var(--ce-panel-border);
  border-radius: 6px;
  color: var(--ce-text);
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}
.type-btn:hover {
  border-color: var(--ce-accent);
}
.type-btn.is-active {
  background: rgba(123, 179, 255, 0.18);
  border-color: var(--ce-accent);
  color: var(--ce-accent);
}
.type-icon {
  font-size: 18px;
}
.upload-area {
  width: 100%;
  max-width: 520px;
  margin-bottom: 22px;
}
.upload-icon {
  font-size: 40px;
  color: var(--ce-text-dim);
}
.upload-text {
  margin-top: 8px;
  font-size: 13px;
  color: var(--ce-text-dim);
}
.upload-tip {
  font-size: 12px;
  color: #5d748f;
  margin-top: 6px;
}
.action-bar {
  margin-bottom: 10px;
}
.start-btn {
  padding: 10px 32px;
  background: var(--ce-accent);
  border: none;
  border-radius: 6px;
  color: #0b1020;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}
.start-btn:hover {
  opacity: 0.9;
}
.start-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.mock-tip {
  margin-top: 24px;
  font-size: 12px;
  color: #5d748f;
}
</style>
