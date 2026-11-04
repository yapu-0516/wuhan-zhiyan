import * as Cesium from 'cesium'
import * as THREE from 'three'
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js'
import type { RoadCollection } from '@/types/building'
import type { EventType } from '@/types/event'
import {
  PERSON_META,
  type CrowdBenchmarkRow,
  type CrowdRegion,
  type CrowdStats,
  type PersonState,
  type PersonType,
  type PersonView,
  type SpawnType,
  type VehicleStats
} from './types'
import {
  dampHeading,
  densitySpeedFactor,
  sampleReactionDelay,
  sampleWalkSpeed,
  serviceExitQueue,
  trafficSpeedFactor
} from './motion'
import { RoadGraph } from './roadGraph'
import { hazardRadiusAt } from './hazard'

interface CrowdPerson {
  id: string
  type: PersonType
  lon: number
  lat: number
  x: number
  z: number
  scale: number
  heading: number
  state: PersonState
  speed: number
  gaitBlend: number
  reactionDelay: number
  reactionRemaining: number
  phase: number
  path: THREE.Vector2[]
  pathIndex: number
  exitNodeId: number | null
}

interface RoadPath {
  points: THREE.Vector2[]
  cumulative: number[]
}

interface HazardState {
  type: EventType
  baseRadiusM: number
  elapsedSec: number
  replans: number
  lastReplanSec: number
}

interface VehicleAgent {
  id: string
  pathIndex: number
  distance: number
  direction: 1 | -1
  speed: number
  currentSpeed: number
  detourPath: THREE.Vector2[] | null
  detourIndex: number
  detourPosition: THREE.Vector2 | null
}

const MAX_PEOPLE = 6000
const MAX_VEHICLES = 1200
const PERSON_SPACING_M = 0.46
const DENSITY_RADIUS_M = 1.35
const MAX_SEPARATION_SPEED_MPS = 0.55
const PROVISIONAL_EXIT_SERVICE_PER_SEC = 1.6
const DEMO_EXIT_LIMIT = 4
const EXIT_LABELS = ['A', 'B', 'C', 'D']
const EXIT_CAPACITIES = [2.2, 1.8, 1.5, 1.2]
const TYPE_ORDER: PersonType[] = ['resident', 'tourist', 'firefighter', 'rescuer']
const VEHICLE_COLORS = ['#eef1f3', '#c1c8cd', '#8d9aa3', '#e0bd64', '#86a9ba', '#c77b73']

function tagPart(geometry: THREE.BufferGeometry, limbKind: number, tone: number): THREE.BufferGeometry {
  const count = geometry.getAttribute('position').count
  geometry.setAttribute('aLimbKind', new THREE.BufferAttribute(new Float32Array(count).fill(limbKind), 1))
  geometry.setAttribute('color', new THREE.BufferAttribute(new Float32Array(count * 3).fill(tone), 3))
  return geometry
}

function makeStickFigureGeometry(): THREE.BufferGeometry {
  const parts: THREE.BufferGeometry[] = []
  const add = (geometry: THREE.BufferGeometry, x = 0, y = 0, z = 0) => {
    geometry.translate(x, y, z)
    parts.push(geometry)
  }
  const makeArm = (x: number, outward: number, limbKind: number) => {
    const arm = new THREE.CapsuleGeometry(0.042, 0.34, 3, 5)
    arm.translate(0, -0.24, 0)
    arm.rotateZ(outward * 0.3)
    arm.translate(x, 1.52, 0)
    add(tagPart(arm, limbKind, 0.72))
  }
  const makeLeg = (x: number, limbKind: number) => {
    const leg = new THREE.CapsuleGeometry(0.055, 0.43, 3, 5)
    leg.translate(0, -0.31, 0)
    const shoe = new THREE.BoxGeometry(0.12, 0.08, 0.23)
    shoe.translate(0, -0.59, 0.045)
    const mergedLeg = mergeGeometries([leg, shoe], false)
    leg.dispose()
    shoe.dispose()
    if (!mergedLeg) throw new Error('腿部几何体合并失败')
    add(tagPart(mergedLeg, limbKind, 0.56), x, 1.04)
  }

  add(tagPart(new THREE.SphereGeometry(0.13, 6, 4), 0, 0.18), 0, 1.7)
  add(tagPart(new THREE.CapsuleGeometry(0.13, 0.3, 3, 6), 0, 1), 0, 1.3)
  makeArm(-0.18, -1, 1)
  makeArm(0.18, 1, 2)
  makeLeg(-0.075, 3)
  makeLeg(0.075, 4)

  const merged = mergeGeometries(parts, false)
  parts.forEach((part) => part.dispose())
  if (!merged) throw new Error('火柴人几何体合并失败')
  merged.computeBoundingSphere()
  return merged
}

const GAIT_VERTEX_DECLARATIONS = `
attribute float aLimbKind;
attribute float aGaitPhase;
attribute float aGaitStrength;

float gaitLimbAngle(float limbKind, float swing) {
  if (limbKind > 3.5) return -swing * 0.36;
  if (limbKind > 2.5) return swing * 0.36;
  if (limbKind > 1.5) return swing * 0.28;
  if (limbKind > 0.5) return -swing * 0.28;
  return 0.0;
}
`

function installGaitShader(material: THREE.MeshLambertMaterial): void {
  material.onBeforeCompile = (shader) => {
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', `#include <common>\n${GAIT_VERTEX_DECLARATIONS}`)
      .replace(
        '#include <beginnormal_vertex>',
        `#include <beginnormal_vertex>
float gaitSwing = sin(aGaitPhase) * aGaitStrength;
float gaitAngle = gaitLimbAngle(aLimbKind, gaitSwing);
if (aLimbKind > 0.5) {
  float gaitNormalCos = cos(gaitAngle);
  float gaitNormalSin = sin(gaitAngle);
  objectNormal = vec3(
    objectNormal.x,
    objectNormal.y * gaitNormalCos - objectNormal.z * gaitNormalSin,
    objectNormal.y * gaitNormalSin + objectNormal.z * gaitNormalCos
  );
}`
      )
      .replace(
        '#include <begin_vertex>',
        `#include <begin_vertex>
if (aLimbKind > 0.5) {
  float gaitPivotY = aLimbKind > 2.5 ? 1.04 : 1.52;
  float gaitPivotX = aLimbKind > 3.5 ? 0.075 : aLimbKind > 2.5 ? -0.075 : aLimbKind > 1.5 ? 0.18 : -0.18;
  vec3 gaitPivot = vec3(gaitPivotX, gaitPivotY, 0.0);
  vec3 gaitOffset = transformed - gaitPivot;
  float gaitCos = cos(gaitAngle);
  float gaitSin = sin(gaitAngle);
  transformed = gaitPivot + vec3(
    gaitOffset.x,
    gaitOffset.y * gaitCos - gaitOffset.z * gaitSin,
    gaitOffset.y * gaitSin + gaitOffset.z * gaitCos
  );
}
transformed.x += sin(aGaitPhase) * aGaitStrength * 0.014;`
      )
  }
  material.customProgramCacheKey = () => 'cityeye-gait-v1'
}

