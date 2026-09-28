<script setup lang="ts">
// 阶段2/4/5：Cesium 三维场景 + 武汉默认视角 + 测试建筑
// 设计要点：
//   1. 无 Ion Token 时使用 Cesium 自带的 NaturalEarthII 离线影像，保证本地可运行；
//   2. 地形用默认椭球（无地形起伏），不依赖任何在线服务；
//   3. 关闭非必要小部件，让三维场景成为视觉主体；
//   4. 默认定位武汉（114.30, 30.52, 800m, pitch=-45° 俯视朝北）；
//   5. 加载 4 个测试建筑（Box Entity），点击弹出建筑信息浮层；
//   6. 通过 defineExpose 暴露 viewer 实例，供后续阶段（事件/相机定位）复用。
import { onMounted, onBeforeUnmount, ref, shallowRef, watch } from 'vue'
import * as Cesium from 'cesium'
import 'cesium/Build/Cesium/Widgets/widgets.css'
import { useRoute } from 'vue-router'
import { CESIUM_ION_TOKEN } from '@/config/cesium'
import { mockBuildings } from '@/mock/buildings'
import type { Building } from '@/types/building'
import { useCityEvents } from '@/composables/useCityEvents'
import { EVENT_TYPE_META, type CityEvent } from '@/types/event'
import EventDetail from '@/components/EventDetail.vue'

// 武汉默认视角：项目以武汉为示范城市，打开即定位武汉上空而非全球视角。
// 高度 800m + pitch=-45° 俯视朝北；测试建筑布置在北方 500~1400m 落在视野中心。
// 阶段9 事件中心定位跳转也会复用此常量作为回退基准点。
const WUHAN_CENTER = {
  longitude: 114.30,
  latitude: 30.52,
  height: 800
}

const containerRef = ref<HTMLDivElement | null>(null)
// Cesium.Viewer 持有大段 WebGL 资源，用 shallowRef 避免深度响应式代理
const viewer = shallowRef<Cesium.Viewer | null>(null)
// 当前选中的建筑（点击建筑后填充，模板渲染信息浮层）
const selectedBuilding = ref<Building | null>(null)
// 阶段8：当前选中的事件（点击事件后填充，模板渲染 EventDetail 浮层）
const selectedEvent = ref<CityEvent | null>(null)
// 点击事件处理器，卸载时需要销毁
let clickHandler: Cesium.ScreenSpaceEventHandler | null = null

// 阶段9：事件中心点击行 → 跳转 /dashboard?eventId=xxx，CesiumViewer 监听并 flyTo
const route = useRoute()
const { events, getEventById } = useCityEvents()

// 飞到指定事件位置并选中显示详情。viewer 未就绪时跳过（onMounted 末尾会再触发一次）。
function flyToEvent(id: unknown) {
  if (!id || typeof id !== 'string') return
  const e = getEventById(id)
  if (!e || !viewer.value) return
  viewer.value.camera.flyTo({
    destination: Cesium.Cartesian3.fromDegrees(e.longitude, e.latitude, 500),
    orientation: { heading: 0, pitch: Cesium.Math.toRadians(-45), roll: 0 },
    duration: 1.5
  })
  selectedEvent.value = e
}
watch(() => route.query.eventId, (id) => flyToEvent(id))

