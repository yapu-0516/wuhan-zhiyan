# CityEye 城市虚拟人群仿真模块

## 1. 技术融合方案

### 1.1 选型结论

采用 **Cesium 主场景 + 独立透明 Three.js 画布覆盖层**：

```text
Cesium Viewer canvas
  └── 原有城市、建筑、道路、事件、POI
Three.js overlay canvas
  └── 低模人物、危险区域、疏散目标
Vue HUD
  └── 人群控制台、统计和性能结果
```

该方案不修改 Cesium 的渲染循环和 WebGL 上下文，不需要侵入 Cesium 私有 API。
Three.js 画布设置 `pointer-events: none`，所有鼠标交互仍由 Cesium 接收。

代价是两层画布之间不共享深度缓冲，因此当前版本不处理建筑对人物的精确遮挡。
如果后续要求严格遮挡，可再替换为 Cesium 同上下文自定义渲染器，但当前阶段不承担该复杂度。

### 1.2 坐标系

Cesium 使用 WGS84 地理坐标和 ECEF 世界坐标；Three.js 使用以米为单位的局部 ENU 坐标。

局部原点：

```ts
origin = Cesium.Cartesian3.fromDegrees(centerLon, centerLat, 0)
enuToFixed = Cesium.Transforms.eastNorthUpToFixedFrame(origin)
fixedToEnu = Cesium.Matrix4.inverse(enuToFixed)
```

经纬度转 Three.js：

```ts
const fixed = Cesium.Cartesian3.fromDegrees(lon, lat, height)
const enu = Cesium.Matrix4.multiplyByPoint(fixedToEnu, fixed, new Cesium.Cartesian3())
// Cesium ENU: x=东, y=北, z=上
// Three.js:  x=东, y=上, z=-北
threePosition.set(enu.x, enu.z, -enu.y)
```

相机同步：

1. 将 `camera.positionWC` 转为局部 ENU，再映射为 Three.js 坐标。
2. 将 `directionWC` 和 `upWC` 转为向量后映射。
3. 使用 Cesium 相机 `fovy` 设置 Three.js 透视相机 FOV。
4. 在 `scene.postRender` 中同步并渲染 Three.js 覆盖层。

## 2. 模块架构

```text
frontend/src/components/
├── scene/crowd/
│   ├── types.ts            人物类型、统计和性能结果
│   ├── motion.ts           个体速度、反应延迟与拥挤降速参数
│   ├── hazard.ts           Demo 级风险场扩展参数
│   ├── roadGraph.ts        临时道路图、风险加权路径和 Dijkstra
│   └── crowdLayer.ts       坐标转换、相机同步、实例化人物、行为与疏散
├── pages/
│   └── CrowdSimulationPanel.vue
│                           人数/类型/聚集/疏散/统计/性能测试控制台
├── dashboard/SceneToolbar.vue
│                           人群仿真入口
├── CesiumViewer.vue        创建并管理 CrowdLayer
└── views/Dashboard.vue     打开人群控制台
```

### 2.1 人物模型

角色采用参考视频中的低多边形胶囊人风格，由 Three.js 基础几何体合并：

- 深色低多边形球体：头部
- 胶囊体：躯干、双臂、双腿
- 盒状鞋底：增强行走方向与落脚感
- 每个顶点携带肢体编号和明度，同一实例网格中即可表现深色头部与彩色身体
- 四种独立 `InstancedMesh`：居民、游客、消防员、救援人员

颜色：

| 类型 | 颜色 |
| --- | --- |
| 居民 | `#4fc3f7` |
| 游客 | `#f0c050` |
| 消防员 | `#ff5a5a` |
| 救援人员 | `#4dd984` |

### 2.2 实例化策略

每个人员类型只使用一个 `InstancedMesh`，每帧更新实例矩阵和步态实例属性。1000 人混合人群
通常只有 **4 个 Draw Calls**，而不是 4000—6000 个独立 Mesh；手臂和腿部动作在顶点着色器中完成，
不会为每个关节增加独立 Draw Call。

```ts
const mesh = new THREE.InstancedMesh(geometry, material, MAX_PEOPLE)
mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage)
mesh.frustumCulled = false
```

