<script setup lang="ts">
// 数据管理 —— 阶段10/11
// 基础数据表格：数据名称 / 数据类型 / 获取时间 / 数据状态。
// 通过 API 接口层 getDataList 获取（USE_MOCK 时走 mock，接后端后走 fetch）。
import { ref, onMounted } from 'vue'
import { getDataList, type DataItem } from '@/api/data'

const dataList = ref<DataItem[]>([])

onMounted(async () => {
  dataList.value = await getDataList()
})

function statusColor(s: string) {
  return s === '已入库' ? '#40c48c' : s === '处理中' ? '#f0c050' : '#7fb3ff'
}
</script>

<template>
  <div class="page">
    <h2 class="page-title">数据管理</h2>
    <p class="page-hint">城市管理所用空间数据资产清单。</p>
    <el-table :data="dataList" stripe class="data-table">
      <el-table-column prop="name" label="数据名称" min-width="200" />
      <el-table-column prop="type" label="数据类型" width="140" />
      <el-table-column prop="time" label="获取时间" width="180" />
      <el-table-column label="数据状态" width="120">
        <template #default="{ row }">
          <span :style="{ color: statusColor(row.status) }">{{ row.status }}</span>
        </template>
      </el-table-column>
    </el-table>
    <p class="mock-tip">⚠️ 当前为 mock 数据，阶段11 后由 API 层获取真实数据清单。</p>
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
  margin: 0 0 18px;
  color: var(--ce-text-dim);
  font-size: 13px;
}
.data-table {
  width: 100%;
  background: transparent;
}
.mock-tip {
  margin-top: 18px;
  font-size: 12px;
  color: #5d748f;
}
</style>
