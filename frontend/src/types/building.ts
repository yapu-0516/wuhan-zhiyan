// 城市建筑类型定义
// 阶段5：用于模拟武汉测试建筑，后续阶段可替换为真实武汉 3D Tiles 数据。
// 结构保持简单：id / 名称 / 经纬度 / 高度，足以支撑 Box Entity 渲染与点击信息。

export interface Building {
  /** 建筑编号，如 B001 */
  id: string
  /** 建筑名称 */
  name: string
  /** 经度 */
  longitude: number
  /** 纬度 */
  latitude: number
  /** 建筑高度（米） */
  height: number
}
