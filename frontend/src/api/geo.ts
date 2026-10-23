// 城市三维对象接口层 —— docs/api.md §3
import { request, loadSnapshot } from './http'
import type { BuildingCollection, BuildingDetail, Poi, RoadCollection } from '@/types/building'

/** 建筑轮廓 GeoJSON GET /api/buildings */
export function getBuildings(): Promise<BuildingCollection> {
  return request('/buildings', undefined, () => loadSnapshot<BuildingCollection>('buildings.geojson'))
}

/** 建筑详情（含沉降监测）GET /api/buildings/{id} */
export function getBuilding(id: string): Promise<BuildingDetail> {
  return request(`/buildings/${encodeURIComponent(id)}`, undefined, async () => {
    const details = await loadSnapshot<Record<string, BuildingDetail>>('building_details.json').catch(
      () => ({}) as Record<string, BuildingDetail>
    )
    if (details[id]) return details[id]
    const fc = await loadSnapshot<BuildingCollection>('buildings.geojson')
    const f = fc.features.find((x) => x.properties.id === id)
    if (!f) throw new Error('建筑不存在')
    return { properties: f.properties, monitoring: null, events: [] }
  })
}

/** 主干路网 + 实时路况 GET /api/roads */
export function getRoads(): Promise<RoadCollection> {
  return request('/roads', undefined, () => loadSnapshot<RoadCollection>('roads.geojson'))
}

/** 应急资源点位 GET /api/pois */
export function getPois(): Promise<Poi[]> {
  return request('/pois', undefined, () => loadSnapshot<Poi[]>('pois.json'))
}
