/**
 * 场景自定义着色器与外观（Appearance）工厂
 *
 * 设计要点：
 * - 所有效果均基于 Cesium.Primitive + 合批 GeometryInstance，一个 Primitive 一次绘制，避免成千上万 Entity；
 * - 每实例属性：color（ColorGeometryInstanceAttribute）+ fx（UNSIGNED_BYTE×4 自定义参数），
 *   顶点着色器中通过 Primitive 批表函数 czm_batchTable_fx(batchId) 读取；
 * - 动画时间：Appearance 不支持自定义 uniform，因此使用一个极简的"场景时钟"材质 —— 其 czm_getMaterial()
 *   把 u_time 写入 material.specular，片元着色器调用 czm_getMaterial() 即可取到秒级时间（每帧 1 次 uniform 更新，零分配）；
 * - 建筑高度：顶点着色器以示范区中心的局部切平面计算顶点离地高度（中心坐标以 high/low 双精度拆分烘焙为常量）；
 * - 安全模式：若自定义着色器在某些显卡上编译失败，CesiumViewer 捕获 renderError 后切回 Cesium 内置外观（见 safe*）。
 */
import * as Cesium from 'cesium'

// ------------------------------------------------------------------ 场景时钟

const CLOCK_SOURCE = `
czm_material czm_getMaterial(czm_materialInput materialInput)
{
    czm_material material = czm_getDefaultMaterial(materialInput);
    material.specular = u_time;
    return material;
}
`

export interface SceneClock {
  readonly material: Cesium.Material
  /** 每帧调用（preRender），更新时间 uniform */
  tick(): void
  /** 当前秒数 */
  now(): number
}

export function createSceneClock(): SceneClock {
  const material = new Cesium.Material({
    translucent: true,
    fabric: { type: 'CeSceneClock', uniforms: { u_time: 0 }, source: CLOCK_SOURCE }
  })
  const t0 = performance.now()
  let current = 0
  return {
    material,
    tick() {
      // 每小时回绕一次，避免 float32 精度随时间下降
      current = ((performance.now() - t0) / 1000) % 3600
      material.uniforms.u_time = current
    },
    now: () => current
  }
}

// ------------------------------------------------------------------ 每实例参数

/** 每实例自定义参数 fx（4 个 0~255 整数，着色器中读取原值） */
export function fxAttribute(a = 0, b = 0, c = 0, d = 0): Cesium.GeometryInstanceAttribute {
  return new Cesium.GeometryInstanceAttribute({
    componentDatatype: Cesium.ComponentDatatype.UNSIGNED_BYTE,
    componentsPerAttribute: 4,
    normalize: false,
    value: [byte(a), byte(b), byte(c), byte(d)]
  })
}

export function byte(v: number): number {
  return Math.max(0, Math.min(255, Math.round(v)))
}

// ------------------------------------------------------------------ 局部坐标系常量

function f(n: number): string {
  return n.toFixed(6)
}

/** 双精度拆分为 high/low（与 Cesium EncodedCartesian3.encode 相同算法，用于 GPU 相对视点精度） */
function encode(value: number): { high: number; low: number } {
  const high = value >= 0 ? Math.floor(value / 65536) * 65536 : -Math.floor(-value / 65536) * 65536
  return { high, low: value - high }
}

/** 生成示范区局部坐标系 GLSL 常量（中心 high/low、天顶方向、方向光） */
export function regionFrameGlsl(lon: number, lat: number): string {
  const center = Cesium.Cartesian3.fromDegrees(lon, lat, 0)
  const ex = encode(center.x)
  const ey = encode(center.y)
  const ez = encode(center.z)
  const enc = {
    high: new Cesium.Cartesian3(ex.high, ey.high, ez.high),
    low: new Cesium.Cartesian3(ex.low, ey.low, ez.low)
  }
  const up = Cesium.Ellipsoid.WGS84.geodeticSurfaceNormal(center, new Cesium.Cartesian3())
  const enu = Cesium.Transforms.eastNorthUpToFixedFrame(center)
  // 方向光：来自东南上方
  const lightLocal = Cesium.Cartesian3.normalize(new Cesium.Cartesian3(0.55, -0.5, 0.65), new Cesium.Cartesian3())
  const light = Cesium.Matrix4.multiplyByPointAsVector(enu, lightLocal, new Cesium.Cartesian3())
  Cesium.Cartesian3.normalize(light, light)
  const v = (c: Cesium.Cartesian3) => `vec3(${f(c.x)}, ${f(c.y)}, ${f(c.z)})`
  return `
const vec3 ce_centerHigh = ${v(enc.high)};
const vec3 ce_centerLow = ${v(enc.low)};
const vec3 ce_up = ${v(up)};
const vec3 ce_light = ${v(light)};
`
}

