import * as Cesium from 'cesium'
import type { RoadCollection } from '@/types/building'
import type { ScenarioFrame, ScenarioRisk, ScenarioType, ScenarioZone } from '@/types/scenario'

const RISK_COLOR: Record<ScenarioRisk, Cesium.Color> = {
  unknown: Cesium.Color.fromCssColorString('#8aa3c4'),
  low: Cesium.Color.fromCssColorString('#4dd984'),
  medium: Cesium.Color.fromCssColorString('#f0c050'),
  high: Cesium.Color.fromCssColorString('#ff9040'),
  critical: Cesium.Color.fromCssColorString('#ff4d4f')
}
const WATER_BODY = Cesium.Color.fromCssColorString('#076a9c').withAlpha(0.62)
const WATER_EDGE = Cesium.Color.fromCssColorString('#74e8ff')
const PREVIOUS_EDGE = Cesium.Color.fromCssColorString('#b7efff').withAlpha(0.72)
const WATER_BASE_HEIGHT = 0.15
const WATER_DEPTH_VISUAL_SCALE = 1.8
const WATER_VERTEX_FORMAT = Cesium.MaterialAppearance.MaterialSupport.TEXTURED.vertexFormat

const WATER_SHADER = `
uniform vec4 waterColor;
uniform vec4 crestColor;

czm_material czm_getMaterial(czm_materialInput materialInput)
{
    czm_material material = czm_getDefaultMaterial(materialInput);
    vec2 uv = materialInput.st;
    float flow = czm_frameNumber * 0.018;
    float waveA = sin(uv.y * 88.0 + flow + sin(uv.x * 24.0) * 2.3);
    float waveB = sin(uv.x * 52.0 - flow * 1.35 + cos(uv.y * 31.0) * 1.7);
    float wave = waveA * 0.58 + waveB * 0.42;
    float crest = smoothstep(0.58, 0.98, wave);
    float body = smoothstep(-0.35, 0.18, wave);

    material.diffuse = mix(waterColor.rgb, crestColor.rgb, crest * 0.5);
    material.alpha = waterColor.a + crest * 0.13;
    material.specular = 0.72 + crest * body * 0.18;
    material.shininess = 38.0;
    return material;
}
`

export class ScenarioLayer {
  private zoneIds: string[] = []
  private roadIds: string[] = []
  private primitives: Cesium.Primitive[] = []
  private roads = new Map<string, [number, number][]>()

  constructor(private viewer: Cesium.Viewer) {}

  setRoads(collection: RoadCollection | null | undefined): void {
    this.roads.clear()
    for (const feature of collection?.features ?? []) {
      const geometry = feature.geometry as { type?: string; coordinates?: number[][] }
      if (geometry?.type === 'LineString' && Array.isArray(geometry.coordinates)) {
        this.roads.set(String(feature.properties?.id), geometry.coordinates as [number, number][])
      }
    }
  }

  render(frame: ScenarioFrame, scenarioType: ScenarioType, previousFrame?: ScenarioFrame): void {
    this.clear()
    for (const zone of frame.zones) {
      const color = RISK_COLOR[zone.risk_level]
      const isFlood = scenarioType === 'flood'
      const depthM = Math.max(0, Number(frame.metrics.water_depth_cm ?? 0) / 100)
      const waterTop = WATER_BASE_HEIGHT + Math.max(0.08, depthM * WATER_DEPTH_VISUAL_SCALE)
      const entity =
        zone.polygon && zone.polygon.length >= 3
          ? {
              polygon: {
                hierarchy: new Cesium.PolygonHierarchy(Cesium.Cartesian3.fromDegreesArray(zone.polygon.flat())),
                height: isFlood ? WATER_BASE_HEIGHT : 3,
                extrudedHeight: isFlood ? waterTop : undefined,
                material: isFlood ? WATER_BODY : color.withAlpha(0.18),
                outline: true,
                outlineColor: isFlood ? WATER_EDGE.withAlpha(0.95) : color.withAlpha(0.9)
              }
            }
          : {
              position: Cesium.Cartesian3.fromDegrees(zone.longitude, zone.latitude, 3),
              ellipse: {
                semiMajorAxis: zone.radius_m ?? 100,
                semiMinorAxis: zone.radius_m ?? 100,
                height: isFlood ? WATER_BASE_HEIGHT : 3,
                extrudedHeight: isFlood ? waterTop : undefined,
                material: isFlood ? WATER_BODY : color.withAlpha(0.18),
                outline: true,
                outlineColor: isFlood ? WATER_EDGE.withAlpha(0.95) : color.withAlpha(0.9)
              }
            }
      this.zoneIds.push(this.viewer.entities.add(entity).id)
      if (isFlood) {
        this.addWaterSurface(zone, waterTop)
        this.addWaterAnnotations(zone, Number(frame.metrics.water_depth_cm ?? 0), waterTop)
      }
    }
    if (scenarioType === 'flood') this.addPreviousExtent(previousFrame)
    for (const id of frame.affected_road_ids) {
      const line = this.roads.get(id)
      if (!line) continue
      this.roadIds.push(
        this.viewer.entities.add({
          polyline: {
            positions: Cesium.Cartesian3.fromDegreesArrayHeights(line.flatMap(([lon, lat]) => [lon, lat, 4])),
            width: 8,
            material: Cesium.Color.fromCssColorString('#ff9040').withAlpha(0.9)
          }
        }).id
      )
    }
    this.viewer.dataSourceDisplay.update(this.viewer.clock.currentTime)
    if (!this.viewer.useDefaultRenderLoop) this.viewer.scene.render()
    this.viewer.scene.requestRender()
  }