onMounted(() => {
  if (CESIUM_ION_TOKEN) {
    Cesium.Ion.defaultAccessToken = CESIUM_ION_TOKEN
  }

  viewer.value = new Cesium.Viewer(containerRef.value as HTMLElement, {
    // 不创建默认的 Cesium Ion 在线底图，避免 Token 依赖；
    // 离线影像稍后异步加载（Cesium 1.106+ provider 推荐用 fromUrl）
    baseLayer: false,
    baseLayerPicker: false,
    geocoder: false,
    homeButton: false,
    sceneModePicker: false,
    navigationHelpButton: false,
    animation: false,
    timeline: false,
    fullscreenButton: false,
    infoBox: false,
    selectionIndicator: false
  })

  // 关闭默认的星空与大气过亮，适配后续深色城市风格
  viewer.value.scene.skyBox.show = false
  viewer.value.scene.backgroundColor = Cesium.Color.fromCssColorString('#0b1020')

  // 阶段4：默认定位到武汉
  // setView 直接定位（无动画），打开城市之眼即看到武汉区域，可旋转/缩放/平移。
  // pitch=-45° 倾斜俯视，能呈现城市立体感；heading=0 朝北。
  viewer.value.camera.setView({
    destination: Cesium.Cartesian3.fromDegrees(
      WUHAN_CENTER.longitude,
      WUHAN_CENTER.latitude,
      WUHAN_CENTER.height
    ),
    orientation: {
      heading: 0,
      pitch: Cesium.Math.toRadians(-45),
      roll: 0
    }
  })

  // 异步加载 Cesium 自带的 NaturalEarthII 离线影像（同步构造器已弃用）
  Cesium.TileMapServiceImageryProvider.fromUrl(
    Cesium.buildModuleUrl('Assets/Textures/NaturalEarthII')
  ).then((provider) => {
    viewer.value?.imageryLayers.addImageryProvider(provider)
  })

  // 阶段5：加载测试建筑（Box Entity）
  // 用简单盒状建筑模拟武汉城市对象，代码结构允许后续替换为真实 3D Tiles。
  // position 取 height/2 让盒子底部贴在椭球面上；宽深 50m 便于在 800m 视角观察与点击。
  // 注意：box.material 必须用 ColorMaterialProperty 包裹 Color，
  //   直接传 Color 实例会触发 "Unable to infer material type" DeveloperError。
  mockBuildings.forEach((b) => {
    viewer.value?.entities.add({
      id: b.id,
      name: b.name,
      position: Cesium.Cartesian3.fromDegrees(b.longitude, b.latitude, b.height / 2),
      box: {
        dimensions: new Cesium.Cartesian3(50, b.height, 50),
        material: new Cesium.ColorMaterialProperty(
          Cesium.Color.fromCssColorString('#3a7bd5').withAlpha(0.75)
        ),
        outline: true,
        outlineColor: Cesium.Color.fromCssColorString('#7fb3ff')
      }
    })
  })

  // 阶段12：补充一条测试道路（Polyline）连接部分建筑，作为城市对象之一
  // 满足验收"建筑/道路/地形/地球"。后续可替换为真实路网数据。
  viewer.value?.entities.add({
    id: 'ROAD_TEST_01',
    name: '测试道路',
    polyline: {
      positions: Cesium.Cartesian3.fromDegreesArray([
        114.299, 30.5245,
        114.301, 30.5270,
        114.300, 30.5300,
        114.302, 30.5330
      ]),
      width: 4,
      material: new Cesium.ColorMaterialProperty(
        Cesium.Color.fromCssColorString('#e6c84a').withAlpha(0.9)
      ),
      clampToGround: true
    }
  })

  // 阶段7：加载城市事件为三维空间对象
  // 从全局事件 store 取数据，按类型用 Point + Label 渲染：
  //   - Point：彩色圆点（颜色取 EVENT_TYPE_META），醒目易点击；
  //   - Label：显示该类型 Emoji，浮在点上方；
  //   - disableDepthTestDistance 设为无穷，使事件点不被建筑遮挡、始终可见。
  // 事件 entity 的 id 用事件 id（E001 等），阶段8 点击 pick 据此匹配详情。
  events.value.forEach((e) => {
    const meta = EVENT_TYPE_META[e.event_type]
    viewer.value?.entities.add({
      id: e.id,
      name: e.name,
      position: Cesium.Cartesian3.fromDegrees(e.longitude, e.latitude, 10),
      point: {
        pixelSize: 18,
        color: Cesium.Color.fromCssColorString(meta.color),
        outlineColor: Cesium.Color.WHITE,
        outlineWidth: 2,
        disableDepthTestDistance: Number.POSITIVE_INFINITY
      },
      label: {
        text: meta.icon,
        font: '22px sans-serif',
        pixelOffset: new Cesium.Cartesian2(0, -24),
        disableDepthTestDistance: Number.POSITIVE_INFINITY
      }
    })
  })

  // 阶段5/8：点击三维对象显示信息
  // 通过 ScreenSpaceEventHandler 监听左键，pick 到实体后：
  //   - 命中建筑（id 在 mockBuildings）→ 显示建筑信息浮层
  //   - 命中事件（id 在事件 store）→ 显示 EventDetail 浮层
  //   - 点击空白 → 清除选中
  clickHandler = new Cesium.ScreenSpaceEventHandler(viewer.value.scene.canvas)
  clickHandler.setInputAction((movement: { position: Cesium.Cartesian2 }) => {
    const picked = viewer.value?.scene.pick(movement.position)
    if (Cesium.defined(picked) && picked.id && picked.id.id) {
      const entityId = picked.id.id as string
      const building = mockBuildings.find((b) => b.id === entityId)
      if (building) {
        selectedBuilding.value = building
        selectedEvent.value = null
        return
      }
      const evt = getEventById(entityId)
      if (evt) {
        selectedEvent.value = evt
        selectedBuilding.value = null
        return
      }
    }
    selectedBuilding.value = null
    selectedEvent.value = null
  }, Cesium.ScreenSpaceEventType.LEFT_CLICK)

  // 阶段9：首次进入若携带 eventId（从事件中心跳转来），定位到该事件
  flyToEvent(route.query.eventId)
})

