<script setup lang="ts">
// 顶部品牌栏：城市之眼 + 副标题
</script>

<template>
  <header class="app-header">
    <div class="brand">
      <span class="brand-mark"></span>
      <div class="brand-text">
        <h1>城市之眼</h1>
        <p>城市智能监测与辅助治理平台</p>
      </div>
    </div>
    <div class="header-right">
      <span class="city-tag">示范城市 · 武汉</span>
    </div>
  </header>
</template>

<style scoped>
.app-header {
  height: var(--header-h);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 22px;
  background: linear-gradient(90deg, #0a1430 0%, #0d1b3a 100%);
  border-bottom: 1px solid var(--ce-panel-border);
  z-index: 10;
}
.brand {
  display: flex;
  align-items: center;
  gap: 14px;
}
.brand-mark {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: radial-gradient(circle at 30% 30%, #7fe9ff, #1f6fb0 70%);
  box-shadow: 0 0 12px rgba(79, 195, 247, 0.8);
}
.brand-text h1 {
  margin: 0;
  font-size: 20px;
  letter-spacing: 4px;
  color: #eaf4ff;
}
.brand-text p {
  margin: 2px 0 0;
  font-size: 11px;
  letter-spacing: 2px;
  color: var(--ce-text-dim);
}
.header-right .city-tag {
  font-size: 12px;
  color: var(--ce-accent);
  padding: 4px 12px;
  border: 1px solid var(--ce-panel-border);
  border-radius: 2px;
  background: rgba(79, 195, 247, 0.06);
}
</style>