  private addWaterSurface(zone: ScenarioZone, waterTop: number): void {
    const positions = this.zonePositions(zone, waterTop + 0.04)
    const geometry = Cesium.PolygonGeometry.fromPositions({
      positions,
      perPositionHeight: true,
      vertexFormat: WATER_VERTEX_FORMAT
    })
    const material = new Cesium.Material({
      fabric: {
        type: 'CityEyeFloodWater',
        uniforms: {
          waterColor: Cesium.Color.fromCssColorString('#075f91').withAlpha(0.56),
          crestColor: Cesium.Color.fromCssColorString('#a9f3ff').withAlpha(0.94)
        },
        source: WATER_SHADER
      }
    })
    const primitive = new Cesium.Primitive({
      geometryInstances: new Cesium.GeometryInstance({ geometry }),
      appearance: new Cesium.MaterialAppearance({
        material,
        translucent: true,
        flat: true,
        faceForward: true
      }),
      asynchronous: false,
      allowPicking: false
    })
    this.primitives.push(this.viewer.scene.primitives.add(primitive))
    this.addShoreline(zone, null, null, waterTop + 0.08)
  }

  private addWaterAnnotations(zone: ScenarioZone, depthCm: number, waterTop: number): void {
    this.zoneIds.push(
      this.viewer.entities.add({
        position: Cesium.Cartesian3.fromDegrees(zone.longitude, zone.latitude, waterTop + 1.1),
        label: {
          text: `模拟积水 ${depthCm.toFixed(1)} cm`,
          font: '600 14px sans-serif',
          fillColor: Cesium.Color.WHITE,
          showBackground: true,
          backgroundColor: WATER_BODY.withAlpha(0.9),
          backgroundPadding: new Cesium.Cartesian2(8, 5),
          pixelOffset: new Cesium.Cartesian2(0, -18),
          disableDepthTestDistance: Number.POSITIVE_INFINITY
        }
      }).id
    )
  }

  private addPreviousExtent(previousFrame?: ScenarioFrame): void {
    for (const zone of previousFrame?.zones ?? []) {
      this.addShoreline(zone, PREVIOUS_EDGE, 11, WATER_BASE_HEIGHT + 0.16)
    }
  }

  private addShoreline(zone: ScenarioZone, color: Cesium.Color | null, width: number | null, height: number): void {
    const positions = this.zonePositions(zone, height)
    if (positions.length < 3) return
    const closed = [...positions, positions[0]]
    if (color && width) {
      this.zoneIds.push(
        this.viewer.entities.add({
          polyline: {
            positions: closed,
            width,
            material: new Cesium.PolylineDashMaterialProperty({
              color,
              dashLength: 14,
              dashPattern: 255
            })
          }
        }).id
      )
    }
    this.zoneIds.push(
      this.viewer.entities.add({
        polyline: {
          positions: closed,
          width: color ? 2 : 4,
          material: color
            ? color.withAlpha(0.95)
            : new Cesium.PolylineGlowMaterialProperty({
                color: WATER_EDGE.withAlpha(0.9),
                glowPower: 0.24,
                taperPower: 1
              })
        }
      }).id
    )
  }

  private zonePositions(zone: ScenarioZone, height: number): Cesium.Cartesian3[] {
    if (zone.polygon && zone.polygon.length >= 3) {
      return Cesium.Cartesian3.fromDegreesArrayHeights(
        zone.polygon.flatMap(([longitude, latitude]) => [longitude, latitude, height])
      )
    }
    const radius = Math.max(20, zone.radius_m ?? 100)
    const lonScale = 111320 * Math.cos(Cesium.Math.toRadians(zone.latitude))
    const positions: Cesium.Cartesian3[] = []
    for (let i = 0; i < 64; i += 1) {
      const angle = (Math.PI * 2 * i) / 64
      positions.push(
        Cesium.Cartesian3.fromDegrees(
          zone.longitude + (Math.cos(angle) * radius) / lonScale,
          zone.latitude + (Math.sin(angle) * radius) / 110540,
          height
        )
      )
    }
    return positions
  }

  focus(frame: ScenarioFrame): boolean {
    const zone = frame.zones[0]
    if (!zone) return false
    let centerLon = zone.longitude
    let centerLat = zone.latitude
    let radius = zone.radius_m ?? 200
    if (zone.polygon?.length) {
      centerLon = zone.polygon.reduce((sum, point) => sum + point[0], 0) / zone.polygon.length
      centerLat = zone.polygon.reduce((sum, point) => sum + point[1], 0) / zone.polygon.length
      radius = Math.max(
        radius,
        ...zone.polygon.map(([lon, lat]) =>
          Math.hypot(
            (lon - centerLon) * 111320 * Math.cos(Cesium.Math.toRadians(centerLat)),
            (lat - centerLat) * 110540
          )
        )
      )
    }
    const sphere = new Cesium.BoundingSphere(
      Cesium.Cartesian3.fromDegrees(centerLon, centerLat, 0),
      Math.max(150, radius)
    )
    this.viewer.camera.flyToBoundingSphere(sphere, {
      offset: new Cesium.HeadingPitchRange(0, Cesium.Math.toRadians(-42), Math.max(700, radius * 3.2)),
      duration: 1.5
    })
    return true
  }

  clear(): void {
    for (const id of [...this.zoneIds, ...this.roadIds]) this.viewer.entities.removeById(id)
    for (const primitive of this.primitives) this.viewer.scene.primitives.remove(primitive)
    this.zoneIds = []
    this.roadIds = []
    this.primitives = []
  }

  destroy(): void {
    this.clear()
    this.roads.clear()
  }
}
