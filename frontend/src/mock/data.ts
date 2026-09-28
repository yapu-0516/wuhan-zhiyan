// 模拟数据资产清单（阶段11）
// 明确标记为 mock：第3周前端原型使用，第4周接 FastAPI 后由真实接口返回。
export interface DataItem {
  /** 数据名称 */
  name: string
  /** 数据类型 */
  type: string
  /** 获取时间 yyyy-MM-dd HH:mm */
  time: string
  /** 数据状态 */
  status: string
}

export const mockDataList: DataItem[] = [
  { name: '武汉示范区遥感影像', type: '遥感影像', time: '2026-09-28 08:00', status: '已入库' },
  { name: '无人机测试影像', type: '无人机影像', time: '2026-09-28 09:30', status: '处理中' },
  { name: '城市道路视频', type: '视频流', time: '2026-09-28 10:00', status: '采集中' },
  { name: '三维城市测试数据', type: '三维模型', time: '2026-09-27 16:00', status: '已入库' }
]