## 3. 关键接口

`CesiumViewer` 对外提供：

```ts
getCrowd(): CrowdLayer | null
```

`CrowdLayer` 主要接口：

```ts
add(type, lon, lat, scale?, heading?): string
remove(id: string): boolean
clear(): void
setScale(id: string, scale: number): boolean
setHeading(id: string, heading: number): boolean
walkTo(id: string, lon: number, lat: number): boolean
walkPath(id: string, points: [number, number][]): boolean
spawn(count: number, type?: SpawnType): number
spawnAt(count: number, type: SpawnType, lon: number, lat: number, radiusM?: number): number
evacuate(lon: number, lat: number, radiusM: number): number
getStats(): CrowdStats
benchmark(sizes?: number[]): Promise<CrowdBenchmarkRow[]>
```

## 4. 行为与仿真

### 4.1 单人行为

- 站立：无目标路径，保持位置和朝向。
- 行走：目标点转换为 Three.js 局部坐标，逐帧以速度移动。
- 步态：双腿交替前后摆动，双臂反向摆动，身体随步频轻微起伏和侧移。
- 转向：使用最短角度差和指数阻尼平滑朝向，不在折线节点瞬间转头。
- 混合：起步和停止时步态幅度平滑过渡，不会从静止瞬间切成机械摆腿。
- 停止/到达：路径耗尽后切换为 `idle` 或 `arrived`。
- 缩放和旋转：通过实例矩阵即时更新。
- 经纬度定位：创建和删除均使用 WGS84 经纬度接口。

### 4.2 批量生成

- 支持四种单一类型和混合人群。
- 默认优先在现有道路中心线两侧约 2.1–3.6 m 偏移分布，作为人行道的近似表现。
- 如果路网尚未加载，则在当前示范区包围盒内随机分布。
- 支持围绕指定经纬度、指定半径增加人员，例如“中心突增 1000 名游客”。

### 4.3 聚集与疏散

疏散使用轻量道路导向算法：

1. 以危险点为中心生成危险区域。
2. 用当前道路折线构建临时拓扑图；共享坐标的交叉点合并，相邻道路端点允许 8 m 内连接。
3. 风险内人员先进入 `reacting` 状态，并按个体反应延迟等待 0.15–6.5 秒。
4. 响应后以风险外 70 m 的道路节点为候选，按四个方位收敛为最多 4 个演示出口，
   再用多源 Dijkstra 计算路网路径。
5. 路径边按危险区暴露程度加权，因此可以绕开高风险区，但不会把危险区内道路直接判为不可通行。
6. 人员到达出口后进入 `waiting`，出口按每秒 1.6 人的临时服务率释放，随后变为 `arrived`。
7. 无可用道路时，沿危险点向外方向直线撤离。

每个人员使用类型化步行速度区间：居民 1.0–1.42 m/s、游客 0.82–1.22 m/s、
消防员 1.35–1.68 m/s、救援人员 1.2–1.55 m/s。1.35 m 邻域内人数增加时会降低
有效步速，最低降至 28%，用于表现轻量拥堵。

局部避让使用空间哈希查找邻近人员，并保持约 0.46 m 间隔；单帧最大分离步长为
按 0.55 m/s 的时间步平滑修正，而不是直接瞬移。这是低成本的视觉避让，不是社会力、
ORCA 或带障碍物的路径约束模型。

当前图搜索是真实道路拓扑上的临时近似，但边宽、方向、通行能力、真实人行道和出口容量仍缺失。
出口服务率是演示参数，不是实测容量。生产级仿真应替换为带容量约束的步行图、障碍物约束和
经标定的局部避障。

### 4.4 Demo 级动态风险场

风险区从事件基础半径开始，按事件类型平滑扩展：

| 事件 | 扩展周期 | 最大半径倍数 | 行为 |
| --- | ---: | ---: | --- |
| 建筑火情 | 45 s | 1.38 | 烟气影响区扩大，路线持续重算 |
| 道路积水 | 75 s | 1.48 | 积水区扩大，路径提高危险边成本 |
| 建筑异常 | 30 s | 1.12 | 警戒区小幅扩大 |
| 交通拥堵 | 40 s | 1.18 | 不作为人员疏散，仅影响车辆 |

