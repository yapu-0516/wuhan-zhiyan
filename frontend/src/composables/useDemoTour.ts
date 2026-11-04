/**
 * 一键演示（导览）：脚本化的 7 步镜头 + 字幕，适合 5 分钟现场演示。
 *
 *  1 城市全域感知   太空俯冲切入示范区
 *  2 数字孪生底座   环绕 CBD 高层建筑群
 *  3 实时路网态势   聚焦最拥堵路段，高亮拥堵流光
 *  4 AI 火情识别    在线：调用 POST /api/demo/scenario 跑真实算法流水线，等待 WS event.created 后飞往新事件；
 *                   离线/失败：自动选择已有最高等级火情事件
 *  5 一键派单处置   在事件详情中打开派单表单并提交（状态机合法时）
 *  6 建筑沉降预警   飞往沉降预警建筑并展示监测曲线
 *  7 联动疏散推演   进入火灾演练页并自动启动演示倍速下的疏散
 *
 * 可随时按 Esc 或点击"退出演示"取消；所有等待均可中断。
 */
import { onBeforeUnmount, reactive } from 'vue'
import { triggerScenario } from '@/api/system'
import { getEvent } from '@/api/event'
import { apiState } from '@/api/http'
import { useCityEvents } from './useCityEvents'
import type { SceneApi, TourFocus, TourState } from '@/components/scene/types'
import type { CityEvent } from '@/types/event'
import { SEVERITY_META, STATUS_TRANSITIONS } from '@/types/event'
import { RISK_LEVEL_META, TRAFFIC_LEVEL_META } from '@/types/building'

class TourCancelled extends Error {}

const TOTAL = 7

