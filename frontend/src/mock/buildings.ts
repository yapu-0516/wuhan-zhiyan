// 模拟武汉测试建筑数据（阶段5）
// 明确标记为 mock 数据：当前为测试用简单盒状建筑，并非真实武汉建筑模型。
// 后续阶段可替换为真实武汉三维城市数据 / 3D Tiles，Building 结构与加载逻辑保持稳定。
import type { Building } from '@/types/building'

// 4 个测试建筑。
// 相机默认在 (114.30, 30.52, 800m)、pitch=-45° 俯视，朝北。
// pitch=-45° 时近处存在视野盲区，因此建筑布置在相机北方约 500~1400m，
// 正好落在 -45° 俯视的视野中心带，便于观察与点击。
// 1° 纬度 ≈ 111km，500m ≈ 0.0045°，1400m ≈ 0.0126°。
export const mockBuildings: Building[] = [
  {
    id: 'B001',
    name: '测试建筑1',
    longitude: 114.299,
    latitude: 30.5245,
    height: 60
  },
  {
    id: 'B002',
    name: '测试建筑2',
    longitude: 114.301,
    latitude: 30.5270,
    height: 95
  },
  {
    id: 'B003',
    name: '测试建筑3',
    longitude: 114.300,
    latitude: 30.5300,
    height: 45
  },
  {
    id: 'B004',
    name: '测试建筑4',
    longitude: 114.302,
    latitude: 30.5330,
    height: 120
  }
]