// ------------------------------------------------------------------ 建筑

function buildingVS(frame: string, startFrame: number): string {
  return `
in vec3 position3DHigh;
in vec3 position3DLow;
in vec3 normal;
in vec4 color;
in float batchId;

out vec3 v_positionEC;
out vec4 v_color;
out vec4 v_info;
out float v_shade;
${frame}
const float ce_startFrame = ${startFrame.toFixed(1)};

void main()
{
    // fx: x=效果模式 y=建筑高度/2 z=随机种子
    vec4 fx = czm_batchTable_fx(batchId);
    vec3 rel = (position3DHigh - ce_centerHigh) + (position3DLow - ce_centerLow);
    float h = max(dot(rel, ce_up), 0.0);
    float top = max(fx.y * 2.0, 3.0);

    // 城市生长动画：按实例种子错峰从地面升起
    float grow = clamp((czm_frameNumber - ce_startFrame - fx.z * 0.3) / 70.0, 0.0, 1.0);
    grow = 1.0 - pow(1.0 - grow, 3.0);

    vec4 p = czm_computePosition();
    p.xyz -= ce_up * (h * (1.0 - grow));

    v_positionEC = (czm_modelViewRelativeToEye * p).xyz;
    v_color = color;
    v_info = vec4(h, top, fx.x, dot(normal, ce_up));
    v_shade = dot(normal, ce_light);
    gl_Position = czm_modelViewProjectionRelativeToEye * p;
}
`
}

const BUILDING_FS = `
in vec3 v_positionEC;
in vec4 v_color;
in vec4 v_info;
in float v_shade;

void main()
{
    czm_materialInput materialInput;
    materialInput.positionToEyeEC = -v_positionEC;
    float t = czm_getMaterial(materialInput).specular;

    float h = v_info.x;
    float top = v_info.y;
    float mode = v_info.z;
    float roof = smoothstep(0.6, 0.9, v_info.w);
    float k = clamp(h / top, 0.0, 1.0);
    vec3 base = v_color.rgb;

    // 竖向渐变：底部深、顶部亮
    vec3 c = base * (0.26 + 0.92 * pow(k, 0.85));
    // 立面朝向明暗
    c *= 0.7 + 0.3 * clamp(v_shade * 0.5 + 0.5, 0.0, 1.0);
    // 楼层线
    float floorLine = smoothstep(0.88, 1.0, fract(h / 3.6)) * (1.0 - roof) * step(4.0, h);
    c += base * floorLine * 0.12;
    // 檐口描边光
    float rim = smoothstep(top - 2.4, top - 0.2, h) * (1.0 - roof);
    c += vec3(0.32, 0.86, 1.0) * rim * 0.55;
    // 屋顶
    c = mix(c, base * 0.8 + vec3(0.03, 0.09, 0.13), roof);

    // 上行扫描光带（约 8 秒一个周期）
    float scanH = mod(t * 40.0, 340.0) - 20.0;
    float band = 1.0 - smoothstep(0.0, 7.0, abs(h - scanH));
    c += vec3(0.3, 0.85, 1.0) * band * 0.7 * (1.0 - roof * 0.7);

    float alpha = v_color.a;
    if (mode > 0.5 && mode < 1.5) {
        // 关联活动事件：红色告警脉冲
        float pulse = 0.5 + 0.5 * sin(t * 5.5);
        vec3 alarm = vec3(1.0, 0.2, 0.17) * (0.55 + 0.8 * k);
        c = mix(c, alarm, 0.5 + 0.42 * pulse);
        c += vec3(1.0, 0.45, 0.35) * rim * pulse;
        alpha = 1.0;
    } else if (mode > 1.5 && mode < 2.5) {
        // 选中高亮
        float pulse = 0.5 + 0.5 * sin(t * 3.2);
        c = mix(c, vec3(0.55, 0.95, 1.0), 0.32 + 0.14 * pulse);
        c += vec3(0.3, 0.75, 0.9) * rim;
        alpha = 1.0;
    } else if (mode > 2.5) {
        // 沉降预警：缓慢呼吸
        float breathe = 0.5 + 0.5 * sin(t * 2.0);
        c += base * (0.12 + 0.28 * breathe) * k;
        alpha = max(alpha, 0.96);
    }

    // 远景雾化，融入暗色底图
    float fog = smoothstep(3500.0, 14000.0, length(v_positionEC));
    c = mix(c, vec3(0.02, 0.05, 0.1), fog * 0.6);
    out_FragColor = vec4(c, alpha);
}
`