onBeforeUnmount(() => {
  clickHandler?.destroy()
  clickHandler = null
  viewer.value?.destroy()
  viewer.value = null
})

defineExpose({
  getViewer: () => viewer.value
})
</script>

<template>
  <div class="cesium-viewer-root" ref="containerRef">
    <!-- 阶段5：建筑信息浮层，点击建筑后显示 -->
    <div v-if="selectedBuilding" class="building-info">
      <div class="building-info__title">🏢 {{ selectedBuilding.name }}</div>
      <dl class="building-info__body">
        <div><dt>建筑编号</dt><dd>{{ selectedBuilding.id }}</dd></div>
        <div><dt>位置</dt><dd>{{ selectedBuilding.longitude.toFixed(4) }}, {{ selectedBuilding.latitude.toFixed(4) }}</dd></div>
        <div><dt>建筑高度</dt><dd>{{ selectedBuilding.height }} m</dd></div>
      </dl>
      <button class="building-info__close" @click="selectedBuilding = null">关闭</button>
    </div>
    <!-- 阶段8：事件详情浮层，点击事件后显示 -->
    <EventDetail
      v-if="selectedEvent"
      :event="selectedEvent"
      @close="selectedEvent = null"
    />
  </div>
</template>

<style scoped>
.cesium-viewer-root {
  width: 100%;
  height: 100%;
  position: relative;
  /* 覆盖 Cesium 默认的浅色工具条背景，融入深色主题 */
  :deep(.cesium-viewer-bottom) {
    display: none;
  }
}

/* 阶段5：建筑信息浮层，半透明深色卡片，数字孪生指挥中心风格 */
.building-info {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 220px;
  padding: 14px 16px;
  background: rgba(16, 22, 44, 0.88);
  border: 1px solid rgba(123, 179, 255, 0.35);
  border-radius: 8px;
  color: #e6edf7;
  font-size: 13px;
  backdrop-filter: blur(6px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
  z-index: 10;
}
.building-info__title {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 10px;
  color: #7fb3ff;
}
.building-info__body {
  margin: 0 0 10px;
  display: grid;
  gap: 6px;
}
.building-info__body > div {
  display: grid;
  grid-template-columns: 64px 1fr;
  gap: 8px;
  align-items: baseline;
}
.building-info__body dt {
  color: #8b97b3;
  margin: 0;
}
.building-info__body dd {
  margin: 0;
  color: #e6edf7;
}
.building-info__close {
  width: 100%;
  padding: 6px 0;
  background: transparent;
  border: 1px solid rgba(123, 179, 255, 0.4);
  border-radius: 4px;
  color: #7fb3ff;
  cursor: pointer;
  font-size: 12px;
}
.building-info__close:hover {
  background: rgba(123, 179, 255, 0.12);
}
</style>
