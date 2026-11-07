<script setup lang="ts">
// 左侧导航：主页面与 AI 分析入口；桌面保留文字，平板收为图标栏，手机转为底部导航。
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import {
  Location,
  Monitor,
  FirstAidKit,
  Warning,
  Files,
  Sunny,
  Van,
  OfficeBuilding,
  Umbrella,
  Fold,
  Expand,
  Menu,
  Close
} from '@element-plus/icons-vue'
import { useCityEvents } from '@/composables/useCityEvents'
import { useDemoBaseline } from '@/composables/useDemoBaseline'
import { useLayout } from '@/composables/useLayout'

const route = useRoute()
const { stats, events } = useCityEvents()
const { calm, demoEventIds } = useDemoBaseline()
const displayActive = computed(() => {
  if (calm.value) return 0
  if (!demoEventIds.value.length) return stats.value.active
  const ids = new Set(demoEventIds.value)
  return events.value.filter((event) => ids.has(event.id) && event.status !== 'resolved').length
})
const { sidebarCollapsed, toggleSidebar } = useLayout()
const mobileMoreOpen = ref(false)

const navItems = [
  { to: '/dashboard', label: '总览', icon: Location },
  { to: '/drill', label: '演练', icon: FirstAidKit },
  { to: '/monitoring', label: '监测', icon: Monitor },
  { to: '/event-center', label: '事件', icon: Warning, badge: true },
  { to: '/data-management', label: '数据', icon: Files }
]

// AI 分析按风险类型独立成页，互不混排
const aiItems = [
  { to: '/ai-analysis/fire', label: '火灾识别', icon: Sunny },
  { to: '/ai-analysis/traffic', label: '交通拥堵', icon: Van },
  { to: '/ai-analysis/building', label: '建筑异常', icon: OfficeBuilding },
  { to: '/ai-analysis/flood', label: '内涝积水', icon: Umbrella }
]

const isActive = (to: string) => route.path === to || route.path.startsWith(`${to}/`)

watch(
  () => route.fullPath,
  () => (mobileMoreOpen.value = false)
)
</script>