export function buildingAppearance(clock: SceneClock, frame: string, startFrame: number): Cesium.MaterialAppearance {
  return new Cesium.MaterialAppearance({
    material: clock.material,
    translucent: true,
    closed: true,
    materialSupport: Cesium.MaterialAppearance.MaterialSupport.BASIC,
    vertexShaderSource: buildingVS(frame, startFrame),
    fragmentShaderSource: BUILDING_FS
  })
}

export function safeBuildingAppearance(): Cesium.PerInstanceColorAppearance {
  return new Cesium.PerInstanceColorAppearance({ translucent: true, closed: true })
}

// ------------------------------------------------------------------ 地面圆（事件涟漪 / 雷达扫描）

const SURFACE_VS = `
in vec3 position3DHigh;
in vec3 position3DLow;
in vec2 st;
in vec4 color;
in float batchId;

out vec3 v_positionEC;
out vec2 v_st;
out vec4 v_color;
out vec4 v_fx;

void main()
{
    vec4 p = czm_computePosition();
    v_positionEC = (czm_modelViewRelativeToEye * p).xyz;
    v_st = st;
    v_color = color;
    v_fx = czm_batchTable_fx(batchId);
    gl_Position = czm_modelViewProjectionRelativeToEye * p;
}
`

const RIPPLE_FS = `
in vec3 v_positionEC;
in vec2 v_st;
in vec4 v_color;
in vec4 v_fx;

void main()
{
    czm_materialInput materialInput;
    materialInput.positionToEyeEC = -v_positionEC;
    float t = czm_getMaterial(materialInput).specular;

    float d = length(v_st - vec2(0.5)) * 2.0;
    if (d > 1.0) {
        discard;
    }
    // fx: x=模式(0 常规 / 1 新事件强提示) y=速度×100 z=相位种子
    float strong = step(0.5, v_fx.x);
    float speed = v_fx.y / 100.0;
    float seed = v_fx.z / 255.0;
    float n = mix(2.0, 3.0, strong);
    float phase = fract(d * n - t * speed - seed);
    float ripple = pow(phase, mix(6.0, 3.5, strong));
    float edge = smoothstep(0.9, 0.975, d) * (1.0 - smoothstep(0.975, 1.0, d));
    float core = 1.0 - smoothstep(0.0, 0.2, d);
    float fade = 1.0 - smoothstep(0.5, 1.0, d);

    float a = ripple * (0.3 + 0.7 * fade) * mix(0.8, 1.0, strong) + edge * 0.5 + core * 0.35;
    vec3 c = mix(v_color.rgb, vec3(1.0), core * 0.35 + ripple * 0.12);
    out_FragColor = vec4(c, clamp(a * v_color.a, 0.0, 1.0));
}
`

const RADAR_FS = `
in vec3 v_positionEC;
in vec2 v_st;
in vec4 v_color;
in vec4 v_fx;

void main()
{
    czm_materialInput materialInput;
    materialInput.positionToEyeEC = -v_positionEC;
    float t = czm_getMaterial(materialInput).specular;

    vec2 q = v_st - vec2(0.5);
    float d = length(q) * 2.0;
    if (d > 1.0) {
        discard;
    }
    float ang = atan(q.y, q.x);
    float sweep = mod(t * 0.7, czm_twoPi);
    float lag = mod(sweep - ang + czm_twoPi * 2.0, czm_twoPi) / czm_twoPi;
    float trail = pow(1.0 - lag, 9.0);
    float lead = 1.0 - smoothstep(0.0, 0.006, lag);

    float ringDist = abs(fract(d * 5.0 + 0.5) - 0.5) / 5.0;
    float grid = 1.0 - smoothstep(0.0015, 0.005, ringDist);
    float edge = smoothstep(0.975, 0.995, d) * (1.0 - smoothstep(0.995, 1.0, d));
    float centerFade = smoothstep(0.0, 0.12, d);

    float a = (trail * 0.32 + lead * 0.5) * centerFade * (0.35 + 0.65 * d) + grid * 0.1 + edge * 0.45;
    vec3 c = mix(v_color.rgb, vec3(0.85, 1.0, 1.0), lead * 0.6);
    out_FragColor = vec4(c, clamp(a * v_color.a, 0.0, 1.0));
}
`

function surfaceAppearance(clock: SceneClock, fs: string): Cesium.MaterialAppearance {
  return new Cesium.MaterialAppearance({
    material: clock.material,
    translucent: true,
    closed: false,
    faceForward: false,
    flat: true,
    vertexShaderSource: SURFACE_VS,
    fragmentShaderSource: fs
  })
}

export const SURFACE_VERTEX_FORMAT = Cesium.VertexFormat.POSITION_AND_ST

