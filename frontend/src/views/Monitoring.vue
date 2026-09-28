<script setup lang="ts">
// 城市监测 —— 阶段10
// 展示当前监测区域与数据来源。第3周为模拟展示，后续接入真实数据源。
const dataSources = [
  { name: '无人机影像', desc: '低空无人机采集的高分辨率影像', icon: '🚁', status: '采集中' },
  { name: '遥感影像', desc: '卫星遥感数据，覆盖武汉示范区', icon: '🛰️', status: '在线' },
  { name: '城市视频', desc: '城市道路监控视频流', icon: '📹', status: '在线' },
  { name: '其他空间数据', desc: '倾斜摄影、激光点云等', icon: '🗺️', status: '待接入' }
]
</script>

<template>
  <div class="page">
    <h2 class="page-title">城市监测</h2>

    <div class="region-card">
      <span class="region-label">当前监测区域</span>
      <span class="region-value">武汉市</span>
    </div>

    <h3 class="section-title">数据来源</h3>
    <div class="source-grid">
      <div v-for="s in dataSources" :key="s.name" class="source-card">
        <div class="source-icon">{{ s.icon }}</div>
        <div class="source-name">{{ s.name }}</div>
        <div class="source-desc">{{ s.desc }}</div>
        <div class="source-status" :class="{ 'is-online': s.status === '在线' }">{{ s.status }}</div>
      </div>
    </div>

    <p class="mock-tip">⚠️ 当前为前端原型阶段，数据来源为模拟展示，后续接入真实数据源。</p>
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
  margin: 0 0 18px;
  font-size: 22px;
  letter-spacing: 2px;
}
.region-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 20px;
  background: rgba(16, 22, 44, 0.6);
  border: 1px solid var(--ce-panel-border);
  border-radius: 8px;
  margin-bottom: 24px;
}
.region-label {
  color: var(--ce-text-dim);
  font-size: 13px;
}
.region-value {
  font-size: 18px;
  font-weight: 600;
  color: var(--ce-accent);
}
.section-title {
  margin: 0 0 14px;
  font-size: 16px;
  font-weight: 500;
  color: var(--ce-text);
}
.source-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 14px;
}
.source-card {
  padding: 18px;
  background: rgba(16, 22, 44, 0.6);
  border: 1px solid var(--ce-panel-border);
  border-radius: 8px;
}
.source-icon {
  font-size: 26px;
  margin-bottom: 8px;
}
.source-name {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 6px;
}
.source-desc {
  font-size: 12px;
  color: var(--ce-text-dim);
  line-height: 1.5;
  margin-bottom: 10px;
}
.source-status {
  display: inline-block;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  background: rgba(93, 116, 143, 0.25);
  color: #8b97b3;
}
.source-status.is-online {
  background: rgba(64, 196, 140, 0.18);
  color: #40c48c;
}
.mock-tip {
  margin-top: 24px;
  font-size: 12px;
  color: #5d748f;
}
</style>
