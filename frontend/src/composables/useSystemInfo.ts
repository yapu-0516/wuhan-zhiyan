// 系统信息（模块级缓存）：示范区名称/范围、演示模式、算法清单。顶栏与三维场景共用。
import { computed, shallowRef } from 'vue'
import { getSystemInfo } from '@/api/system'
import type { SystemInfo } from '@/types/api'
import { DEFAULT_REGION } from '@/config/cesium'

const info = shallowRef<SystemInfo | null>(null)
let pending: Promise<SystemInfo | null> | null = null

export function useSystemInfo() {
  function load(force = false): Promise<SystemInfo | null> {
    if (!pending || force) {
      pending = getSystemInfo()
        .then((i) => {
          info.value = i
          return i
        })
        .catch((e) => {
          console.warn('[system] 系统信息获取失败', e)
          pending = null
          return null
        })
    }
    return pending
  }

  const region = computed(() => {
    const r = info.value?.region
    const valid = r && Array.isArray(r.center) && r.center.length === 2 && Array.isArray(r.bbox) && r.bbox.length === 4
    return valid ? { name: r.name || DEFAULT_REGION.name, center: r.center, bbox: r.bbox } : { ...DEFAULT_REGION }
  })

  const demoMode = computed(() => !!info.value?.demo_mode)

  return { info, load, region, demoMode }
}
