/**
 * Cesium Ion 访问令牌配置
 *
 * 说明：
 *   - 当前阶段（第3周）为纯本地运行，三维场景使用 Cesium 自带的离线影像，
 *     不依赖 Cesium Ion 在线服务，因此此处 Token 留空即可正常运行。
 *   - 若后续阶段需要接入 Ion 提供的高清卫星影像 / Cesium World Terrain /
 *     Cesium OSM 建筑白模 / 3D Tiles 城市数据，请到
 *     https://ion.cesium.com/signup 免费注册，把 Token 填到下方 CESIUM_ION_TOKEN。
 *   - 该常量在 CesiumViewer 初始化时读取，未来切换数据源只改这里即可。
 */
export const CESIUM_ION_TOKEN = ''