export function useDemoTour(
  getApi: () => SceneApi | null,
  enterEmergencyDrill?: () => Promise<void>
) {
  const state = reactive<TourState>({ running: false, index: 0, total: TOTAL, title: '', caption: '', focus: null })
  const { lastCreated, events, getEventById, upsert } = useCityEvents()
  let runId = 0

  function guard(id: number) {
    if (id !== runId) throw new TourCancelled()
  }

  async function sleep(ms: number, id: number) {
    const end = Date.now() + ms
    while (Date.now() < end) {
      guard(id)
      await new Promise((r) => window.setTimeout(r, Math.min(150, Math.max(0, end - Date.now()))))
    }
    guard(id)
  }

  /** 轮询等待条件成立（可中断），超时返回 null */
  async function waitFor<T>(fn: () => T | null | undefined, timeout: number, id: number): Promise<T | null> {
    const end = Date.now() + timeout
    while (Date.now() < end) {
      guard(id)
      const v = fn()
      if (v) return v
      await new Promise((r) => window.setTimeout(r, 200))
    }
    return null
  }

  function step(index: number, title: string, caption: string, focus: TourFocus | null = null) {
    state.index = index
    state.title = title
    state.caption = caption
    state.focus = focus
  }

  function pickFireEvent(): CityEvent | null {
    const list = events.value.filter((e) => e.event_type === 'fire')
    const score = (e: CityEvent) => (e.status === 'resolved' ? 0 : 10) + (SEVERITY_META[e.severity]?.rank ?? 0)
    const sorted = [...list].sort((a, b) => score(b) - score(a) || b.timestamp.localeCompare(a.timestamp))
    if (sorted[0]) return sorted[0]
    return events.value.find((e) => e.status !== 'resolved') ?? null
  }

  async function run(api: SceneApi, id: number) {
    const stats = api.sceneStats()

    // 1 城市全域感知
    step(
      1,
      '城市全域感知',
      `从卫星视角切入汉口沿江示范区：${stats.buildings || '—'} 栋真实建筑、${stats.roads || '—'} 条主干道、${stats.pois || '—'} 处应急资源已接入城市智眼。`,
      'kpi'
    )
    await api.flyFromSpace()
    await sleep(800, id)

    // 2 数字孪生底座
    const [clon, clat] = api.denseCenter()
    step(
      2,
      '三维数字孪生底座',
      `基于 OpenStreetMap 建筑轮廓按实测/楼层/估算高度拉伸，${stats.monitored} 栋重点建筑接入沉降监测；红色脉冲为存在活动事件的建筑。`
    )
    await api.orbit(clon, clat, { range: 1500, pitch: -27, speed: 8 })
    await sleep(9500, id)
    api.stopOrbit()

    // 3 实时路网态势
    api.setLayerVisible('roads', true)
    api.highlightCongestion(true)
    const traffic = api.cityTraffic()
    const spot = api.congestedSpot()
    const tpiText = traffic ? `全路网 TPI ${traffic.tpi.toFixed(1)}（${TRAFFIC_LEVEL_META[traffic.level].label}）` : '路网实时路况'
    step(
      3,
      '实时路网态势',
      `${tpiText}；流光速度对应实时车速，${spot ? `当前最拥堵路段：${spot.name}（TPI ${spot.tpi.toFixed(1)}）` : '红色为严重拥堵路段'}。`,
      'traffic'
    )
    if (spot) await api.flyTo(spot.lon, spot.lat, { range: 1300, pitch: -42, duration: 2.4 })
    else await api.flyHome(2.4)
    guard(id)
    await sleep(6500, id)
    api.highlightCongestion(false)

    // 4 AI 火情识别
    let target: CityEvent | null = null
    if (apiState.mode === 'live') {
      step(4, 'AI 火情识别', '正在调用 FlameNet-Lite 火情识别算法，分析无人机巡检影像…', 'feed')
      const before = lastCreated.value
      try {
        const res = await triggerScenario('fire')
        guard(id)
        target = await waitFor(
          () => {
            const e = lastCreated.value
            if (e && e !== before && e.event_type === 'fire') return e
            return res.event_id ? getEventById(res.event_id) : null
          },
          6000,
          id
        )
        if (!target && res.event_id) {
          const e = await getEvent(res.event_id).catch(() => undefined)
          guard(id)
          if (e) {
            upsert(e)
            target = e
          }
        }
      } catch (e) {
        if (e instanceof TourCancelled) throw e
        console.warn('[tour] 触发演示场景失败，改用已有火情事件', e)
      }
    }
    if (!target) target = pickFireEvent()
    if (target) {
      step(
        4,
        'AI 火情识别',
        `识别到「${target.name}」，置信度 ${Math.round((target.confidence ?? 0) * 100)}%，${SEVERITY_META[target.severity]?.label ?? ''}，已自动生成事件并推送指挥中心。`,
        'feed'
      )
      await api.flyToEvent(target.id, { open: true, range: 650, pitch: -33, duration: 2.6 })
      await sleep(5500, id)

      // 5 一键派单处置
      const current = getEventById(target.id) ?? target
      if (STATUS_TRANSITIONS[current.status]?.includes('processing') && current.status !== 'resolved') {
        step(5, '一键派单处置', '值班员在事件详情中选择处置单位并派单，事件状态由「待核查」流转为「处置中」。', 'feed')
        await sleep(1200, id)
        const updated = await api.demoDispatch()
        guard(id)
        step(
          5,
          '一键派单处置',
          updated
            ? `已派单至「${updated.assignee ?? '属地处置单位'}」，事件进入处置中，全流程留痕可追溯。`
            : '派单演示未完成（请检查后端连接），可在事件中心继续处置。',
          'feed'
        )
      } else {
        step(
          5,
          '处置闭环跟踪',
          `该事件当前状态：处置中${current.assignee ? `（${current.assignee}）` : ''}，指挥中心实时跟踪处置进度。`,
          'feed'
        )
      }
      await sleep(5000, id)
    } else {
      step(4, 'AI 火情识别', '当前暂无火情事件，系统持续监测中。', 'feed')
      await sleep(3000, id)
    }

    // 6 建筑沉降预警
    api.closePanels()
    const b = api.findRiskBuilding()
    if (b) {
      const risk = RISK_LEVEL_META[b.risk_level ?? 'watch']
      step(
        6,
        '建筑沉降预警',
        `「${b.name}」接入 InSAR/水准沉降监测，风险等级「${risk.label}」；右侧曲线为累计沉降时序与速率分析。`
      )
      await api.flyToBuilding(b.id, { open: true, range: Math.max(520, b.height * 4.5), pitch: -26, duration: 2.6 })
      await sleep(7000, id)
    } else {
      step(6, '建筑沉降监测', '重点建筑沉降监测运行正常，暂无关注/预警建筑。')
      await sleep(2500, id)
    }

    // 7 联动疏散推演
    api.closePanels()
    if (enterEmergencyDrill) {
      step(
        7,
        '联动疏散推演',
        '进入应急演练：烟气风险扩大后，系统沿临时道路图重新计算安全出口、通行路径和出口排队。',
        'safety'
      )
      await sleep(2500, id)
      await enterEmergencyDrill()
      return
    }
    step(7, '感知 · 分析 · 决策 · 处置', '城市智眼：多源感知接入、AI 智能识别、三维态势研判、事件闭环处置。', 'safety')
    await api.flyHome(3)
    await sleep(3500, id)
  }

  function onKey(e: KeyboardEvent) {
    if (e.key === 'Escape') stop()
  }

  function cleanup() {
    window.removeEventListener('keydown', onKey)
    state.running = false
    state.focus = null
    state.title = ''
    state.caption = ''
    state.index = 0
  }

  async function start() {
    const api = getApi()
    if (!api || state.running) return
    const id = ++runId
    state.running = true
    window.addEventListener('keydown', onKey)
    try {
      await run(api, id)
    } catch (e) {
      if (!(e instanceof TourCancelled)) console.warn('[tour] 演示中断', e)
    } finally {
      if (id === runId) {
        api.stopOrbit()
        api.highlightCongestion(false)
        cleanup()
      }
    }
  }

  function stop() {
    if (!state.running) return
    runId++
    const api = getApi()
    api?.cancelFlight()
    api?.stopOrbit()
    api?.highlightCongestion(false)
    cleanup()
  }

  onBeforeUnmount(() => {
    runId++
    window.removeEventListener('keydown', onKey)
  })

  return { state, start, stop }
}