<template>
  <aside class="sidebar" :class="{ collapsed: sidebarCollapsed }">
    <nav class="nav-list">
      <RouterLink
        v-for="item in navItems"
        :key="item.to"
        :to="item.to"
        class="nav-item"
        :class="{ active: isActive(item.to) }"
        :title="sidebarCollapsed ? item.label : undefined"
      >
        <el-icon class="nav-icon"><component :is="item.icon" /></el-icon>
        <span class="nav-text">
          <span class="nav-label">{{ item.label }}</span>
        </span>
        <span v-if="item.badge && displayActive > 0" class="nav-badge ce-num">{{
          displayActive > 99 ? '99+' : displayActive
        }}</span>
      </RouterLink>

      <div class="nav-group-label" title="AI 分析">
        <span>AI 分析</span>
      </div>
      <RouterLink
        v-for="item in aiItems"
        :key="item.to"
        :to="item.to"
        class="nav-item nav-item--sub"
        :class="{ active: isActive(item.to) }"
        :title="sidebarCollapsed ? item.label : undefined"
      >
        <el-icon class="nav-icon"><component :is="item.icon" /></el-icon>
        <span class="nav-text">
          <span class="nav-label">{{ item.label }}</span>
        </span>
      </RouterLink>
      <button
        class="nav-item nav-item--more"
        type="button"
        aria-label="打开 AI 分析导航"
        :aria-expanded="mobileMoreOpen"
        @click="mobileMoreOpen = true"
      >
        <el-icon class="nav-icon"><Menu /></el-icon>
        <span class="nav-text"><span class="nav-label">更多</span></span>
      </button>
    </nav>
    <div class="sidebar-footer">
      <button class="collapse-btn" :title="sidebarCollapsed ? '展开导航' : '收起导航'" @click="toggleSidebar">
        <el-icon><component :is="sidebarCollapsed ? Expand : Fold" /></el-icon>
      </button>
      <span class="ver">CityEye v1.0</span>
    </div>
  </aside>

  <Teleport to="body">
    <Transition name="nav-sheet">
      <div v-if="mobileMoreOpen" class="nav-sheet" @click.self="mobileMoreOpen = false">
        <section role="dialog" aria-modal="true" aria-labelledby="mobile-nav-title">
          <header>
            <div>
              <h2 id="mobile-nav-title">AI 分析</h2>
              <p>按风险类型进入独立分析页</p>
            </div>
            <button type="button" aria-label="关闭 AI 分析导航" @click="mobileMoreOpen = false">
              <el-icon><Close /></el-icon>
            </button>
          </header>
          <nav>
            <RouterLink v-for="item in aiItems" :key="item.to" :to="item.to">
              <el-icon><component :is="item.icon" /></el-icon>
              <span>{{ item.label }}</span>
            </RouterLink>
          </nav>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.sidebar {
  position: relative;
  z-index: 10;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  min-width: 0;
  overflow: hidden;
  background: var(--ce-bg);
  border-right: 1px solid var(--ce-divider);
}
.nav-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 12px 8px;
  overflow-y: auto;
}
.nav-group-label {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin: 10px 4px 2px;
  padding: 6px 8px 0;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0;
  color: var(--ce-text-faint);
  border-top: 1px solid var(--ce-divider);
}
.nav-item--sub {
  height: 38px;
  padding-left: 14px;
}
.nav-item--sub .nav-icon {
  font-size: 15px;
}
.nav-item--sub .nav-label {
  font-size: 13px;
  letter-spacing: 0;
}
.nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  height: 42px;
  padding: 0 10px;
  border: 1px solid transparent;
  border-radius: 5px;
  color: var(--ce-text-dim);
  text-decoration: none;
  white-space: nowrap;
  transition:
    color 0.15s ease,
    background-color 0.15s ease,
    border-color 0.15s ease;
}
.nav-item:hover {
  color: var(--ce-text-strong);
  background: #1a1c1e;
}
.nav-item.active {
  color: var(--ce-text-strong);
  border-color: transparent;
  background: #1d1f22;
}
.nav-item.active::before {
  content: '';
  position: absolute;
  left: 10px;
  right: 10px;
  bottom: 0;
  width: auto;
  height: 1px;
  background: var(--ce-accent);
}
.nav-icon {
  flex: none;
  font-size: 18px;
}
.nav-item.active .nav-icon {
  color: currentColor;
}
.nav-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
  line-height: 1.25;
}
.nav-label {
  font-size: 14px;
  letter-spacing: 0;
}
.nav-badge {
  margin-left: auto;
  min-width: 20px;
  height: 18px;
  padding: 0 5px;
  border-radius: 4px;
  font-size: 11px;
  line-height: 18px;
  text-align: center;
  color: #fff;
  background: #463033;
  color: #f0b2b4;
}
.nav-item--more {
  display: none;
  border: 1px solid transparent;
  background: transparent;
  cursor: pointer;
}
.nav-sheet {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: none;
  align-items: flex-end;
  background: rgba(0, 0, 0, 0.62);
}
.nav-sheet section {
  width: 100%;
  padding: 16px;
  border-top: 1px solid var(--ce-panel-border);
  background: var(--ce-panel-solid);
}
.nav-sheet header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--ce-divider);
}
.nav-sheet h2 {
  margin: 0;
  color: var(--ce-text-strong);
  font-size: 20px;
  font-weight: 600;
}
.nav-sheet p {
  margin: 4px 0 0;
  color: var(--ce-text-dim);
  font-size: 13px;
}
.nav-sheet header button {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  border: 1px solid var(--ce-panel-border);
  border-radius: 4px;
  background: transparent;
  color: var(--ce-text-dim);
}
.nav-sheet nav {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1px;
  margin-top: 12px;
  background: var(--ce-divider);
  border: 1px solid var(--ce-divider);
}
.nav-sheet a {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 48px;
  padding: 0 12px;
  background: var(--ce-panel-solid);
  color: var(--ce-text);
  font-size: 14px;
  text-decoration: none;
}
.nav-sheet a.router-link-active {
  color: var(--ce-text-strong);
}
.nav-sheet a.router-link-active::after {
  content: '';
  position: absolute;
  right: 12px;
  bottom: 0;
  left: 12px;
  height: 1px;
  background: var(--ce-accent);
}
.nav-sheet-enter-active,
.nav-sheet-leave-active {
  transition: opacity 0.2s ease;
}
.nav-sheet-enter-active section,
.nav-sheet-leave-active section {
  transition: transform 0.25s var(--ce-ease);
}
.nav-sheet-enter-from,
.nav-sheet-leave-to {
  opacity: 0;
}
.nav-sheet-enter-from section,
.nav-sheet-leave-to section {
  transform: translateY(100%);
}
.sidebar-footer {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-top: 1px solid var(--ce-divider);
}
.collapse-btn {
  flex: none;
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border: 1px solid var(--ce-divider);
  border-radius: 3px;
  background: transparent;
  color: var(--ce-text-dim);
  cursor: pointer;
}
.collapse-btn:hover {
  color: #fff;
  border-color: var(--ce-panel-border-strong);
}
.ver {
  font-size: 12px;
  letter-spacing: 0;
  color: var(--ce-text-faint);
  white-space: nowrap;
}