function makeVehicleGeometry(): THREE.BufferGeometry {
  const body = new THREE.BoxGeometry(1.9, 0.58, 4.1)
  body.translate(0, 0.62, 0)
  const cabin = new THREE.BoxGeometry(1.55, 0.58, 1.9)
  cabin.translate(0, 1.18, -0.2)
  const merged = mergeGeometries([body, cabin], false)
  body.dispose()
  cabin.dispose()
  if (!merged) throw new Error('车辆几何体合并失败')
  merged.computeBoundingSphere()
  return merged
}

export class CrowdLayer {
  private readonly threeScene = new THREE.Scene()
  private readonly camera = new THREE.PerspectiveCamera(50, 1, 0.5, 120000)
  private readonly renderer: THREE.WebGLRenderer
  private readonly meshes: Record<PersonType, THREE.InstancedMesh>
  private readonly gaitPhases: Record<PersonType, THREE.InstancedBufferAttribute>
  private readonly gaitStrengths: Record<PersonType, THREE.InstancedBufferAttribute>
  private readonly vehicleMesh: THREE.InstancedMesh
  private readonly members: Record<PersonType, CrowdPerson[]> = {
    resident: [],
    tourist: [],
    firefighter: [],
    rescuer: []
  }
  private readonly people = new Map<string, CrowdPerson>()
  private readonly vehicles: VehicleAgent[] = []
  private readonly markerGroup = new THREE.Group()
  private readonly removePostRender: () => void
  private readonly resizeObserver: ResizeObserver
  private readonly origin: Cesium.Cartesian3
  private readonly fixedToEnu: Cesium.Matrix4
  private enuToFixed: Cesium.Matrix4
  private region: CrowdRegion
  private roadPaths: RoadPath[] = []
  private readonly roadGraph = new RoadGraph()
  private readonly exitQueues = new Map<number, string[]>()
  private readonly exitRelease = new Map<number, number>()
  private readonly exitLabels = new Map<number, string>()
  private hazard: HazardState | null = null
  private vehicleIncident: { x: number; z: number; radius: number } | null = null
  private evacuationCenter: { x: number; z: number; radius: number } | null = null
  private simulationSpeed = 1
  private evacuationElapsedSec = 0
  private evacuationComplete = false
  private peakWaiting = 0
  private peakWaitingExitLabel = ''
  private evacuationIds = new Set<string>()
  private lastFrame = performance.now()
  private idSeq = 0
  private disposed = false
  private sampleFrames = 0
  private sampleMs = 0

