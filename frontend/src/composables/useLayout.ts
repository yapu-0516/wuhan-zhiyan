// 应用外壳布局状态（侧边栏折叠），记忆到 localStorage
import { ref, watch } from 'vue'

const KEY = 'cityeye.sidebarCollapsed'

function read(): boolean {
  try {
    // 总览以城市画面为主，首次进入使用图标导航栏；手动展开后记住用户选择。
    return localStorage.getItem(KEY) !== '0'
  } catch {
    return true
  }
}

const sidebarCollapsed = ref(read())

watch(sidebarCollapsed, (v) => {
  try {
    localStorage.setItem(KEY, v ? '1' : '0')
  } catch {
    /* 隐私模式等不可用时忽略 */
  }
})

export function useLayout() {
  return { sidebarCollapsed, toggleSidebar: () => (sidebarCollapsed.value = !sidebarCollapsed.value) }
}
