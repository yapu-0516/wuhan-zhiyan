// 城市三维对象接口层 —— docs/api.md §3
import { request, loadSnapshot } from './http'
import type {
  BuildingCollection,
  BuildingDetail,
  BuildingDistrictManifest,
  Poi,
  RoadCollection
} from '@/types/building'

const districtAssetBase = `${import.meta.env.BASE_URL.replace(/\/?$/, '/')}buildings/districts`
let districtManifestAsset: Promise<BuildingDistrictManifest> | null = null

function loadDistrictManifest(): Promise<BuildingDistrictManifest> {
  districtManifestAsset ??= fetch(`${districtAssetBase}/manifest.json`).then((response) => {
    if (!response.ok) throw new Error('精细建筑分区清单不存在')
    return response.json() as Promise<BuildingDistrictManifest>
  })
  return districtManifestAsset
}

/** 建筑轮廓 GeoJSON GET /api/buildings */
export function getBuildings(): Promise<BuildingCollection> {
  return request('/buildings', undefined, () => loadSnapshot<BuildingCollection>('buildings.geojson'))
}

/** 可加载的精细建筑分区 GET /api/buildings/fine/districts */
export function getBuildingDistricts(): Promise<BuildingDistrictManifest> {
  return request('/buildings/fine/districts', undefined, loadDistrictManifest)
}

/** 武汉分区精细建筑轮廓 GET /api/buildings/fine?district=武昌区 */
export function getFineBuildings(district?: string): Promise<BuildingCollection> {
  const query = district ? `?district=${encodeURIComponent(district)}` : ''
  return request(`/buildings/fine${query}`, undefined, async () => {
    const manifest = await loadDistrictManifest()
    const item = manifest.districts.find((entry) => entry.name === district)
    if (!item) return { type: 'FeatureCollection', features: [] }
    const response = await fetch(`${districtAssetBase}/${item.prefix}.geojson`)
    if (!response.ok) throw new Error(`${district}精细建筑不存在`)
    return response.json() as Promise<BuildingCollection>
  })
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