export function rippleAppearance(clock: SceneClock): Cesium.MaterialAppearance {
  return surfaceAppearance(clock, RIPPLE_FS)
}

export function radarAppearance(clock: SceneClock): Cesium.MaterialAppearance {
  return surfaceAppearance(clock, RADAR_FS)
}

// ------------------------------------------------------------------ 折线（路况流光 / 事件光柱）

let polylineVSCache: string | null = null

/** 基于 Cesium 默认折线外观顶点着色器注入每实例 color / fx */
function polylineVS(): string {
  if (polylineVSCache) return polylineVSCache
  const base = new Cesium.PolylineMaterialAppearance().vertexShaderSource
  const declTarget = 'in float batchId;'
  const assignTarget = 'v_polylineAngle = angle;'
  if (!base.includes(declTarget) || !base.includes(assignTarget)) {
    throw new Error('[scene] 折线着色器模板不匹配，改用内置外观')
  }
  polylineVSCache = base
    .replace(declTarget, `${declTarget}\nin vec4 color;\nout vec4 v_color;\nout vec4 v_fx;`)
    .replace(assignTarget, `${assignTarget}\n    v_color = color;\n    v_fx = czm_batchTable_fx(batchId);`)
  return polylineVSCache
}

const ROAD_FS = `
in vec2 v_st;
in vec4 v_color;
in vec4 v_fx;

void main()
{
    czm_materialInput materialInput;
    float t = czm_getMaterial(materialInput).specular;

    vec2 st = v_st;
    st.t = czm_readNonPerspective(st.t, gl_FragCoord.w);
    float across = abs(st.t - 0.5) * 2.0;
    float core = 1.0 - smoothstep(0.1, 0.42, across);
    float glow = pow(max(1.0 - across, 0.0), 2.2);

    // fx: x=流速×100（周期/秒）y=光点个数 z=高亮
    float speed = v_fx.x / 100.0;
    float phase = fract(st.s * max(v_fx.y, 1.0) - t * speed);
    float trail = pow(phase, 5.0);
    float hi = step(0.5, v_fx.z) * (0.6 + 0.4 * sin(t * 6.0));

    vec3 base = v_color.rgb;
    vec3 rgb = base * (0.5 * glow + 0.7 * core) + mix(base, vec3(1.0), 0.55) * trail * (core + glow * 0.35);
    rgb *= 1.0 + hi * 0.9;
    float a = clamp(glow * 0.45 + core * 0.5 + trail * 0.55 * (core + glow * 0.3) + hi * glow * 0.3, 0.0, 1.0);
    out_FragColor = vec4(rgb, a * v_color.a);
    czm_writeLogDepth();
}
`

const BEAM_FS = `
in vec2 v_st;
in vec4 v_color;
in vec4 v_fx;

void main()
{
    czm_materialInput materialInput;
    float t = czm_getMaterial(materialInput).specular;

    vec2 st = v_st;
    st.t = czm_readNonPerspective(st.t, gl_FragCoord.w);
    float across = abs(st.t - 0.5) * 2.0;
    float glow = pow(max(1.0 - across, 0.0), 1.7);
    float core = 1.0 - smoothstep(0.0, 0.3, across);
    float fadeUp = pow(1.0 - st.s, 1.35);
    float seed = v_fx.z / 255.0 * 6.2831853;
    float rise = pow(fract(st.s * 1.6 - t * 0.55 + seed), 9.0);
    float pulse = 0.82 + 0.18 * sin(t * 3.0 + seed);

    vec3 c = mix(v_color.rgb, vec3(1.0), core * 0.45 + rise * 0.35);
    float a = (glow * fadeUp * 0.8 + rise * glow * 0.7 * (1.0 - st.s)) * pulse;
    out_FragColor = vec4(c, clamp(a * v_color.a, 0.0, 1.0));
    czm_writeLogDepth();
}
`

function lineAppearance(clock: SceneClock, fs: string): Cesium.PolylineMaterialAppearance {
  return new Cesium.PolylineMaterialAppearance({
    material: clock.material,
    translucent: true,
    vertexShaderSource: polylineVS(),
    fragmentShaderSource: fs
  })
}

export const LINE_VERTEX_FORMAT = Cesium.PolylineMaterialAppearance.VERTEX_FORMAT

export function roadAppearance(clock: SceneClock): Cesium.Appearance {
  return lineAppearance(clock, ROAD_FS)
}

export function beamAppearance(clock: SceneClock): Cesium.Appearance {
  return lineAppearance(clock, BEAM_FS)
}

export function safeLineAppearance(): Cesium.Appearance {
  return new Cesium.PolylineColorAppearance({ translucent: true })
}