疏散启动后每 4 秒根据当前风险半径重新运行路网搜索。界面显示当前风险半径和动态重规划次数。
这些曲线是演示参数，不是 CFD、二维水动力或结构有限元计算结果。

风险扩大后，新进入风险半径但尚未登记的人员会分批加入疏散；进度使用“已安全人数 /
已纳入疏散人数”。地图同时绘制青色代表性路线、黄色高风险路段和红色封闭核心路段。

四个演示出口的临时服务率为 2.2、1.8、1.5、1.2 人/秒。这个差异用于稳定展示瓶颈和
出口切换，不是真实出口容量。

## 5. 分阶段实现清单

| 阶段 | 内容 | 状态 |
| --- | --- | --- |
| 1 | Three.js/Cesium 叠加、相机同步、ENU 坐标转换 | 完成 |
| 2 | 单人创建、删除、缩放、旋转、经纬度定位 | 完成 |
| 3 | 站立、行走、转向、停止、路径目标 | 完成 |
| 4 | 批量生成、人员类型、区域人数统计 | 完成 |
| 5 | 中心聚集、危险区、沿道路疏散、安全点标记 | 完成 |
| 6 | InstancedMesh、合并几何、远景可读性缩放、性能测试 | 完成 |
| 7 | 道路侧向站位、类型化步速、个体反应延迟、轻量拥堵与局部避让 | 完成 |
| 8 | 胶囊人模型、交替步态、反向摆臂、平滑转向和步态混合 | 完成 |
| 9 | 临时道路拓扑、风险加权最短路、独立出口排队和疏散进度统计 | 完成 |
| 10 | 事件化动态风险区、周期重规划、交通场景差异化处置 | 完成 |
| 11 | 固定演示场景、1/4/8 倍速、四出口、路线图层、过程时间线和完成摘要 | 完成 |
| 12 | 交通拥堵专用车辆视图、外围减速、核心区停车和人工启动绕行 | 完成 |

## 6. 性能实测

测试环境：Chrome 155，Windows 11，AMD Radeon 610M（ANGLE/D3D11），
Three.js 覆盖层画布 `1254 × 1123`。

测试口径：每个规模预热后连续渲染 20 帧，使用 WebGL `finish()` 等待提交完成；
表中“渲染吞吐”是人群覆盖层自身的等效吞吐，不等同于显示器刷新率，也不包含 Cesium
场景其他图层的 GPU 成本。

| 人数 | 渲染吞吐 / s | 单帧耗时 ms | Draw Calls | 三角形 |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 1142.9 | 0.88 | 1 | 424 |
| 10 | 1324.5 | 0.76 | 3 | 4,240 |
| 50 | 1298.7 | 0.77 | 4 | 21,200 |
| 100 | 1058.2 | 0.95 | 4 | 42,400 |
| 500 | 424.6 | 2.35 | 4 | 212,000 |
| 1000 | 225.2 | 4.44 | 4 | 424,000 |

结果说明：

- Draw Call 不随人数线性增长，四种人员类型最多 4 次。
- 胶囊人增加了轮廓细节，三角形数随人数线性增长，1000 人约为 42.4 万三角形。
- 1000 人时单帧人群覆盖层提交耗时约 4.44 ms；实际端到端 FPS 仍受 Cesium 场景、
  浏览器合成、显卡和后台窗口节流影响。
- 远景采用最大 12 倍的可读性放大，近景恢复真实人物比例，避免城市总览时人物完全不可见。

## 7. 关键代码

### 7.1 坐标转换

```ts
private lonLatToLocal(lon: number, lat: number, height: number): THREE.Vector3 {
  const fixed = Cesium.Cartesian3.fromDegrees(lon, lat, height)
  const local = Cesium.Matrix4.multiplyByPoint(
    this.fixedToEnu,
    fixed,
    new Cesium.Cartesian3()
  )
  return new THREE.Vector3(local.x, local.z, -local.y)
}
```