  constructor(
    private readonly host: HTMLElement,
    private readonly scene: Cesium.Scene,
    region: CrowdRegion
  ) {
    this.region = region
    this.origin = Cesium.Cartesian3.fromDegrees(region.center[0], region.center[1], 0)
    this.enuToFixed = Cesium.Transforms.eastNorthUpToFixedFrame(this.origin)
    this.fixedToEnu = Cesium.Matrix4.inverse(this.enuToFixed, new Cesium.Matrix4())

    this.renderer = new THREE.WebGLRenderer({ alpha: true, antialias: false, powerPreference: 'high-performance' })
    this.renderer.setClearColor(0x000000, 0)
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5))
    this.renderer.domElement.className = 'crowd-three-canvas'
    this.host.appendChild(this.renderer.domElement)

    const geometry = makeStickFigureGeometry()
    const gaitPhases = {} as Record<PersonType, THREE.InstancedBufferAttribute>
    const gaitStrengths = {} as Record<PersonType, THREE.InstancedBufferAttribute>
    const makeMesh = (type: PersonType) => {
      const material = new THREE.MeshLambertMaterial({ color: PERSON_META[type].color, vertexColors: true })
      installGaitShader(material)
      const typeGeometry = geometry.clone()
      const phases = new THREE.InstancedBufferAttribute(new Float32Array(MAX_PEOPLE), 1)
      const strengths = new THREE.InstancedBufferAttribute(new Float32Array(MAX_PEOPLE), 1)
      phases.setUsage(THREE.DynamicDrawUsage)
      strengths.setUsage(THREE.DynamicDrawUsage)
      typeGeometry.setAttribute('aGaitPhase', phases)
      typeGeometry.setAttribute('aGaitStrength', strengths)
      gaitPhases[type] = phases
      gaitStrengths[type] = strengths
      const mesh = new THREE.InstancedMesh(typeGeometry, material, MAX_PEOPLE)
      mesh.count = 0
      mesh.frustumCulled = false
      mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage)
      this.threeScene.add(mesh)
      return mesh
    }
    this.meshes = {
      resident: makeMesh('resident'),
      tourist: makeMesh('tourist'),
      firefighter: makeMesh('firefighter'),
      rescuer: makeMesh('rescuer')
    }
    geometry.dispose()
    this.gaitPhases = gaitPhases
    this.gaitStrengths = gaitStrengths
    const vehicleGeometry = makeVehicleGeometry()
    this.vehicleMesh = new THREE.InstancedMesh(
      vehicleGeometry,
      new THREE.MeshBasicMaterial({ color: 0xffffff }),
      MAX_VEHICLES
    )
    this.vehicleMesh.count = 0
    this.vehicleMesh.frustumCulled = false
    this.vehicleMesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage)
    this.threeScene.add(this.vehicleMesh)

    this.threeScene.add(new THREE.AmbientLight(0xffffff, 1.8))
    const sun = new THREE.DirectionalLight(0xffffff, 2.2)
    sun.position.set(0.4, 1, 0.25)
    this.threeScene.add(sun, this.markerGroup)

    this.resizeObserver = new ResizeObserver(() => this.resize())
    this.resizeObserver.observe(this.host)
    this.resize()
    this.removePostRender = scene.postRender.addEventListener(() => this.render())
  }

  setRegion(region: CrowdRegion): void {
    this.region = region
  }

  setSimulationSpeed(speed: number): void {
    this.simulationSpeed = Math.max(0.5, Math.min(8, speed))
  }

  setHazardScenario(type: EventType, baseRadiusM: number): void {
    this.hazard = {
      type,
      baseRadiusM,
      elapsedSec: 0,
      replans: 0,
      lastReplanSec: 0
    }
  }

  clearHazardScenario(): void {
    this.hazard = null
  }

  private currentHazardRadius(): number {
    if (!this.hazard) return this.evacuationCenter?.radius ?? 0
    return hazardRadiusAt(this.hazard.type, this.hazard.baseRadiusM, this.hazard.elapsedSec)
  }

  private exitLabel(exitNodeId: number): string {
    const existing = this.exitLabels.get(exitNodeId)
    if (existing) return existing
    const label = EXIT_LABELS[this.exitLabels.size] ?? `${this.exitLabels.size + 1}`
    this.exitLabels.set(exitNodeId, label)
    return label
  }

  private exitCapacity(exitNodeId: number): number {
    const labelIndex = EXIT_LABELS.indexOf(this.exitLabel(exitNodeId))
    return EXIT_CAPACITIES[Math.max(0, labelIndex)] ?? PROVISIONAL_EXIT_SERVICE_PER_SEC
  }

  private exitDirectionLabel(exitNodeId: number | null): string {
    if (exitNodeId === null || !this.evacuationCenter) return ''
    const point = this.roadGraph.pointForNode(exitNodeId)
    if (!point) return ''
    const angle = Math.atan2(point.z - this.evacuationCenter.z, point.x - this.evacuationCenter.x)
    const directions = [
      '东侧出口',
      '东北侧出口',
      '北侧出口',
      '西北侧出口',
      '西侧出口',
      '西南侧出口',
      '南侧出口',
      '东南侧出口'
    ]
    const index = Math.round(((angle + Math.PI * 2) % (Math.PI * 2)) / (Math.PI / 4)) % 8
    return directions[index]
  }

  setRoads(collection: RoadCollection | null | undefined): void {
    this.roadPaths = (collection?.features ?? []).flatMap((feature) => {
      const geometry = feature.geometry as { type?: string; coordinates?: unknown }
      if (!Array.isArray(geometry?.coordinates)) return []
      const lines =
        geometry.type === 'LineString'
          ? [geometry.coordinates]
          : geometry.type === 'MultiLineString'
            ? geometry.coordinates
            : []
      return (lines as [number, number][][]).map((line) => {
        const points = line.map(([lon, lat]) => {
          const point = this.lonLatToLocal(lon, lat, 0)
          return new THREE.Vector2(point.x, point.z)
        })
        const cumulative = [0]
        for (let i = 1; i < points.length; i++) {
          cumulative.push(cumulative[i - 1] + points[i].distanceTo(points[i - 1]))
        }
        return { points, cumulative }
      })
    })
    this.roadGraph.build(
      this.roadPaths.map((road, index) => ({
        id: `path-${index}`,
        points: road.points.map((point) => ({ x: point.x, z: point.y }))
      }))
    )
  }

  private lonLatToLocal(lon: number, lat: number, height: number): THREE.Vector3 {
    const fixed = Cesium.Cartesian3.fromDegrees(lon, lat, height)
    const local = Cesium.Matrix4.multiplyByPoint(this.fixedToEnu, fixed, new Cesium.Cartesian3())
    return new THREE.Vector3(local.x, local.z, -local.y)
  }

  private localToLonLat(x: number, z: number, height = 0): [number, number] {
    const fixed = Cesium.Matrix4.multiplyByPoint(
      this.enuToFixed,
      new Cesium.Cartesian3(x, -z, height),
      new Cesium.Cartesian3()
    )
    const carto = Cesium.Cartographic.fromCartesian(fixed)
    return [Cesium.Math.toDegrees(carto.longitude), Cesium.Math.toDegrees(carto.latitude)]
  }

  private resize(): void {
    const width = Math.max(1, this.host.clientWidth)
    const height = Math.max(1, this.host.clientHeight)
    this.renderer.setSize(width, height, false)
    this.camera.aspect = width / height
    this.camera.updateProjectionMatrix()
  }

  private syncCamera(): void {
    const cesiumCamera = this.scene.camera
    const position = Cesium.Matrix4.multiplyByPoint(
      this.fixedToEnu,
      cesiumCamera.positionWC,
      new Cesium.Cartesian3()
    )
    const direction = Cesium.Matrix4.multiplyByPointAsVector(
      this.fixedToEnu,
      cesiumCamera.directionWC,
      new Cesium.Cartesian3()
    )
    const up = Cesium.Matrix4.multiplyByPointAsVector(
      this.fixedToEnu,
      cesiumCamera.upWC,
      new Cesium.Cartesian3()
    )
    this.camera.position.set(position.x, position.z, -position.y)
    this.camera.up.set(up.x, up.z, -up.y).normalize()
    const target = new THREE.Vector3(
      position.x + direction.x,
      position.z + direction.z,
      -(position.y + direction.y)
    )
    this.camera.lookAt(target)
    const frustum = cesiumCamera.frustum as Cesium.PerspectiveFrustum
    if (typeof frustum.fovy === 'number' && Number.isFinite(frustum.fovy)) {
      const fov = Cesium.Math.toDegrees(frustum.fovy)
      if (Math.abs(this.camera.fov - fov) > 0.01) {
        this.camera.fov = fov
        this.camera.updateProjectionMatrix()
      }
    }
  }

  private render(): void {
    if (this.disposed) return
    const started = performance.now()
    const realDt = Math.min(0.1, (started - this.lastFrame) / 1000)
    const dt = Math.min(0.25, realDt * this.simulationSpeed)
    this.lastFrame = started
    if (!this.people.size && !this.vehicles.length) {
      this.host.style.visibility = 'hidden'
      return
    }
    this.host.style.visibility = 'visible'
    this.advance(dt)
    this.advanceVehicles(dt)
    this.syncCamera()
    this.renderer.render(this.threeScene, this.camera)
    this.sampleFrames++
    this.sampleMs += performance.now() - started
  }

  private advance(dt: number): void {
    this.advanceHazard(dt)
    this.releaseExitQueues(dt)
    this.updateEvacuationMetrics(dt)
    const neighborCounts = this.buildNeighborCounts()
    for (const person of this.people.values()) {
      if (person.state === 'reacting') {
        person.reactionRemaining = Math.max(0, person.reactionRemaining - dt)
        if (person.reactionRemaining > 0) continue
        person.state = 'evacuating'
      }
      if (person.state === 'waiting') continue
      let moving = false
      const target = person.path[person.pathIndex]
      if (target) {
        const dx = target.x - person.x
        const dz = target.y - person.z
        const distance = Math.hypot(dx, dz)
        if (distance < 0.8) {
          person.pathIndex++
          if (person.pathIndex >= person.path.length) {
            if (person.state === 'evacuating' && person.exitNodeId !== null) {
              person.state = 'waiting'
              const queue = this.exitQueues.get(person.exitNodeId)
              if (queue) queue.push(person.id)
              else this.exitQueues.set(person.exitNodeId, [person.id])
            } else {
              person.state = person.state === 'evacuating' ? 'arrived' : 'idle'
            }
          }
        } else {
          const speedFactor = densitySpeedFactor(neighborCounts.get(person.id) ?? 0)
          const step = Math.min(distance, person.speed * speedFactor * dt)
          person.x += (dx / distance) * step
          person.z += (dz / distance) * step
          person.heading = dampHeading(person.heading, Math.atan2(dx, dz), 7, dt)
          person.phase += dt * (5 + person.speed) * (0.65 + speedFactor * 0.35)
          moving = true
        }
      }
      const targetGait = moving ? 1 : 0
      person.gaitBlend += (targetGait - person.gaitBlend) * Math.min(1, dt * 10)
      if (!moving && person.state === 'evacuating' && person.pathIndex >= person.path.length) {
        person.state = 'arrived'
      }
    }
    this.separateNearbyPeople(dt)
    this.syncInstances()
  }

  private updateEvacuationMetrics(dt: number): void {
    if (!this.evacuationIds.size || this.evacuationComplete) return
    this.evacuationElapsedSec += dt
    let waiting = 0
    let largestQueue = 0
    let largestExit: number | null = null
    for (const [exitNodeId, queue] of this.exitQueues) {
      waiting += queue.length
      if (queue.length > largestQueue) {
        largestQueue = queue.length
        largestExit = exitNodeId
      }
    }
    if (waiting > this.peakWaiting) {
      this.peakWaiting = waiting
      this.peakWaitingExitLabel = this.exitDirectionLabel(largestExit)
    }
    let safe = 0
    for (const id of this.evacuationIds) {
      if (this.people.get(id)?.state === 'arrived') safe++
    }
    this.evacuationComplete = safe === this.evacuationIds.size
  }

  private advanceHazard(dt: number): void {
    if (!this.hazard) return
    this.hazard.elapsedSec += dt
    const radius = this.currentHazardRadius()
    if (this.vehicleIncident) this.vehicleIncident.radius = radius
    if (this.evacuationCenter) this.evacuationCenter.radius = radius
    if (!this.evacuationIds.size || this.hazard.elapsedSec - this.hazard.lastReplanSec < 4) return
    this.hazard.lastReplanSec = this.hazard.elapsedSec
    this.replanActiveEvacuation()
  }

  private replanActiveEvacuation(): void {
    const center = this.evacuationCenter
    if (!center || !this.hazard) return
    const radius = this.currentHazardRadius()
    const navigate = this.roadGraph.prepareEvacuation({ x: center.x, z: center.z }, radius, DEMO_EXIT_LIMIT)
    const routesByExit = new Map<number, THREE.Vector2[]>()
    let evaluated = false
    for (const id of this.evacuationIds) {
      const person = this.people.get(id)
      if (!person || (person.state !== 'reacting' && person.state !== 'evacuating')) continue
      const planned = navigate({ x: person.x, z: person.z })
      const route = planned
        ? planned.points.map((point) => new THREE.Vector2(point.x, point.z))
        : this.fallbackEscapeRoute(person.x, person.z, center.x, center.z, radius)
      if (!route.length) continue
      const nextExit = planned?.exitNodeId ?? null
      person.path = route
      person.pathIndex = 0
      person.exitNodeId = nextExit
      if (nextExit !== null && !routesByExit.has(nextExit)) {
        this.exitLabel(nextExit)
        routesByExit.set(nextExit, route)
      }
      evaluated = true
    }
    for (const person of this.people.values()) {
      if (this.evacuationIds.has(person.id)) continue
      if (Math.hypot(person.x - center.x, person.z - center.z) > radius) continue
      const planned = navigate({ x: person.x, z: person.z })
      const route = planned
        ? planned.points.map((point) => new THREE.Vector2(point.x, point.z))
        : this.fallbackEscapeRoute(person.x, person.z, center.x, center.z, radius)
      person.path = route
      person.pathIndex = 0
      person.exitNodeId = planned?.exitNodeId ?? null
      person.state = 'reacting'
      person.reactionRemaining = person.reactionDelay
      this.evacuationIds.add(person.id)
      this.evacuationComplete = false
      if (person.exitNodeId !== null && !routesByExit.has(person.exitNodeId)) {
        this.exitLabel(person.exitNodeId)
        routesByExit.set(person.exitNodeId, route)
      }
      evaluated = true
    }
    if (evaluated) this.hazard.replans++
    this.refreshEvacuationMarkers(center, radius, routesByExit)
  }

  private refreshEvacuationMarkers(
    center: { x: number; z: number },
    radius: number,
    routesByExit: Map<number, THREE.Vector2[]>
  ): void {
    this.clearMarkers()
    this.markerGroup.add(this.makeRing(center.x, center.z, radius, '#ff4d4f', 0.32))
    for (const points of this.roadGraph.segmentsWithin(center, radius, 80)) {
      const linePoints = points.map((point) => new THREE.Vector2(point.x, point.z))
      this.markerGroup.add(this.makeLine(linePoints, '#d9a45d', 0.22))
    }
    for (const points of this.roadGraph.segmentsWithin(center, radius * 0.45, 50)) {
      const linePoints = points.map((point) => new THREE.Vector2(point.x, point.z))
      this.markerGroup.add(this.makeLine(linePoints, '#ff5b5b', 0.78))
    }
    for (const route of Array.from(routesByExit.values()).slice(0, DEMO_EXIT_LIMIT)) {
      this.markerGroup.add(this.makeLine(route, '#5ddcff', 0.66))
      const exit = route[route.length - 1]
      this.markerGroup.add(this.makeRing(exit.x, exit.y, 8, '#4dd984', 0.7))
    }
  }

  private releaseExitQueues(dt: number): void {
    for (const [exitNodeId, queue] of this.exitQueues) {
      if (!queue.length) {
        this.exitRelease.set(exitNodeId, 0)
        continue
      }
      const service = serviceExitQueue(
        queue.length,
        this.exitRelease.get(exitNodeId) ?? 0,
        this.exitCapacity(exitNodeId),
        dt
      )
      for (let index = 0; index < service.released; index++) {
        const id = queue.shift()!
        const person = this.people.get(id)
        if (person?.state === 'waiting') person.state = 'arrived'
      }
      this.exitRelease.set(exitNodeId, service.credit)
    }
  }

  private buildNeighborCounts(): Map<string, number> {
    const cells = new Map<string, CrowdPerson[]>()
    for (const person of this.people.values()) {
      const key = `${Math.floor(person.x / DENSITY_RADIUS_M)}:${Math.floor(person.z / DENSITY_RADIUS_M)}`
      const list = cells.get(key)
      if (list) list.push(person)
      else cells.set(key, [person])
    }
    const counts = new Map<string, number>()
    for (const person of this.people.values()) {
      const cx = Math.floor(person.x / DENSITY_RADIUS_M)
      const cz = Math.floor(person.z / DENSITY_RADIUS_M)
      let count = 0
      for (let dx = -1; dx <= 1; dx++) {
        for (let dz = -1; dz <= 1; dz++) {
          for (const other of cells.get(`${cx + dx}:${cz + dz}`) ?? []) {
            if (other.id !== person.id && Math.hypot(other.x - person.x, other.z - person.z) <= DENSITY_RADIUS_M) {
              count++
            }
          }
        }
      }
      counts.set(person.id, count)
    }
    return counts
  }

  private separateNearbyPeople(dt: number): void {
    const cells = new Map<string, CrowdPerson[]>()
    for (const person of this.people.values()) {
      const key = `${Math.floor(person.x / PERSON_SPACING_M)}:${Math.floor(person.z / PERSON_SPACING_M)}`
      const list = cells.get(key)
      if (list) list.push(person)
      else cells.set(key, [person])
    }
    for (const person of this.people.values()) {
      const cx = Math.floor(person.x / PERSON_SPACING_M)
      const cz = Math.floor(person.z / PERSON_SPACING_M)
      let pushX = 0
      let pushZ = 0
      for (let dx = -1; dx <= 1; dx++) {
        for (let dz = -1; dz <= 1; dz++) {
          for (const other of cells.get(`${cx + dx}:${cz + dz}`) ?? []) {
            if (other.id <= person.id) continue
            const vx = person.x - other.x
            const vz = person.z - other.z
            const distance = Math.hypot(vx, vz)
            if (distance >= PERSON_SPACING_M) continue
            const angle = distance > 1e-4 ? Math.atan2(vz, vx) : (person.phase + other.phase) % (Math.PI * 2)
            const overlap = PERSON_SPACING_M - distance
            pushX += Math.cos(angle) * overlap * 0.5
            pushZ += Math.sin(angle) * overlap * 0.5
          }
        }
      }
      if (!pushX && !pushZ) continue
      const length = Math.hypot(pushX, pushZ)
      const step = Math.min(length, MAX_SEPARATION_SPEED_MPS * Math.min(dt, 0.1))
      person.x += (pushX / length) * step
      person.z += (pushZ / length) * step
    }
  }

  private syncInstances(): void {
    const position = new THREE.Vector3()
    const scale = new THREE.Vector3()
    const quaternion = new THREE.Quaternion()
    const axisY = new THREE.Vector3(0, 1, 0)
    const matrix = new THREE.Matrix4()
    const cameraPosition = this.camera.position
    for (const type of TYPE_ORDER) {
      const list = this.members[type]
      const mesh = this.meshes[type]
      const gaitPhase = this.gaitPhases[type]
      const gaitStrength = this.gaitStrengths[type]
      for (let i = 0; i < list.length; i++) {
        const person = list[i]
        const bob = (0.5 - 0.5 * Math.cos(person.phase * 2)) * 0.032 * person.gaitBlend
        position.set(person.x, bob, person.z)
        quaternion.setFromAxisAngle(axisY, person.heading)
        // 远景时适度放大低模人物，保持屏幕可辨识度；近景恢复真实比例。
        const distance = Math.hypot(person.x - cameraPosition.x, person.z - cameraPosition.z)
        scale.setScalar(person.scale * Math.max(1, Math.min(12, distance / 180)))
        matrix.compose(position, quaternion, scale)
        mesh.setMatrixAt(i, matrix)
        gaitPhase.setX(i, person.phase)
        gaitStrength.setX(i, person.gaitBlend)
      }
      mesh.count = list.length
      mesh.instanceMatrix.needsUpdate = true
      gaitPhase.needsUpdate = true
      gaitStrength.needsUpdate = true
    }
  }

  private advanceVehicles(dt: number): void {
    for (const vehicle of this.vehicles) {
      if (vehicle.detourPath) {
        const target = vehicle.detourPath[vehicle.detourIndex]
        if (!target) continue
        const sourcePath = this.roadPaths[vehicle.pathIndex]
        const current =
          vehicle.detourPosition ??
          (sourcePath ? this.roadPointAt(sourcePath, vehicle.distance) : target.clone())
        vehicle.detourPosition = current
        const dx = target.x - current.x
        const dz = target.y - current.y
        const distance = Math.hypot(dx, dz)
        if (distance < 1.2) {
          current.copy(target)
          vehicle.detourIndex++
        } else {
          const ratio = Math.min(1, (vehicle.speed * dt) / distance)
          current.lerp(target, ratio)
          if (ratio >= 1) vehicle.detourIndex++
        }
        vehicle.currentSpeed = vehicle.speed
        continue
      }
      const path = this.roadPaths[vehicle.pathIndex]
      if (!path || path.points.length < 2) continue
      const total = path.cumulative[path.cumulative.length - 1]
      const point = this.roadPointAt(path, vehicle.distance)
      const incidentDistance = this.vehicleIncident
        ? Math.hypot(point.x - this.vehicleIncident.x, point.y - this.vehicleIncident.z)
        : Number.POSITIVE_INFINITY
      const stopped = !!this.vehicleIncident && incidentDistance <= this.vehicleIncident.radius
      vehicle.currentSpeed = this.vehicleIncident
        ? vehicle.speed * trafficSpeedFactor(incidentDistance, this.vehicleIncident.radius)
        : vehicle.speed
      if (!stopped) {
        vehicle.distance += vehicle.currentSpeed * vehicle.direction * dt
        if (vehicle.distance >= total) {
          vehicle.distance = total
          vehicle.direction = -1
        } else if (vehicle.distance <= 0) {
          vehicle.distance = 0
          vehicle.direction = 1
        }
      }
    }
    this.syncVehicles()
  }

  private syncVehicles(): void {
    const position = new THREE.Vector3()
    const scale = new THREE.Vector3()
    const quaternion = new THREE.Quaternion()
    const axisY = new THREE.Vector3(0, 1, 0)
    const matrix = new THREE.Matrix4()
    const cameraPosition = this.camera.position
    for (let i = 0; i < this.vehicles.length; i++) {
      const vehicle = this.vehicles[i]
      const path = this.roadPaths[vehicle.pathIndex]
      if (!path) continue
      const point =
        vehicle.detourPosition ??
        this.roadPointAt(path, vehicle.distance)
      const detourAhead = vehicle.detourPath?.[vehicle.detourIndex]
      const ahead =
        detourAhead ??
        this.roadPointAt(path, Math.min(path.cumulative[path.cumulative.length - 1], vehicle.distance + 1.5))
      const dx = ahead.x - point.x
      const dz = ahead.y - point.y
      const heading = Math.atan2(dx * vehicle.direction, dz * vehicle.direction)
      position.set(point.x, 0.1, point.y)
      quaternion.setFromAxisAngle(axisY, heading)
      const distance = Math.hypot(point.x - cameraPosition.x, point.y - cameraPosition.z)
      scale.setScalar(Math.max(1.1, Math.min(7.5, distance / 210)))
      matrix.compose(position, quaternion, scale)
      this.vehicleMesh.setMatrixAt(i, matrix)
    }
    this.vehicleMesh.count = this.vehicles.length
    this.vehicleMesh.instanceMatrix.needsUpdate = true
  }

  private roadPointAt(path: RoadPath, distance: number): THREE.Vector2 {
    const total = path.cumulative[path.cumulative.length - 1]
    const d = Math.max(0, Math.min(total, distance))
    let low = 0
    let high = path.cumulative.length - 1
    while (low + 1 < high) {
      const mid = (low + high) >> 1
      if (path.cumulative[mid] <= d) low = mid
      else high = mid
    }
    const from = path.points[low]
    const to = path.points[Math.min(high, path.points.length - 1)]
    const span = Math.max(0.0001, path.cumulative[high] - path.cumulative[low])
    return from.clone().lerp(to, (d - path.cumulative[low]) / span)
  }

  private randomVehiclePlacement(near?: { lon: number; lat: number; radius: number }): {
    pathIndex: number
    distance: number
  } | null {
    if (!this.roadPaths.length) return null
    if (near) {
      const target = this.lonLatToLocal(near.lon, near.lat, 0)
      const candidates: Array<{ pathIndex: number; distance: number }> = []
      for (let pathIndex = 0; pathIndex < this.roadPaths.length; pathIndex++) {
        const path = this.roadPaths[pathIndex]
        for (let i = 0; i < path.points.length - 1; i++) {
          const midpoint = path.points[i].clone().lerp(path.points[i + 1], 0.5)
          if (Math.hypot(midpoint.x - target.x, midpoint.y - target.z) <= near.radius) {
            candidates.push({
              pathIndex,
              distance: path.cumulative[i] + (path.cumulative[i + 1] - path.cumulative[i]) * Math.random()
            })
          }
        }
      }
      if (candidates.length) return candidates[Math.floor(Math.random() * candidates.length)]
    }
    const pathIndex = Math.floor(Math.random() * this.roadPaths.length)
    const path = this.roadPaths[pathIndex]
    const total = path.cumulative[path.cumulative.length - 1] ?? 0
    return { pathIndex, distance: Math.random() * total }
  }

  private chooseType(type: SpawnType): PersonType {
    if (type !== 'mixed') return type
    const r = Math.random()
    return r < 0.45 ? 'resident' : r < 0.72 ? 'tourist' : r < 0.88 ? 'firefighter' : 'rescuer'
  }

  private randomRoadPoint(): [number, number] | null {
    if (!this.roadPaths.length) return null
    const path = this.roadPaths[Math.floor(Math.random() * this.roadPaths.length)]
    if (!path.points.length) return null
    const total = path.cumulative[path.cumulative.length - 1]
    const distance = Math.random() * total
    const point = this.roadPointAt(path, distance)
    const ahead = this.roadPointAt(path, Math.min(total, distance + 1))
    const dx = ahead.x - point.x
    const dz = ahead.y - point.y
    const length = Math.max(0.001, Math.hypot(dx, dz))
    const offset = (2.2 + Math.random() * 1.3) * (Math.random() < 0.5 ? -1 : 1)
    return this.localToLonLat(point.x - (dz / length) * offset, point.y + (dx / length) * offset)
  }

  private clampToRegion(lon: number, lat: number): [number, number] {
    const [w, s, e, n] = this.region.bbox
    return [Math.min(e, Math.max(w, lon)), Math.min(n, Math.max(s, lat))]
  }

  spawn(count: number, type: SpawnType = 'mixed'): number {
    const total = Math.max(0, Math.min(MAX_PEOPLE - this.people.size, Math.floor(count)))
    for (let i = 0; i < total; i++) {
      const resolvedType = this.chooseType(type)
      const roadPoint = this.randomRoadPoint()
      const lon =
        roadPoint?.[0] ??
        this.region.bbox[0] + Math.random() * (this.region.bbox[2] - this.region.bbox[0])
      const lat =
        roadPoint?.[1] ??
        this.region.bbox[1] + Math.random() * (this.region.bbox[3] - this.region.bbox[1])
      this.add(resolvedType, lon, lat)
    }
    return total
  }

  spawnAt(count: number, type: SpawnType, lon: number, lat: number, radiusM = 180): number {
    const total = Math.max(0, Math.min(MAX_PEOPLE - this.people.size, Math.floor(count)))
    const center = this.lonLatToLocal(lon, lat, 0)
    for (let i = 0; i < total; i++) {
      const placement = this.randomVehiclePlacement({ lon, lat, radius: Math.max(120, radiusM * 1.35) })
      if (placement) {
        const path = this.roadPaths[placement.pathIndex]
        const point = this.roadPointAt(path, placement.distance)
        const ahead = this.roadPointAt(path, Math.min(path.cumulative[path.cumulative.length - 1], placement.distance + 1))
        const dx = ahead.x - point.x
        const dz = ahead.y - point.y
        const length = Math.max(0.001, Math.hypot(dx, dz))
        const offset = (2.1 + Math.random() * 1.5) * (Math.random() < 0.5 ? -1 : 1)
        const [plon, plat] = this.localToLonLat(point.x - (dz / length) * offset, point.y + (dx / length) * offset)
        this.add(this.chooseType(type), plon, plat)
      } else {
        const angle = Math.random() * Math.PI * 2
        const radius = Math.sqrt(Math.random()) * radiusM
        const [plon, plat] = this.localToLonLat(
          center.x + Math.cos(angle) * radius,
          center.z + Math.sin(angle) * radius
        )
        this.add(this.chooseType(type), plon, plat)
      }
    }
    return total
  }

  spawnVehicles(count = 240, near?: { lon: number; lat: number; radius: number }): number {
    const total = Math.max(0, Math.min(MAX_VEHICLES - this.vehicles.length, Math.floor(count)))
    let added = 0
    for (let i = 0; i < total; i++) {
      const placement = this.randomVehiclePlacement(near)
      if (!placement) break
      const speed = 6 + Math.random() * 9
      this.vehicles.push({
        id: `V${this.idSeq++}`,
        pathIndex: placement.pathIndex,
        distance: placement.distance,
        direction: Math.random() < 0.5 ? 1 : -1,
        speed,
        currentSpeed: speed,
        detourPath: null,
        detourIndex: 0,
        detourPosition: null
      })
      this.vehicleMesh.setColorAt(
        this.vehicles.length - 1,
        new THREE.Color(VEHICLE_COLORS[Math.floor(Math.random() * VEHICLE_COLORS.length)])
      )
      added++
    }
    if (this.vehicleMesh.instanceColor) this.vehicleMesh.instanceColor.needsUpdate = true
    this.syncVehicles()
    return added
  }

  setVehicleIncident(lon: number, lat: number, radiusM: number, autoDetour = true): void {
    const center = this.lonLatToLocal(lon, lat, 0)
    this.vehicleIncident = { x: center.x, z: center.z, radius: radiusM }
    if (autoDetour) this.applyVehicleDetours()
    this.syncVehicles()
  }

  startTrafficControl(): number {
    if (!this.vehicleIncident) return 0
    const rerouted = this.applyVehicleDetours()
    this.syncVehicles()
    return rerouted
  }

  private applyVehicleDetours(): number {
    if (!this.vehicleIncident) return 0
    const center = this.vehicleIncident
    const radiusM = center.radius
    const navigate = this.roadGraph.prepareEvacuation({ x: center.x, z: center.z }, radiusM, 6)
    let rerouted = 0
    for (const vehicle of this.vehicles) {
      const path = this.roadPaths[vehicle.pathIndex]
      if (!path) continue
      const point = vehicle.detourPosition ?? this.roadPointAt(path, vehicle.distance)
      const pathTouchesHazard = path.points.some(
        (candidate) => Math.hypot(candidate.x - center.x, candidate.y - center.z) <= radiusM
      )
      if (!pathTouchesHazard && Math.hypot(point.x - center.x, point.y - center.z) > radiusM) continue
      const planned = navigate({ x: point.x, z: point.y })
      if (!planned?.points.length) continue
      vehicle.detourPath = planned.points.map((p) => new THREE.Vector2(p.x, p.z))
      vehicle.detourIndex = 0
      vehicle.detourPosition = point.clone()
      rerouted++
    }
    return rerouted
  }

  clearVehicleIncident(): void {
    this.vehicleIncident = null
    for (const vehicle of this.vehicles) {
      vehicle.detourPath = null
      vehicle.detourIndex = 0
      vehicle.detourPosition = null
      vehicle.currentSpeed = vehicle.speed
    }
    this.syncVehicles()
  }

  getVehicleStats(): VehicleStats {
    const total = this.vehicles.length
    const rerouted = this.vehicles.filter((vehicle) => !!vehicle.detourPath?.length).length
    if (!this.vehicleIncident) {
      return { total, moving: total, affected: 0, stopped: 0, rerouted, averageSpeedKmh: 0 }
    }
    let affected = 0
    let stopped = 0
    let speedSum = 0
    for (const vehicle of this.vehicles) {
      const path = this.roadPaths[vehicle.pathIndex]
      if (!path) continue
      const point = vehicle.detourPosition ?? this.roadPointAt(path, vehicle.distance)
      if (
        Math.hypot(point.x - this.vehicleIncident.x, point.y - this.vehicleIncident.z) <=
        this.vehicleIncident.radius * 1.7
      ) {
        affected++
      }
      if (vehicle.currentSpeed <= 0.05) stopped++
      speedSum += vehicle.currentSpeed
    }
    return {
      total,
      moving: total - stopped,
      affected,
      stopped,
      rerouted,
      averageSpeedKmh: total ? Math.round((speedSum / total) * 3.6) : 0
    }
  }

  setFramePeople(
    people: Array<{ id: string; longitude: number; latitude: number; state: 'idle' | 'queued' | 'moving' | 'safe' }>,
    type: PersonType = 'resident'
  ): void {
    this.clear()
    for (const item of people) {
      const id = this.add(type, item.longitude, item.latitude)
      const person = this.people.get(id)
      if (person) {
        person.state = item.state === 'moving' ? 'evacuating' : item.state === 'safe' ? 'arrived' : 'idle'
      }
    }
    this.syncInstances()
  }

  add(type: PersonType, lon: number, lat: number, scale = 1, heading = 0): string {
    const [clon, clat] = this.clampToRegion(lon, lat)
    const local = this.lonLatToLocal(clon, clat, 0)
    const person: CrowdPerson = {
      id: `P${++this.idSeq}`,
      type,
      lon: clon,
      lat: clat,
      x: local.x,
      z: local.z,
      scale: Math.max(0.3, Math.min(4, scale)),
      heading,
      state: 'idle',
      speed: sampleWalkSpeed(type),
      gaitBlend: 0,
      reactionDelay: sampleReactionDelay(type),
      reactionRemaining: 0,
      phase: Math.random() * Math.PI * 2,
      path: [],
      pathIndex: 0,
      exitNodeId: null
    }
    this.people.set(person.id, person)
    this.members[type].push(person)
    this.syncInstances()
    return person.id
  }

  remove(id: string): boolean {
    const person = this.people.get(id)
    if (!person) return false
    this.people.delete(id)
    this.members[person.type] = this.members[person.type].filter((item) => item.id !== id)
    this.syncInstances()
    return true
  }

  clear(): void {
    this.people.clear()
    for (const type of TYPE_ORDER) this.members[type] = []
    this.vehicles.splice(0)
    this.vehicleMesh.count = 0
    this.vehicleIncident = null
    this.hazard = null
    this.evacuationCenter = null
    this.evacuationIds.clear()
    this.exitQueues.clear()
    this.exitRelease.clear()
    this.exitLabels.clear()
    this.evacuationElapsedSec = 0
    this.evacuationComplete = false
    this.peakWaiting = 0
    this.peakWaitingExitLabel = ''
    this.syncInstances()
    this.syncVehicles()
    this.clearMarkers()
  }

  setScale(id: string, scale: number): boolean {
    const person = this.people.get(id)
    if (!person) return false
    person.scale = Math.max(0.3, Math.min(4, scale))
    this.syncInstances()
    return true
  }

  setHeading(id: string, heading: number): boolean {
    const person = this.people.get(id)
    if (!person) return false
    person.heading = heading
    this.syncInstances()
    return true
  }

  walkTo(id: string, lon: number, lat: number): boolean {
    const person = this.people.get(id)
    if (!person) return false
    const point = this.lonLatToLocal(lon, lat, 0)
    person.path = [new THREE.Vector2(point.x, point.z)]
    person.pathIndex = 0
    person.state = 'walking'
    return true
  }

  walkFirstTo(lon: number, lat: number): boolean {
    const first = this.people.values().next().value as CrowdPerson | undefined
    return first ? this.walkTo(first.id, lon, lat) : false
  }

  walkPath(id: string, points: [number, number][]): boolean {
    const person = this.people.get(id)
    if (!person || points.length === 0) return false
    person.path = points.map(([lon, lat]) => {
      const point = this.lonLatToLocal(lon, lat, 0)
      return new THREE.Vector2(point.x, point.z)
    })
    person.pathIndex = 0
    person.state = 'walking'
    return true
  }

  getPerson(id: string): PersonView | null {
    const p = this.people.get(id)
    if (!p) return null
    const [lon, lat] = this.localToLonLat(p.x, p.z)
    return { id: p.id, type: p.type, longitude: lon, latitude: lat, scale: p.scale, heading: p.heading, state: p.state }
  }

  firstPersonId(): string | null {
    return this.people.keys().next().value ?? null
  }

  getStats(): CrowdStats {
    const byType: Record<PersonType, number> = { resident: 0, tourist: 0, firefighter: 0, rescuer: 0 }
    const byArea: Record<string, number> = {}
    const [w, s, e, n] = this.region.bbox
    const center = this.lonLatToLocal((w + e) / 2, (s + n) / 2, 0)
    const west = this.lonLatToLocal(w, s, 0)
    const east = this.lonLatToLocal(e, n, 0)
    const xSpan = Math.max(1, Math.abs(east.x - west.x))
    const zSpan = Math.max(1, Math.abs(east.z - west.z))
    let moving = 0
    for (const person of this.people.values()) {
      byType[person.type]++
      if (person.state === 'walking' || person.state === 'evacuating') moving++
      const col = Math.max(0, Math.min(2, Math.floor(((person.x - (center.x - xSpan / 2)) / xSpan) * 3)))
      const row = Math.max(0, Math.min(2, Math.floor(((person.z - (center.z - zSpan / 2)) / zSpan) * 3)))
      const key = `区域 ${String.fromCharCode(65 + row)}${col + 1}`
      byArea[key] = (byArea[key] ?? 0) + 1
    }
    return { total: this.people.size, moving, byType, byArea }
  }

  regionCenter(): [number, number] {
    return [...this.region.center]
  }

  focus(): boolean {
    if (!this.people.size) return false
    let x = 0
    let z = 0
    for (const person of this.people.values()) {
      x += person.x
      z += person.z
    }
    const [lon, lat] = this.localToLonLat(x / this.people.size, z / this.people.size)
    const target = new Cesium.BoundingSphere(Cesium.Cartesian3.fromDegrees(lon, lat, 1.2), 1)
    this.scene.camera.flyToBoundingSphere(target, {
      offset: new Cesium.HeadingPitchRange(
        Cesium.Math.toRadians(20),
        Cesium.Math.toRadians(-25),
        55
      ),
      duration: 1.5
    })
    return true
  }

  evacuate(lon: number, lat: number, radiusM: number): number {
    const danger = this.lonLatToLocal(lon, lat, 0)
    if (!this.hazard) this.setHazardScenario('building', radiusM)
    const radius = this.currentHazardRadius()
    this.evacuationCenter = { x: danger.x, z: danger.z, radius }

    let moved = 0
    this.evacuationIds.clear()
    this.exitQueues.clear()
    this.exitRelease.clear()
    this.exitLabels.clear()
    this.evacuationElapsedSec = 0
    this.evacuationComplete = false
    this.peakWaiting = 0
    this.peakWaitingExitLabel = ''
    const navigate = this.roadGraph.prepareEvacuation({ x: danger.x, z: danger.z }, radius, DEMO_EXIT_LIMIT)
    const routesByExit = new Map<number, THREE.Vector2[]>()
    for (const person of this.people.values()) {
      if (Math.hypot(person.x - danger.x, person.z - danger.z) > radius) continue
      const planned = navigate({ x: person.x, z: person.z })
      const route = planned
        ? planned.points.map((point) => new THREE.Vector2(point.x, point.z))
        : this.fallbackEscapeRoute(person.x, person.z, danger.x, danger.z, radius)
      person.path = route
      person.pathIndex = 0
      person.exitNodeId = planned?.exitNodeId ?? null
      person.state = 'reacting'
      person.reactionRemaining = person.reactionDelay
      this.evacuationIds.add(person.id)
      moved++
      if (planned && route.length && !routesByExit.has(planned.exitNodeId)) {
        this.exitLabel(planned.exitNodeId)
        routesByExit.set(planned.exitNodeId, route)
      }
    }
    this.refreshEvacuationMarkers(danger, radius, routesByExit)
    return moved
  }

  getEvacuationProgress(): {
    total: number
    inside: number
    escaped: number
    reacting: number
    moving: number
    waiting: number
    safe: number
    hazardRadiusM: number
    replans: number
    elapsedSec: number
    peakWaiting: number
    bottleneckExitLabel: string
    activeExits: number
    closedRoads: number
    completed: boolean
  } {
    const center = this.evacuationCenter
    if (!center || !this.evacuationIds.size) {
      return {
        total: 0,
        inside: 0,
        escaped: 0,
        reacting: 0,
        moving: 0,
        waiting: 0,
        safe: 0,
        hazardRadiusM: this.currentHazardRadius(),
        replans: this.hazard?.replans ?? 0,
        elapsedSec: 0,
        peakWaiting: 0,
        bottleneckExitLabel: '',
        activeExits: 0,
        closedRoads: 0,
        completed: false
      }
    }
    let inside = 0
    let reacting = 0
    let moving = 0
    let waiting = 0
    let safe = 0
    const activeExits = new Set<number>()
    for (const id of this.evacuationIds) {
      const person = this.people.get(id)
      if (!person) continue
      if (person.exitNodeId !== null) activeExits.add(person.exitNodeId)
      if (Math.hypot(person.x - center.x, person.z - center.z) <= center.radius) inside++
      if (person.state === 'reacting') reacting++
      else if (person.state === 'evacuating') moving++
      else if (person.state === 'waiting') waiting++
      else if (person.state === 'arrived') safe++
    }
    return {
      total: this.evacuationIds.size,
      inside,
      escaped: this.evacuationIds.size - inside,
      reacting,
      moving,
      waiting,
      safe,
      hazardRadiusM: this.currentHazardRadius(),
      replans: this.hazard?.replans ?? 0,
      elapsedSec: this.evacuationElapsedSec,
      peakWaiting: this.peakWaiting,
      bottleneckExitLabel: this.peakWaitingExitLabel,
      activeExits: activeExits.size,
      closedRoads: this.roadGraph.segmentsWithin(center, center.radius * 0.45, 500).length,
      completed: this.evacuationComplete
    }
  }

  countWithinRadius(lon: number, lat: number, radiusM: number): number {
    const center = this.lonLatToLocal(lon, lat, 0)
    let count = 0
    for (const person of this.people.values()) {
      if (Math.hypot(person.x - center.x, person.z - center.z) <= radiusM) count++
    }
    return count
  }

  dispatchResponders(
    lon: number,
    lat: number,
    type: Extract<PersonType, 'firefighter' | 'rescuer'>,
    count: number,
    startRadiusM = 220
  ): number {
    const before = this.members[type].length
    const added = this.spawnAt(count, type, lon, lat, startRadiusM)
    const list = this.members[type].slice(before)
    for (let i = 0; i < list.length; i++) {
      const angle = (i / Math.max(1, list.length)) * Math.PI * 2
      const radius = 18 + Math.random() * 24
      const point = this.lonLatToLocal(lon, lat, 0)
      const [targetLon, targetLat] = this.localToLonLat(
        point.x + Math.cos(angle) * radius,
        point.z + Math.sin(angle) * radius
      )
      this.walkTo(list[i].id, targetLon, targetLat)
    }
    return added
  }

  private fallbackEscapeRoute(
    px: number,
    pz: number,
    dangerX: number,
    dangerZ: number,
    radiusM: number
  ): THREE.Vector2[] {
    const dx = px - dangerX
    const dz = pz - dangerZ
    const length = Math.max(1, Math.hypot(dx, dz))
    return [new THREE.Vector2(dangerX + (dx / length) * (radiusM + 250), dangerZ + (dz / length) * (radiusM + 250))]
  }

  private makeLine(points: THREE.Vector2[], color: string, opacity: number): THREE.Line {
    const geometry = new THREE.BufferGeometry().setFromPoints(
      points.map((point) => new THREE.Vector3(point.x, 4.5, point.y))
    )
    const material = new THREE.LineBasicMaterial({
      color,
      transparent: true,
      opacity,
      depthWrite: false,
      depthTest: false
    })
    const line = new THREE.Line(geometry, material)
    line.renderOrder = 2
    return line
  }

  private makeRing(x: number, z: number, radius: number, color: string, opacity: number): THREE.Group {
    const group = new THREE.Group()
    const geometry = new THREE.RingGeometry(Math.max(1, radius - 3), Math.max(2, radius), 48)
    geometry.rotateX(-Math.PI / 2)
    const material = new THREE.MeshBasicMaterial({
      color,
      transparent: true,
      opacity,
      side: THREE.DoubleSide,
      depthWrite: false,
      depthTest: false
    })
    const ring = new THREE.Mesh(geometry, material)
    ring.renderOrder = 3
    const fillGeometry = new THREE.CircleGeometry(Math.max(2, radius), 48)
    fillGeometry.rotateX(-Math.PI / 2)
    const fillMaterial = new THREE.MeshBasicMaterial({
      color,
      transparent: true,
      opacity: Math.min(0.12, opacity * 0.3),
      side: THREE.DoubleSide,
      depthWrite: false,
      depthTest: false
    })
    const fill = new THREE.Mesh(fillGeometry, fillMaterial)
    fill.renderOrder = 2
    group.add(fill, ring)
    group.position.set(x, 3, z)
    return group
  }

  private clearMarkers(): void {
    this.markerGroup.traverse((object) => {
      const mesh = object as THREE.Mesh
      mesh.geometry?.dispose()
      if (Array.isArray(mesh.material)) mesh.material.forEach((material) => material.dispose())
      else mesh.material?.dispose()
    })
    this.markerGroup.clear()
  }

  async benchmark(sizes = [1, 10, 50, 100, 500, 1000]): Promise<CrowdBenchmarkRow[]> {
    const rows: CrowdBenchmarkRow[] = []
    for (const size of sizes) {
      this.clear()
      this.spawn(size, 'mixed')
      const frames = 20
      this.renderer.info.autoReset = false
      const started = performance.now()
      for (let i = 0; i < frames; i++) {
        if (i === frames - 1) this.renderer.info.reset()
        this.advance(1 / 60)
        this.syncCamera()
        this.renderer.render(this.threeScene, this.camera)
      }
      this.renderer.getContext().finish()
      const elapsed = performance.now() - started
      const triangles = this.renderer.info.render.triangles
      const drawCalls = this.renderer.info.render.calls
      this.renderer.info.autoReset = true
      const frameMs = elapsed / frames
      rows.push({
        people: size,
        fps: Number((1000 / frameMs).toFixed(1)),
        frameMs: Number(frameMs.toFixed(2)),
        drawCalls,
        triangles
      })
    }
    return rows
  }

  destroy(): void {
    this.disposed = true
    this.removePostRender()
    this.resizeObserver.disconnect()
    this.clear()
    for (const mesh of Object.values(this.meshes)) {
      mesh.geometry.dispose()
      if (Array.isArray(mesh.material)) mesh.material.forEach((material) => material.dispose())
      else mesh.material.dispose()
    }
    this.vehicleMesh.geometry.dispose()
    if (Array.isArray(this.vehicleMesh.material)) this.vehicleMesh.material.forEach((material) => material.dispose())
    else this.vehicleMesh.material.dispose()
    this.renderer.dispose()
    this.renderer.domElement.remove()
  }
}