/* 折叠为图标栏 */
.collapsed .nav-item {
  justify-content: center;
  padding: 0;
}
.collapsed .nav-text,
.collapsed .nav-group-label {
  display: none;
}
.collapsed .ver {
  display: none;
}
.collapsed .nav-badge {
  position: absolute;
  top: 4px;
  right: 4px;
  min-width: 16px;
  height: 16px;
  padding: 0 3px;
  font-size: 10px;
  line-height: 16px;
}

@media (max-width: 1100px) {
  .nav-text,
  .nav-group-label,
  .ver {
    display: none;
  }
  .nav-list {
    padding-inline: 6px;
  }
  .nav-item,
  .nav-item--sub {
    justify-content: center;
    height: 42px;
    padding: 0;
  }
  .sidebar-footer {
    justify-content: center;
    padding: 8px 0;
  }
}

@media (max-width: 700px) {
  .sidebar {
    position: fixed;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 30;
    height: 56px;
    border-top: 1px solid var(--ce-divider);
    border-right: 0;
  }
  .nav-list {
    flex-direction: row;
    align-items: stretch;
    gap: 0;
    padding: 0;
    overflow-x: auto;
    overflow-y: hidden;
  }
  .nav-group-label,
  .sidebar-footer {
    display: none;
  }
  .nav-item,
  .nav-item--sub {
    flex: 1 0 16.666%;
    min-width: 0;
    flex-direction: column;
    justify-content: center;
    gap: 2px;
    height: 56px;
    padding: 0 2px;
    border-radius: 0;
  }
  .nav-text {
    display: flex;
  }
  .nav-label {
    font-size: 12px;
    line-height: 1.1;
  }
  .nav-icon {
    font-size: 17px;
  }
  .nav-item.active::before {
    left: 8px;
    right: 8px;
  }
  .nav-badge {
    position: absolute;
    top: 5px;
    right: 8px;
    min-width: 15px;
    height: 15px;
    padding: 0 3px;
    font-size: 10px;
    line-height: 15px;
  }
  .nav-item--sub {
    display: none;
  }
  .nav-item--more {
    display: flex;
  }
  .nav-sheet {
    display: flex;
  }
}
.collapsed .sidebar-footer {
  justify-content: center;
  padding: 10px 0;
}
</style>