### 7.2 实例矩阵

```ts
const distance = Math.hypot(person.x - cameraPosition.x, person.z - cameraPosition.z)
scale.setScalar(person.scale * Math.max(1, Math.min(12, distance / 180)))
matrix.compose(position, quaternion, scale)
mesh.setMatrixAt(i, matrix)
mesh.instanceMatrix.needsUpdate = true
```

### 7.3 疏散路径选择

`roadGraph.ts` 将道路顶点合并为图节点，从风险区外的候选出口做多源 Dijkstra。
边成本由长度和危险区暴露程度共同决定；每个人员的最后偏移位置通过最近路段投影接入临时图，
因此路径会沿连续道路跨过多条路段，而不是只走到单条道路的最近端点。

## 8. 验证记录

- 单人：在 55 m 视距下可见，定位到人群中心成功。
- 100 人：浏览器成功生成，统计与类型分布同步更新。
- 500 人：区域中心聚集后可见，统计为 500 名游客。
- 应急演练：风险内人员先显示反应等待，随后转入 `moving` 状态；演练面板同步显示等待、移动和到达人数。
- 单人近景：双腿和双臂交替摆动，人物沿路径连续移动，转向使用平滑角度插值。
- 混合人群：胶囊人头部、躯干、四肢和落脚方向可辨识，重叠时按时间步平滑分离。
- 临时路网：真实道路数据可构建连通图，风险内人员沿多段道路移动到风险区外节点。
- 疏散统计：反应、移动、出口排队和安全人数分别计数，进度只按真正到达安全节点的人数计算。
- 动态风险：风险半径随时间扩大，活动疏散每 4 秒重新选择风险加权路径。
- 事件差异：交通拥堵显示“无需人员疏散”，不会误触发大规模人员移动。
- Demo 场景：火灾、内涝、建筑异常和交通拥堵可固定选择，不再依赖随机抽取。
- 动态暴露：风险区扩大后，新进入风险区的人员会加入疏散统计和路径规划。
- 可视化证据：地图绘制代表性路线、高风险路段、安全出口和随时间变化的风险范围。
- 过程复盘：右侧显示最近两条推演事件、当前风险半径、重规划次数和启用出口数。
- 车辆联动：进入风险区或道路被高风险区截断的车辆，会沿临时安全路径绕出事件影响区。
- 交通疏导：交通拥堵不触发人员疏散；车辆先在事件外围降至 25% 速度、核心区停车，
  启动“交通疏导”后再沿临时安全路径分流。
- 交通指标：显示平均车速、排队车辆、受影响车辆和累计绕行车辆。
- 性能测试：1、10、50、100、500、1000 人均完成。
- 原 Cesium 地图、事件、道路、建筑、AI 解析和报告入口仍可操作。
- `vue-tsc`、Vite 构建、ESLint 和前端 49 项单测通过。

## 9. 当前限制

1. 独立透明画布不共享深度缓冲，人物不会被建筑严格遮挡。
2. 人物位置使用零高程平面，尚未采样真实地形和桥面高度。
3. 道路旁 2.1–3.6 m 偏移不是实际 OSM 人行道几何；当前道路数据不足以判断围墙、台阶、
   过街设施和建筑出入口。
4. 局部避让只处理人员间距，没有建筑、围栏和道路边界障碍，可能仍出现穿越建筑的情况。
5. 临时图使用道路中心线，不是真实步行网络；交叉口和路段宽度仍待 B 提供。
6. 出口每秒 1.6 人的服务率是统一演示参数，没有按实际宽度、楼梯或闸口容量标定。
7. 当前人数上限为 6000，界面常规上限为 1000。
8. 尚未接入真实事件自动触发和 LLM 情景参数；当前由控制台手动触发。
9. 动态风险场采用事件化平滑扩展曲线，没有烟气、水深、流速或结构力学物理求解。
10. 四个演示出口和不同服务率是人工设置的展示参数，真实出口仍需 B 的步行网络和容量数据。

这些限制不影响当前“轻量、可运行、可演示”的目标，也为后续替换路径规划和场景编排
保留了清晰边界。
