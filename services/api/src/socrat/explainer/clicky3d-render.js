/* Clicky3D renderer: the HeyClicky studio in WebGL2. Environment and irradiance are baked
   once, then each frame runs shadow, half-res AO, the studio pass, ids, and the ink composite.
   Shader math and constants are the recovered ones; only the API around them is ours. */
const Clicky3DRender = (() => {
  'use strict';

  const PI = Math.PI;
  const SHADOW_SIZE = 1024;
  const ENV_SIZE = 128;
  const ENV_MIPS = 6;
  const IRR_SIZE = 32;
  const KEY_DIR = norm([-0.55, 0.62, 0.56]);
  const RIM_DIR = norm([0.35, 0.45, -0.85]);
  const SHADOW_DIR = norm([-0.15, 1.0, 0.12]);
  const KEY_COLOR = [1.0, 0.97, 0.92];
  const RIM_COLOR = [0.78, 0.86, 1.0];
  const KEY_INTENSITY = 2.4;
  const RIM_INTENSITY = 0.55;
  const ENV_INTENSITY = 0.9;
  const EXPOSURE = 1.7;
  const LOOK_POWER = 1.3;
  const LOOK_SATURATION = 1.365;
  const ROOM_LEVEL = 0.3;
  const GROUND_OPACITY = 0.3;

  // ---------------------------------------------------------------- matrix helpers
  const m4 = () => new Float32Array(16);
  function identity() { const m = m4(); m[0] = m[5] = m[10] = m[15] = 1; return m; }
  function mul(a, b) {
    const o = m4();
    for (let c = 0; c < 4; c++) for (let r = 0; r < 4; r++) {
      o[c * 4 + r] = a[r] * b[c * 4] + a[4 + r] * b[c * 4 + 1] + a[8 + r] * b[c * 4 + 2] + a[12 + r] * b[c * 4 + 3];
    }
    return o;
  }
  function perspective(fov, aspect, near, far) {
    const m = m4(), f = 1 / Math.tan((fov * PI) / 360), nf = 1 / (near - far);
    m[0] = f / aspect; m[5] = f; m[10] = (far + near) * nf; m[11] = -1; m[14] = 2 * far * near * nf;
    return m;
  }
  function ortho(l, r, b, t, n, f) {
    const m = identity();
    m[0] = 2 / (r - l); m[5] = 2 / (t - b); m[10] = -2 / (f - n);
    m[12] = -(r + l) / (r - l); m[13] = -(t + b) / (t - b); m[14] = -(f + n) / (f - n);
    return m;
  }
  function lookAt(eye, target, up) {
    const z = norm([eye[0] - target[0], eye[1] - target[1], eye[2] - target[2]]);
    const x = norm(cross(up, z));
    const y = cross(z, x);
    const m = m4();
    m[0] = x[0]; m[4] = x[1]; m[8] = x[2]; m[12] = -dot(x, eye);
    m[1] = y[0]; m[5] = y[1]; m[9] = y[2]; m[13] = -dot(y, eye);
    m[2] = z[0]; m[6] = z[1]; m[10] = z[2]; m[14] = -dot(z, eye);
    m[15] = 1;
    return m;
  }
  function norm(v) { const l = Math.hypot(v[0], v[1], v[2]) || 1; return [v[0] / l, v[1] / l, v[2] / l]; }
  function cross(a, b) { return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]; }
  function dot(a, b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; }

  // ---------------------------------------------------------------- shader sources
  const FULLSCREEN_VERT = `#version 300 es
precision highp float;
void main() {
  vec2 p = vec2(float((gl_VertexID << 1) & 2), float(gl_VertexID & 2));
  gl_Position = vec4(p * 2.0 - 1.0, 0.0, 1.0);
}`;

  const ENV_COMPONENTS = `
const float PI = 3.14159265358979;
float saturate(float v) { return clamp(v, 0.0, 1.0); }
float softbox(vec3 d, vec3 n, float hw, float hh, float intensity) {
  float k = dot(d, n);
  if (k <= 0.0) return 0.0;
  vec3 helper = abs(n.y) > 0.95 ? vec3(0.0, 0.0, 1.0) : vec3(0.0, 1.0, 0.0);
  vec3 u = normalize(cross(helper, n));
  vec3 v = cross(n, u);
  vec2 p = vec2(dot(d, u), dot(d, v)) / k;
  vec2 q = abs(p) - vec2(hw, hh);
  float edge = max(q.x, q.y);
  return intensity * (1.0 - smoothstep(-0.03, 0.03, edge));
}
vec3 studioRadiance(vec3 d, float room) {
  float up = d.y;
  vec3 ceiling = vec3(0.96, 0.97, 1.0), wall = vec3(0.84, 0.86, 0.90), floorColor = vec3(0.55, 0.53, 0.52);
  vec3 c = up >= 0.0 ? mix(wall, ceiling, smoothstep(0.0, 0.85, up)) : mix(wall, floorColor, smoothstep(0.0, 0.3, -up));
  c *= room;
  c += softbox(d, normalize(vec3(-0.55, 0.62, 0.56)), 0.45, 0.32, 6.0) * vec3(1.0, 0.97, 0.92);
  c += softbox(d, normalize(vec3(0.85, 0.22, 0.3)), 0.10, 0.62, 3.0);
  c += softbox(d, vec3(0.0, 1.0, 0.0), 0.55, 0.40, 2.2);
  c += softbox(d, normalize(vec3(0.35, 0.45, -0.85)), 0.40, 0.14, 2.4) * vec3(0.80, 0.88, 1.0);
  return c;
}
vec3 cubeDirection(int face, vec2 uv) {
  if (face == 0) return normalize(vec3(1.0, -uv.y, -uv.x));
  if (face == 1) return normalize(vec3(-1.0, -uv.y, uv.x));
  if (face == 2) return normalize(vec3(uv.x, 1.0, uv.y));
  if (face == 3) return normalize(vec3(uv.x, -1.0, -uv.y));
  if (face == 4) return normalize(vec3(uv.x, -uv.y, 1.0));
  return normalize(vec3(-uv.x, -uv.y, -1.0));
}
uint reverseBits(uint x) {
  x = ((x & 0x55555555u) << 1) | ((x & 0xAAAAAAAAu) >> 1);
  x = ((x & 0x33333333u) << 2) | ((x & 0xCCCCCCCCu) >> 2);
  x = ((x & 0x0F0F0F0Fu) << 4) | ((x & 0xF0F0F0F0u) >> 4);
  x = ((x & 0x00FF00FFu) << 8) | ((x & 0xFF00FF00u) >> 8);
  return (x << 16) | (x >> 16);
}
vec2 hammersley(uint i, uint count) {
  return vec2(float(i) / float(count), float(reverseBits(i)) * 2.3283064365386963e-10);
}
vec3 tangentToWorld(vec3 hv, vec3 n) {
  vec3 upv = abs(n.z) < 0.999 ? vec3(0.0, 0.0, 1.0) : vec3(1.0, 0.0, 0.0);
  vec3 tx = normalize(cross(upv, n));
  vec3 ty = cross(n, tx);
  return tx * hv.x + ty * hv.y + n * hv.z;
}`;

  const ENV_FRAG = `#version 300 es
precision highp float;
uniform int uFace;
uniform int uSize;
uniform int uLevel;
uniform int uLevels;
uniform float uRoom;
out vec4 fragColor;
${ENV_COMPONENTS}
void main() {
  vec2 uv = gl_FragCoord.xy / float(uSize) * 2.0 - 1.0;
  vec3 n = cubeDirection(uFace, uv);
  float roughness = float(uLevel) / float(max(1, uLevels - 1));
  vec3 total = vec3(0.0);
  if (uLevel == 0) {
    total = studioRadiance(n, uRoom);
  } else {
    float alpha = roughness * roughness;
    float weight = 0.0;
    const uint samples = 192u;
    for (uint i = 0u; i < samples; i++) {
      vec2 xi = hammersley(i, samples);
      float phi = 2.0 * PI * xi.x;
      float cosTheta = sqrt((1.0 - xi.y) / (1.0 + (alpha * alpha - 1.0) * xi.y));
      float sinTheta = sqrt(1.0 - cosTheta * cosTheta);
      vec3 hv = tangentToWorld(vec3(cos(phi) * sinTheta, sin(phi) * sinTheta, cosTheta), n);
      vec3 l = normalize(2.0 * dot(n, hv) * hv - n);
      float nl = dot(n, l);
      if (nl > 0.0) { total += studioRadiance(l, uRoom) * nl; weight += nl; }
    }
    total /= max(weight, 1e-4);
  }
  fragColor = vec4(total, 1.0);
}`;

  const IRR_FRAG = `#version 300 es
precision highp float;
uniform int uFace;
uniform int uSize;
uniform float uRoom;
out vec4 fragColor;
${ENV_COMPONENTS}
void main() {
  vec2 uv = gl_FragCoord.xy / float(uSize) * 2.0 - 1.0;
  vec3 n = cubeDirection(uFace, uv);
  vec3 total = vec3(0.0);
  const uint samples = 512u;
  for (uint i = 0u; i < samples; i++) {
    vec2 xi = hammersley(i, samples);
    float phi = 2.0 * PI * xi.x;
    float cosTheta = sqrt(1.0 - xi.y), sinTheta = sqrt(xi.y);
    vec3 l = tangentToWorld(vec3(cos(phi) * sinTheta, sin(phi) * sinTheta, cosTheta), n);
    total += studioRadiance(l, uRoom);
  }
  fragColor = vec4(total / float(samples), 1.0);
}`;

  const OBJECT_VERT = `#version 300 es
precision highp float;
layout(location = 0) in vec3 aPosition;
layout(location = 1) in vec3 aNormal;
layout(location = 2) in vec2 aUv;
uniform mat4 uViewProjection;
uniform mat4 uModel;
uniform mat3 uNormalMatrix;
out vec3 vWorld;
out vec3 vNormal;
out vec2 vUv;
void main() {
  vec4 world = uModel * vec4(aPosition, 1.0);
  vWorld = world.xyz;
  vNormal = uNormalMatrix * aNormal;
  vUv = aUv;
  gl_Position = uViewProjection * world;
}`;

  const STUDIO_FRAG = `#version 300 es
precision highp float;
precision highp samplerCube;
precision highp sampler2D;
in vec3 vWorld;
in vec3 vNormal;
in vec2 vUv;
out vec4 fragColor;
uniform samplerCube uEnvironmentMap;
uniform samplerCube uIrradianceMap;
uniform sampler2D uShadowMap;
uniform sampler2D uOcclusionMap;
uniform sampler2D uOcclusionDistances;
uniform vec4 uEye;
uniform vec4 uViewForward;
uniform vec4 uKey;
uniform vec4 uKeyColor;
uniform vec4 uRim;
uniform vec4 uRimColor;
uniform vec4 uEnvironment;
uniform vec4 uShadow;
uniform vec4 uOcclusion;
uniform vec4 uGrade;
uniform vec4 uCutHatch;
uniform mat4 uLightViewProjection;
uniform vec3 uShadowDirection;
uniform vec4 uBaseColor;
uniform vec4 uEmissive;
uniform vec4 uSurface;
uniform vec4 uCoat;
uniform vec4 uFlags;
uniform vec4 uCut;
uniform vec4 uBands[16];
const float PI = 3.14159265358979;
const float INV_PI = 0.3183098861837907;
float saturate(float v) { return clamp(v, 0.0, 1.0); }
vec3 sRGBFromLinear(vec3 value) {
  vec3 v = max(value, 0.0);
  vec3 curved = pow(v, vec3(0.41666)) * 1.055 - 0.055;
  return mix(curved, value * 12.92, step(value, vec3(0.0031308)));
}
float D_GGX(float alpha, float nh) { float a2 = alpha * alpha; float d = nh * nh * (a2 - 1.0) + 1.0; return INV_PI * a2 / (d * d); }
float V_Smith(float alpha, float nl, float nv) {
  float a2 = alpha * alpha;
  float gv = nl * sqrt(a2 + (1.0 - a2) * nv * nv), gl = nv * sqrt(a2 + (1.0 - a2) * nl * nl);
  return 0.5 / max(gv + gl, 1e-6);
}
vec3 F_Schlick(vec3 f0, float vh) { float f = exp2((-5.55473 * vh - 6.98316) * vh); return f0 * (1.0 - f) + f; }
vec3 specularGGX(vec3 l, vec3 v, vec3 n, vec3 f0, float roughness) {
  float alpha = roughness * roughness;
  vec3 hv = normalize(l + v);
  float nl = saturate(dot(n, l)), nv = saturate(dot(n, v)), nh = saturate(dot(n, hv)), vh = saturate(dot(v, hv));
  return F_Schlick(f0, vh) * (V_Smith(alpha, nl, nv) * D_GGX(alpha, nh));
}
vec3 environmentBRDF(vec3 f0, float roughness, float nv) {
  const vec4 c0 = vec4(-1.0, -0.0275, -0.572, 0.022), c1 = vec4(1.0, 0.0425, 1.04, -0.04);
  vec4 r = roughness * c0 + c1;
  float a004 = min(r.x * r.x, exp2(-9.28 * nv)) * r.x + r.y;
  vec2 ab = vec2(-1.04, 1.04) * a004 + r.zw;
  return f0 * ab.x + ab.y;
}
vec3 neutralToneMap(vec3 color) {
  const float startCompression = 0.8 - 0.04, desaturation = 0.15;
  float x = min(color.r, min(color.g, color.b));
  float offset = x < 0.08 ? x - 6.25 * x * x : 0.04;
  color -= offset;
  float peak = max(color.r, max(color.g, color.b));
  if (peak < startCompression) return color;
  float d = 1.0 - startCompression;
  float newPeak = 1.0 - d * d / (peak + d - startCompression);
  color *= newPeak / peak;
  float g = 1.0 - 1.0 / (desaturation * (peak - newPeak) + 1.0);
  return mix(color, vec3(newPeak), g);
}
vec3 agxToneMap(vec3 color, float power, float saturation) {
  const mat3 sRGBToRec2020 = mat3(vec3(0.6274, 0.0691, 0.0164), vec3(0.3293, 0.9195, 0.0880), vec3(0.0433, 0.0113, 0.8956));
  const mat3 rec2020ToSRGB = mat3(vec3(1.6605, -0.1246, -0.0182), vec3(-0.5876, 1.1329, -0.1006), vec3(-0.0728, -0.0083, 1.1187));
  const mat3 inset = mat3(vec3(0.856627153315983, 0.137318972929847, 0.11189821299995),
                          vec3(0.0951212405381588, 0.761241990602591, 0.0767994186031903),
                          vec3(0.0482516061458583, 0.101439036467562, 0.811302368396859));
  const mat3 outset = mat3(vec3(1.1271005818144368, -0.1413297634984383, -0.14132976349843826),
                           vec3(-0.11060664309660323, 1.157823702216272, -0.11060664309660294),
                           vec3(-0.016493938717834573, -0.016493938717834257, 1.2519364065950405));
  const float minEv = -12.47393, maxEv = 4.026069;
  vec3 x = inset * (sRGBToRec2020 * color);
  x = clamp((log2(max(x, vec3(1e-10))) - minEv) / (maxEv - minEv), 0.0, 1.0);
  vec3 x2 = x * x, x4 = x2 * x2;
  x = 15.5 * x4 * x2 - 40.14 * x4 * x + 31.96 * x4 - 6.868 * x2 * x + 0.4298 * x2 + 0.1191 * x - 0.00232;
  float luma = dot(x, vec3(0.2126, 0.7152, 0.0722));
  x = pow(max(x, 0.0), vec3(power));
  x = luma + saturation * (x - luma);
  x = pow(max(outset * x, 0.0), vec3(2.2));
  return clamp(rec2020ToSRGB * x, 0.0, 1.0);
}
vec3 toneMap(vec3 color) {
  return uGrade.x > 0.5 ? agxToneMap(color, uGrade.y, uGrade.z) : neutralToneMap(color);
}
vec3 turnIntoStudio(vec3 d) {
  float c = uEnvironment.x, s = uEnvironment.y;
  return vec3(c * d.x - s * d.z, d.y, s * d.x + c * d.z);
}
const vec2 SHADOW_DISK[12] = vec2[12](
  vec2(-0.326, -0.406), vec2(-0.840, -0.074), vec2(-0.696, 0.457), vec2(-0.203, 0.621),
  vec2(0.962, -0.195), vec2(0.473, -0.480), vec2(0.519, 0.767), vec2(0.185, -0.893),
  vec2(0.507, 0.064), vec2(0.896, 0.412), vec2(-0.322, -0.933), vec2(-0.792, -0.598)
);
float shadowVisibility(vec3 world, vec3 normal, float softness) {
  vec3 towardLight = uShadowDirection;
  float facing = dot(normal, towardLight);
  vec3 offsetWorld = world + normal * uShadow.z * (1.0 + 4.0 * (1.0 - saturate(facing)));
  vec4 clip = uLightViewProjection * vec4(offsetWorld, 1.0);
  vec3 ndc = clip.xyz / clip.w;
  vec2 uv = vec2(ndc.x * 0.5 + 0.5, ndc.y * 0.5 + 0.5);
  if (any(lessThan(uv, vec2(0.0))) || any(greaterThan(uv, vec2(1.0))) || ndc.z > 1.0) return 1.0;
  float reference = ndc.z * 0.5 + 0.5 - uShadow.y;
  float sum = 0.0;
  for (int k = 0; k < 12; k++) {
    vec2 at = uv + SHADOW_DISK[k] * uShadow.x * softness;
    sum += reference <= texture(uShadowMap, at).r ? 1.0 : 0.0;
  }
  return mix(smoothstep(-0.35, 0.25, facing), sum / 12.0, smoothstep(-0.2, 0.1, facing));
}
float occlusionAt(vec2 pixel, float distanceValue, float reach) {
  ivec2 size = textureSize(uOcclusionMap, 0);
  vec2 at = pixel * 0.5 - 0.5;
  ivec2 base = ivec2(floor(at));
  vec2 f = at - vec2(base);
  float sum = 0.0, weight = 0.0, nearest = 1.0, nearestGap = 1e9;
  for (int y = 0; y <= 1; y++) for (int x = 0; x <= 1; x++) {
    ivec2 q = clamp(base + ivec2(x, y), ivec2(0), size - 1);
    float dq = texelFetch(uOcclusionDistances, q, 0).r;
    float value = texelFetch(uOcclusionMap, q, 0).a;
    float gap = dq > 0.0 ? abs(dq - distanceValue) : 1e9;
    if (gap < nearestGap) { nearestGap = gap; nearest = value; }
    float wq = (x == 1 ? f.x : 1.0 - f.x) * (y == 1 ? f.y : 1.0 - f.y) * saturate(1.0 - gap / (reach * 0.25));
    sum += value * wq;
    weight += wq;
  }
  return weight > 1e-4 ? sum / weight : nearest;
}
void main() {
  float ambientOcclusion = 1.0;
  if (uOcclusion.z > 0.5 && uCoat.w < 0.5) {
    ambientOcclusion = occlusionAt(gl_FragCoord.xy, dot(vWorld - uEye.xyz, uViewForward.xyz), max(uOcclusion.x, 1e-5));
  }
  bool isCutPart = dot(uCut.xyz, uCut.xyz) > 0.25;
  float hatchLine = 0.0;
  {
    vec3 cutNormal = isCutPart ? uCut.xyz : vec3(0.0, 0.0, 1.0);
    vec3 toFragment = vWorld - uEye.xyz;
    float along = dot(cutNormal, toFragment);
    vec3 onPlane = abs(along) > 1e-6 ? uEye.xyz + toFragment * ((uCut.w - dot(cutNormal, uEye.xyz)) / along) : vWorld;
    vec3 across = abs(cutNormal.y) < 0.95 ? normalize(cross(cutNormal, vec3(0.0, 1.0, 0.0))) : normalize(cross(cutNormal, vec3(1.0, 0.0, 0.0)));
    vec3 diagonal = (across - cross(cutNormal, across)) * 0.70710678;
    float lines = dot(onPlane, diagonal) / max(uCutHatch.x, 1e-6);
    float fromLine = abs(fract(lines - 0.4) - 0.5);
    float soften = 0.5 * fwidth(lines);
    hatchLine = 1.0 - smoothstep(0.1 - soften, 0.1 + soften, fromLine);
  }
  if (isCutPart) {
    if (dot(vWorld, uCut.xyz) > uCut.w) discard;
    if (!gl_FrontFacing && uFlags.z < 0.5) {
      vec4 cutBase = uBaseColor;
      vec3 face = mix(cutBase.rgb, vec3(1.0), 0.22) * mix(0.82, 1.0, ambientOcclusion);
      face *= mix(1.0, 0.72, hatchLine);
      fragColor = vec4(sRGBFromLinear(toneMap(face * uEnvironment.w)), cutBase.a * uSurface.z);
      return;
    }
  }
  vec3 n = normalize(vNormal);
  if (uFlags.y > 0.5) {
    n = normalize(cross(dFdx(vWorld), dFdy(vWorld)));
    if (dot(n, uEye.xyz - vWorld) < 0.0) n = -n;
  } else if (uFlags.z > 0.5 && !gl_FrontFacing) {
    n = -n;
  }
  vec4 base = uBaseColor;
  int bandCount = int(uSurface.w);
  if (bandCount > 0) {
    int band = clamp(int(floor((1.0 - vUv.y) * float(bandCount))), 0, bandCount - 1);
    base.rgb *= uBands[band].rgb;
  }
  float metalness = uSurface.y;
  vec3 geometryNormal = normalize(vNormal);
  vec3 variation = max(abs(dFdx(geometryNormal)), abs(dFdy(geometryNormal)));
  float roughness = min(max(uSurface.x, 0.045) + max(max(variation.x, variation.y), variation.z), 1.0);
  vec3 diffuseColor = base.rgb * (1.0 - metalness);
  vec3 f0 = mix(vec3(0.04), base.rgb, metalness);
  vec3 v = normalize(uEye.xyz - vWorld);
  float nv = saturate(dot(n, v));
  float visibility = shadowVisibility(vWorld, n, uShadow.w * 0.6);
  if (uRim.w > 1.5) { fragColor = vec4(ambientOcclusion, ambientOcclusion, ambientOcclusion, 1.0); return; }
  if (uRim.w > 0.5) { fragColor = vec4(visibility, visibility, visibility, 1.0); return; }
  if (uCoat.w > 0.5) visibility = 1.0;
  float nlKey = saturate(dot(n, uKey.xyz)), nlRim = saturate(dot(n, uRim.xyz));
  float keyShade = mix(0.55, 1.0, visibility) * mix(1.0, ambientOcclusion, 0.3);
  vec3 color = uKeyColor.rgb * nlKey * keyShade * (diffuseColor * INV_PI + specularGGX(uKey.xyz, v, n, f0, roughness));
  color += uRimColor.rgb * nlRim * (diffuseColor * INV_PI + specularGGX(uRim.xyz, v, n, f0, roughness));
  float environmentStrength = uEnvironment.z;
  vec3 r = reflect(-v, n);
  const float maxMip = 6.0;
  vec3 prefiltered = textureLod(uEnvironmentMap, turnIntoStudio(r), roughness * maxMip).rgb;
  vec3 ambient = textureLod(uIrradianceMap, turnIntoStudio(n), 0.0).rgb;
  float occ = mix(0.6, 1.0, visibility) * mix(1.0, ambientOcclusion, 0.75);
  color += (ambient * diffuseColor * 0.72 * mix(0.6, 1.0, visibility) * ambientOcclusion
            + prefiltered * environmentBRDF(f0, roughness, nv) * occ) * environmentStrength;
  float sheen = uCoat.z;
  if (sheen > 0.0) color += sheen * mix(base.rgb, vec3(1.0), 0.5) * pow(1.0 - nv, 3.0) * 0.5 * environmentStrength;
  float coat = uCoat.x;
  if (coat > 0.0) {
    float coatRoughness = max(uCoat.y, 0.045);
    float fresnel = F_Schlick(vec3(0.04), nv).x;
    vec3 coatSpecular = uKeyColor.rgb * nlKey * keyShade * specularGGX(uKey.xyz, v, n, vec3(0.04), coatRoughness)
      + textureLod(uEnvironmentMap, turnIntoStudio(r), coatRoughness * maxMip).rgb
        * environmentBRDF(vec3(0.04), coatRoughness, nv) * environmentStrength * occ;
    color = color * (1.0 - coat * fresnel) + coat * coatSpecular;
  }
  float glow = max(uEmissive.r, max(uEmissive.g, uEmissive.b));
  if (glow > 0.0) {
    vec3 lamp = uEmissive.rgb / glow * min(glow, 0.9);
    color = max(color * (1.0 - saturate(glow)), lamp) + lamp * pow(nv, 3.0) * 0.18;
  }
  float alpha = base.a * uSurface.z;
  if (uCoat.w > 0.5) {
    float fresnel = F_Schlick(vec3(0.04), nv).x;
    vec3 reflection = prefiltered * environmentStrength;
    color = mix(color, reflection, fresnel);
    float highlight = dot(color, vec3(0.2126, 0.7152, 0.0722));
    alpha = clamp(max(mix(alpha, 1.0, fresnel), saturate(highlight - 0.75) * 0.8), 0.0, 1.0);
  }
  color = glow > 0.0 ? mix(toneMap(color * uEnvironment.w), min(color, vec3(1.0)), saturate(glow)) : toneMap(color * uEnvironment.w);
  fragColor = vec4(sRGBFromLinear(color), alpha);
}`;

  const ID_FRAG = `#version 300 es
precision highp float;
in vec3 vWorld;
in vec3 vNormal;
in vec2 vUv;
uniform uint uId;
uniform vec4 uCut;
uniform vec4 uFlags;
out uint fragId;
void main() {
  if (dot(uCut.xyz, uCut.xyz) > 0.25) {
    if (dot(vWorld, uCut.xyz) > uCut.w) discard;
    if (!gl_FrontFacing && uFlags.z < 0.5) { fragId = uId | 0x80000000u; return; }
  }
  fragId = uId;
}`;

  const DISTANCE_FRAG = `#version 300 es
precision highp float;
in vec3 vWorld;
in vec3 vNormal;
in vec2 vUv;
uniform vec3 uEye;
uniform vec3 uForward;
uniform vec4 uCut;
out vec4 fragColor;
vec3 packDepth(float d) {
  float v = clamp(d / 128.0, 0.0, 1.0) * 16777215.0;
  float r = floor(v / 65536.0);
  float g = floor(mod(v / 256.0, 256.0));
  float b = mod(v, 256.0);
  return vec3(r, g, b) / 255.0;
}
void main() {
  if (dot(uCut.xyz, uCut.xyz) > 0.25 && dot(vWorld, uCut.xyz) > uCut.w) discard;
  float d = dot(vWorld - uEye, uForward);
  fragColor = vec4(packDepth(d), 1.0);
}`;

  const AO_FRAG = `#version 300 es
precision highp float;
uniform sampler2D uDistance;
uniform vec2 uHalfSize;
uniform vec3 uEye;
uniform vec3 uForward;
uniform vec3 uRight;
uniform vec3 uUp;
uniform float uTanHalf;
uniform float uAspect;
uniform float uReach;
uniform float uStrength;
out vec4 fragColor;
float saturate(float v) { return clamp(v, 0.0, 1.0); }
float decodeDistance(vec4 t) {
  return (t.r * 255.0 * 65536.0 + t.g * 255.0 * 256.0 + t.b * 255.0) / 16777215.0 * 128.0;
}
vec3 packDepth(float d) {
  float v = clamp(d / 128.0, 0.0, 1.0) * 16777215.0;
  return vec3(floor(v / 65536.0), floor(mod(v / 256.0, 256.0)), mod(v, 256.0)) / 255.0;
}
vec3 pointAt(ivec2 p, float depth) {
  vec2 ndc = (vec2(p) + 0.5) / uHalfSize * 2.0 - 1.0;
  vec3 dir = normalize(uRight * (ndc.x * uTanHalf * uAspect) + uUp * (ndc.y * uTanHalf) - uForward);
  return uEye + dir * depth;
}
void main() {
  ivec2 size = ivec2(uHalfSize);
  ivec2 p = ivec2(gl_FragCoord.xy);
  float d = decodeDistance(texelFetch(uDistance, p, 0));
  if (d <= 0.0) { fragColor = vec4(0.0, 0.0, 0.0, 1.0); return; }
  vec3 P = pointAt(p, d);
  ivec2 x1 = min(p + ivec2(1, 0), size - 1), x0 = max(p - ivec2(1, 0), ivec2(0));
  ivec2 y1 = min(p + ivec2(0, 1), size - 1), y0 = max(p - ivec2(0, 1), ivec2(0));
  float dx1 = decodeDistance(texelFetch(uDistance, x1, 0));
  float dx0 = decodeDistance(texelFetch(uDistance, x0, 0));
  float dy1 = decodeDistance(texelFetch(uDistance, y1, 0));
  float dy0 = decodeDistance(texelFetch(uDistance, y0, 0));
  vec3 X1 = dx1 > 0.0 ? pointAt(x1, dx1) - P : vec3(1e9);
  vec3 X0 = dx0 > 0.0 ? P - pointAt(x0, dx0) : vec3(1e9);
  vec3 Y1 = dy1 > 0.0 ? pointAt(y1, dy1) - P : vec3(1e9);
  vec3 Y0 = dy0 > 0.0 ? P - pointAt(y0, dy0) : vec3(1e9);
  vec3 X = length(X1) < length(X0) ? X1 : X0;
  vec3 Y = length(Y1) < length(Y0) ? Y1 : Y0;
  if (length(X) > 1e8 || length(Y) > 1e8) { fragColor = vec4(packDepth(d), 1.0); return; }
  vec3 N = normalize(cross(X, Y));
  if (dot(N, uEye - P) < 0.0) N = -N;
  float reach = max(uReach, 1e-5);
  float pixel = d * (2.0 * uTanHalf / uHalfSize.y);
  float reachPixels = clamp(reach / max(pixel, 1e-7), 2.0, 36.0);
  const int pattern[16] = int[16](0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5);
  float turn = (float(pattern[(p.y & 3) * 4 + (p.x & 3)]) + 0.5) / 16.0;
  float angle = turn * 6.2831853;
  float occ = 0.0;
  const int taps = 12;
  for (int k = 0; k < taps; k++) {
    float t = (float(k) + fract(turn * 7.0 + 0.5)) / float(taps);
    float a = angle + float(k) * 2.3999632;
    ivec2 q = clamp(p + ivec2(round(vec2(cos(a), sin(a)) * reachPixels * t)), ivec2(0), size - 1);
    float dq = decodeDistance(texelFetch(uDistance, q, 0));
    if (dq <= 0.0) continue;
    vec3 v = pointAt(q, dq) - P;
    float vv = dot(v, v);
    float falloff = max(0.0, 1.0 - vv / (reach * reach));
    occ += falloff * max(0.0, dot(v, N) - 0.03 * reach) / (vv + 0.02 * reach * reach) * reach;
  }
  float ao = saturate(1.0 - uStrength * occ / float(taps));
  fragColor = vec4(packDepth(d), ao);
}`;

  const BLUR_FRAG = `#version 300 es
precision highp float;
uniform sampler2D uRaw;
uniform sampler2D uDistance;
uniform vec2 uHalfSize;
uniform vec3 uEye;
uniform vec3 uForward;
uniform vec3 uRight;
uniform vec3 uUp;
uniform float uTanHalf;
uniform float uAspect;
uniform float uReach;
out vec4 fragColor;
float saturate(float v) { return clamp(v, 0.0, 1.0); }
float decodeDistance(vec4 t) {
  return (t.r * 255.0 * 65536.0 + t.g * 255.0 * 256.0 + t.b * 255.0) / 16777215.0 * 128.0;
}
vec3 packDepth(float d) {
  float v = clamp(d / 128.0, 0.0, 1.0) * 16777215.0;
  return vec3(floor(v / 65536.0), floor(mod(v / 256.0, 256.0)), mod(v, 256.0)) / 255.0;
}
vec3 pointAt(ivec2 p, float depth) {
  vec2 ndc = (vec2(p) + 0.5) / uHalfSize * 2.0 - 1.0;
  vec3 dir = normalize(uRight * (ndc.x * uTanHalf * uAspect) + uUp * (ndc.y * uTanHalf) - uForward);
  return uEye + dir * depth;
}
void main() {
  ivec2 size = ivec2(uHalfSize);
  ivec2 p = ivec2(gl_FragCoord.xy);
  float d = decodeDistance(texelFetch(uDistance, p, 0));
  if (d <= 0.0) { fragColor = vec4(0.0, 0.0, 0.0, 1.0); return; }
  vec3 P = pointAt(p, d);
  float nearReach = max(uReach, 1e-5) * 0.25;
  float sum = 0.0, weight = 0.0;
  for (int y = -2; y <= 1; y++) for (int x = -2; x <= 1; x++) {
    ivec2 q = clamp(p + ivec2(x, y), ivec2(0), size - 1);
    float dq = decodeDistance(texelFetch(uDistance, q, 0));
    if (dq <= 0.0) continue;
    float wq = saturate(1.0 - length(pointAt(q, dq) - P) / nearReach);
    sum += texelFetch(uRaw, q, 0).a * wq;
    weight += wq;
  }
  float ao = weight > 0.0 ? sum / weight : texelFetch(uRaw, p, 0).a;
  fragColor = vec4(packDepth(d), ao);
}`;

  const GROUND_VERT = `#version 300 es
precision highp float;
uniform mat4 uViewProjection;
uniform vec4 uGround;
out vec3 vWorld;
void main() {
  int id = gl_VertexID;
  vec2 corner = vec2((id & 1) == 1 ? 1.0 : -1.0, (id >> 1) == 1 ? 1.0 : -1.0);
  vec3 world = vec3(uGround.y + corner.x * uGround.w, uGround.x, uGround.z + corner.y * uGround.w);
  vWorld = world;
  gl_Position = uViewProjection * vec4(world, 1.0);
}`;

  const GROUND_FRAG = `#version 300 es
precision highp float;
in vec3 vWorld;
uniform sampler2D uShadowMap;
uniform mat4 uLightViewProjection;
uniform vec4 uShadow;
uniform vec4 uGround;
uniform vec4 uGroundColor;
uniform vec4 uKey;
out vec4 fragColor;
vec3 sRGBFromLinear(vec3 value) {
  vec3 v = max(value, 0.0);
  vec3 curved = pow(v, vec3(0.41666)) * 1.055 - 0.055;
  return mix(curved, value * 12.92, step(value, vec3(0.0031308)));
}
const vec2 SHADOW_DISK[12] = vec2[12](
  vec2(-0.326, -0.406), vec2(-0.840, -0.074), vec2(-0.696, 0.457), vec2(-0.203, 0.621),
  vec2(0.962, -0.195), vec2(0.473, -0.480), vec2(0.519, 0.767), vec2(0.185, -0.893),
  vec2(0.507, 0.064), vec2(0.896, 0.412), vec2(-0.322, -0.933), vec2(-0.792, -0.598)
);
void main() {
  vec4 clip = uLightViewProjection * vec4(vWorld + vec3(0.0, uShadow.z, 0.0), 1.0);
  vec3 ndc = clip.xyz / clip.w;
  vec2 uv = vec2(ndc.x * 0.5 + 0.5, ndc.y * 0.5 + 0.5);
  if (any(lessThan(uv, vec2(0.0))) || any(greaterThan(uv, vec2(1.0))) || ndc.z > 1.0) discard;
  float reference = ndc.z * 0.5 + 0.5 - uShadow.y;
  float radius = uGround.w / 1.9;
  float shade = 0.0;
  for (int k = 0; k < 12; k++) {
    float depth = texture(uShadowMap, uv + SHADOW_DISK[k] * uShadow.x * uShadow.w * 2.0).r;
    if (depth < reference) {
      float height = (reference - depth) * uKey.w;
      shade += 1.0 - smoothstep(radius * 0.05, radius * 0.7, height);
    }
  }
  shade /= 12.0;
  float distanceOut = length(vWorld.xz - vec2(uGround.y, uGround.z)) / uGround.w;
  float fade = 1.0 - smoothstep(0.55, 1.0, distanceOut);
  if (uGroundColor.a < 0.0) { fragColor = vec4(vec3(shade), 1.0); return; }
  fragColor = vec4(sRGBFromLinear(uGroundColor.rgb), shade * uGroundColor.a * fade);
}`;

  const SHADOW_FRAG = `#version 300 es
precision highp float;
in vec3 vWorld;
uniform vec4 uCut;
void main() {
  if (dot(uCut.xyz, uCut.xyz) > 0.25 && dot(vWorld, uCut.xyz) > uCut.w) discard;
}`;

  const COMPOSITE_FRAG = `#version 300 es
precision highp float;
precision highp usampler2D;
uniform sampler2D uScene;
uniform usampler2D uOpaqueIds;
uniform usampler2D uClearIds;
uniform vec2 uTargetSize;
uniform vec4 uInkColor;
uniform float uHalfWidth;
uniform float uSeamHalfWidth;
uniform float uSeamStrength;
uniform float uSeamShade;
uniform float uReach;
uniform int uNeighbourCount;
uniform int uReadsClear;
uniform int uDebug;
uniform vec4 uNeighbours[80];
out vec4 fragColor;
vec2 nearestEdges(ivec2 p) {
  ivec2 size = textureSize(uOpaqueIds, 0);
  uint a = texelFetch(uOpaqueIds, p, 0).r;
  uint b = uReadsClear != 0 ? texelFetch(uClearIds, p, 0).r : 0u;
  vec2 nearest = vec2(1e9);
  for (int i = 0; i < 80; i++) {
    if (i >= uNeighbourCount) break;
    vec4 neighbour = uNeighbours[i];
    if (neighbour.z > uReach) break;
    ivec2 q = clamp(p + ivec2(neighbour.xy), ivec2(0), size - 1);
    uint qa = texelFetch(uOpaqueIds, q, 0).r;
    uint qb = uReadsClear != 0 ? texelFetch(uClearIds, q, 0).r : 0u;
    if (qa != a || qb != b) {
      bool silhouette = (qa == 0u) != (a == 0u);
      if (silhouette) nearest.x = min(nearest.x, neighbour.z);
      else nearest.y = min(nearest.y, neighbour.z);
    }
  }
  return nearest;
}
void main() {
  ivec2 p = ivec2(gl_FragCoord.xy);
  if (uDebug == 1) {
    float id = float(texelFetch(uOpaqueIds, p, 0).r);
    fragColor = vec4(vec3(mod(id, 7.0) / 6.0), 1.0);
    return;
  }
  vec2 nearest = nearestEdges(p);
  if (uDebug == 2) {
    fragColor = vec4(vec3(1.0 - clamp(nearest.x / 4.0, 0.0, 1.0)), 1.0);
    return;
  }
  if (uDebug == 3) {
    fragColor = vec4(vec3(1.0 - clamp(nearest.y / 4.0, 0.0, 1.0)), 1.0);
    return;
  }
  if (uDebug == 4) {
    fragColor = vec4(texelFetch(uScene, p, 0).rgb, 1.0);
    return;
  }
  vec4 ink = vec4(uInkColor.rgb, uInkColor.a) * clamp(uHalfWidth - nearest.x + 1.0, 0.0, 1.0);
  float shade = 1.0 - uSeamStrength * clamp(uSeamHalfWidth - nearest.y + 1.0, 0.0, 1.0) * (1.0 - uSeamShade);
  vec3 scene = texelFetch(uScene, p, 0).rgb;
  // Premultiplied ink over the scene; the seam multiplies through both.
  fragColor = vec4(scene * (1.0 - ink.a) * shade + ink.rgb * shade, 1.0);
}`;

  const SHOW_FRAG = `#version 300 es
precision highp float;
uniform sampler2D uTex;
uniform vec2 uSize;
uniform int uChannel;
out vec4 fragColor;
void main() {
  vec2 uv = gl_FragCoord.xy / uSize;
  vec4 t = texture(uTex, uv);
  float v = uChannel == 0 ? t.r : t.a;
  fragColor = vec4(vec3(v), 1.0);
}`;

  // ---------------------------------------------------------------- GL helpers
  function compile(gl, type, source) {
    const shader = gl.createShader(type);
    gl.shaderSource(shader, source);
    gl.compileShader(shader);
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
      const log = gl.getShaderInfoLog(shader);
      gl.deleteShader(shader);
      throw new Error('Clicky3D shader: ' + log);
    }
    return shader;
  }
  function program(gl, vert, frag) {
    const p = gl.createProgram();
    const vs = compile(gl, gl.VERTEX_SHADER, vert), fs = compile(gl, gl.FRAGMENT_SHADER, frag);
    gl.attachShader(p, vs); gl.attachShader(p, fs); gl.linkProgram(p);
    gl.deleteShader(vs); gl.deleteShader(fs);
    if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error('Clicky3D link: ' + gl.getProgramInfoLog(p));
    const uniforms = {}, sizes = {};
    const count = gl.getProgramParameter(p, gl.ACTIVE_UNIFORMS);
    for (let i = 0; i < count; i++) {
      const info = gl.getActiveUniform(p, i);
      const name = info.name.replace(/\[0\]$/, '');
      uniforms[name] = gl.getUniformLocation(p, info.name);
      sizes[name] = info.size;
    }
    return { p, u: uniforms, sizes };
  }
  function texture(gl, w, h, internal, format, type, filter) {
    const t = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, t);
    gl.texImage2D(gl.TEXTURE_2D, 0, internal, w, h, 0, format, type, null);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, filter || gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, filter || gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    return t;
  }
  function framebuffer(gl, color, depth) {
    const f = gl.createFramebuffer();
    gl.bindFramebuffer(gl.FRAMEBUFFER, f);
    if (color) gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, color, 0);
    if (depth) gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.DEPTH_ATTACHMENT, gl.TEXTURE_2D, depth, 0);
    return f;
  }

  // Cartesian halves with a polar edge table, exactly the shipped neighbour pattern.
  function edgeNeighbours(reach) {
    const list = [], seen = new Set();
    for (let ring = 1; ring <= 5; ring++) {
      const radius = ((reach + 1) * ring) / 5;
      const steps = Math.ceil(2 * PI * radius);
      for (let step = 0; step < steps; step++) {
        const angle = (step + (ring % 2 ? 0 : 0.5)) * (PI / 8);
        const dx = Math.round(Math.cos(angle) * radius);
        const dy = Math.round(Math.sin(angle) * radius);
        if (dx === 0 && dy === 0) continue;
        const key = dx + ',' + dy;
        if (seen.has(key)) continue;
        seen.add(key);
        list.push([dx, dy, Math.hypot(dx, dy)]);
        if (list.length >= 80) break;
      }
      if (list.length >= 80) break;
    }
    list.sort((a, b) => a[2] - b[2]);
    return list;
  }

  function create(canvas) {
    const gl = canvas.getContext('webgl2', {
      alpha: true,
      antialias: false,
      depth: true,
      stencil: false,
      premultipliedAlpha: false,
      preserveDrawingBuffer: true,
      powerPreference: 'high-performance',
    });
    if (!gl) throw new Error('Clicky3D needs WebGL2');

    const programs = {
      env: program(gl, FULLSCREEN_VERT, ENV_FRAG),
      irr: program(gl, FULLSCREEN_VERT, IRR_FRAG),
      studio: program(gl, OBJECT_VERT, STUDIO_FRAG),
      ids: program(gl, OBJECT_VERT, ID_FRAG),
      distance: program(gl, OBJECT_VERT, DISTANCE_FRAG),
      ao: program(gl, FULLSCREEN_VERT, AO_FRAG),
      blur: program(gl, FULLSCREEN_VERT, BLUR_FRAG),
      ground: program(gl, GROUND_VERT, GROUND_FRAG),
      shadow: program(gl, OBJECT_VERT, SHADOW_FRAG),
      composite: program(gl, FULLSCREEN_VERT, COMPOSITE_FRAG),
      show: program(gl, FULLSCREEN_VERT, SHOW_FRAG),
      probe: program(gl, FULLSCREEN_VERT, `#version 300 es
precision highp float;
out vec4 fragColor;
void main() { fragColor = vec4(0.2, 0.4, 0.6, 1.0); }`),
    };

    // Environment cube: one face/mip at a time, then the irradiance cube.
    const hdr = !!gl.getExtension('EXT_color_buffer_float');
    const envInternal = hdr ? gl.RGBA16F : gl.RGBA8;
    const envType = hdr ? gl.HALF_FLOAT : gl.UNSIGNED_BYTE;
    const envTex = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_CUBE_MAP, envTex);
    for (let level = 0; level < ENV_MIPS; level++) {
      const size = Math.max(1, ENV_SIZE >> level);
      for (let face = 0; face < 6; face++) {
        gl.texImage2D(gl.TEXTURE_CUBE_MAP_POSITIVE_X + face, level, envInternal, size, size, 0, gl.RGBA, envType, null);
      }
    }
    gl.texParameteri(gl.TEXTURE_CUBE_MAP, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR);
    gl.texParameteri(gl.TEXTURE_CUBE_MAP, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_CUBE_MAP, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_CUBE_MAP, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_CUBE_MAP, gl.TEXTURE_MAX_LEVEL, ENV_MIPS - 1);
    const irrTex = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_CUBE_MAP, irrTex);
    for (let face = 0; face < 6; face++) {
      gl.texImage2D(gl.TEXTURE_CUBE_MAP_POSITIVE_X + face, 0, envInternal, IRR_SIZE, IRR_SIZE, 0, gl.RGBA, envType, null);
    }
    gl.texParameteri(gl.TEXTURE_CUBE_MAP, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_CUBE_MAP, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_CUBE_MAP, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_CUBE_MAP, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);

    const bakeFbo = gl.createFramebuffer();
    gl.bindFramebuffer(gl.FRAMEBUFFER, bakeFbo);
    gl.disable(gl.DEPTH_TEST);
    gl.disable(gl.BLEND);
    gl.useProgram(programs.env.p);
    for (let level = 0; level < ENV_MIPS; level++) {
      const size = Math.max(1, ENV_SIZE >> level);
      gl.viewport(0, 0, size, size);
      gl.uniform1i(programs.env.u.uSize, size);
      gl.uniform1i(programs.env.u.uLevel, level);
      gl.uniform1i(programs.env.u.uLevels, ENV_MIPS);
      gl.uniform1f(programs.env.u.uRoom, ROOM_LEVEL);
      for (let face = 0; face < 6; face++) {
        gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_CUBE_MAP_POSITIVE_X + face, envTex, level);
        gl.uniform1i(programs.env.u.uFace, face);
        gl.drawArrays(gl.TRIANGLES, 0, 3);
      }
    }
    gl.useProgram(programs.irr.p);
    gl.viewport(0, 0, IRR_SIZE, IRR_SIZE);
    gl.uniform1i(programs.irr.u.uSize, IRR_SIZE);
    gl.uniform1f(programs.irr.u.uRoom, ROOM_LEVEL);
    for (let face = 0; face < 6; face++) {
      gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_CUBE_MAP_POSITIVE_X + face, irrTex, 0);
      gl.uniform1i(programs.irr.u.uFace, face);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
    }
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);

    const shadowTex = texture(gl, SHADOW_SIZE, SHADOW_SIZE, gl.DEPTH_COMPONENT24, gl.DEPTH_COMPONENT, gl.UNSIGNED_INT, gl.NEAREST);
    const shadowFbo = framebuffer(gl, null, shadowTex);
    gl.bindFramebuffer(gl.FRAMEBUFFER, shadowFbo);
    gl.drawBuffers([gl.NONE]);
    {
      const status = gl.checkFramebufferStatus(gl.FRAMEBUFFER);
      if (status !== gl.FRAMEBUFFER_COMPLETE) throw new Error('Clicky3D shadow target: 0x' + status.toString(16));
    }
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);

    const emptyVao = gl.createVertexArray();
    const probeVao = gl.createVertexArray();
    const geoCache = new Map();
    const samples = gl.getParameter(gl.MAX_SAMPLES);
    const msaaCount = Math.min(4, samples || 0);

    let width = 1, height = 1, dpr = 1;
    const targets = {};

    function disposeTargets() {
      const kill = value => {
        if (!value) return;
        if (value.fbo) gl.deleteFramebuffer(value.fbo);
        if (value.tex) gl.deleteTexture(value.tex);
        if (value.rb || value.colorRb) gl.deleteRenderbuffer(value.rb || value.colorRb);
        if (value.depthRb) gl.deleteRenderbuffer(value.depthRb);
      };
      for (const key of Object.keys(targets)) {
        if (key === 'msaa') kill(targets.msaa);
        else kill(targets[key]);
        delete targets[key];
      }
    }

    function complete(name) {
      const status = gl.checkFramebufferStatus(gl.FRAMEBUFFER);
      if (status !== gl.FRAMEBUFFER_COMPLETE) throw new Error('Clicky3D ' + name + ' target: 0x' + status.toString(16));
    }

    function makeTargets(w, h) {
      disposeTargets();
      const fullW = Math.max(1, Math.round(w * dpr)), fullH = Math.max(1, Math.round(h * dpr));
      const halfW = Math.max(1, Math.ceil(fullW / 2)), halfH = Math.max(1, Math.ceil(fullH / 2));
      width = fullW; height = fullH;

      const sceneTex = texture(gl, fullW, fullH, gl.RGBA8, gl.RGBA, gl.UNSIGNED_BYTE, gl.LINEAR);
      const sceneFbo = framebuffer(gl, sceneTex, null);
      complete('scene');

      const idsTex = texture(gl, fullW, fullH, gl.R32UI, gl.RED_INTEGER, gl.UNSIGNED_INT, gl.NEAREST);
      const clearTex = texture(gl, fullW, fullH, gl.R32UI, gl.RED_INTEGER, gl.UNSIGNED_INT, gl.NEAREST);
      const idDepth = gl.createRenderbuffer();
      gl.bindRenderbuffer(gl.RENDERBUFFER, idDepth);
      gl.renderbufferStorage(gl.RENDERBUFFER, gl.DEPTH_COMPONENT24, fullW, fullH);
      const idFbo = gl.createFramebuffer();
      gl.bindFramebuffer(gl.FRAMEBUFFER, idFbo);
      gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, idsTex, 0);
      gl.framebufferRenderbuffer(gl.FRAMEBUFFER, gl.DEPTH_ATTACHMENT, gl.RENDERBUFFER, idDepth);
      complete('id');
      const clearFbo = gl.createFramebuffer();
      gl.bindFramebuffer(gl.FRAMEBUFFER, clearFbo);
      gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, clearTex, 0);
      gl.framebufferRenderbuffer(gl.FRAMEBUFFER, gl.DEPTH_ATTACHMENT, gl.RENDERBUFFER, idDepth);
      complete('clear');

      const distanceTex = texture(gl, halfW, halfH, gl.RGBA8, gl.RGBA, gl.UNSIGNED_BYTE, gl.NEAREST);
      const aoTex = texture(gl, halfW, halfH, gl.RGBA8, gl.RGBA, gl.UNSIGNED_BYTE, gl.NEAREST);
      const blurTex = texture(gl, halfW, halfH, gl.RGBA8, gl.RGBA, gl.UNSIGNED_BYTE, gl.NEAREST);
      const distanceFbo = framebuffer(gl, distanceTex, null);
      const distanceDepth = gl.createRenderbuffer();
      gl.bindRenderbuffer(gl.RENDERBUFFER, distanceDepth);
      gl.renderbufferStorage(gl.RENDERBUFFER, gl.DEPTH_COMPONENT24, halfW, halfH);
      gl.bindFramebuffer(gl.FRAMEBUFFER, distanceFbo);
      gl.framebufferRenderbuffer(gl.FRAMEBUFFER, gl.DEPTH_ATTACHMENT, gl.RENDERBUFFER, distanceDepth);
      complete('distance');
      const aoFbo = framebuffer(gl, aoTex, null);
      complete('ao');
      const blurFbo = framebuffer(gl, blurTex, null);
      complete('blur');
      gl.bindFramebuffer(gl.FRAMEBUFFER, null);

      let msaa = null;
      if (msaaCount >= 2) {
        const colorRb = gl.createRenderbuffer();
        gl.bindRenderbuffer(gl.RENDERBUFFER, colorRb);
        gl.renderbufferStorageMultisample(gl.RENDERBUFFER, msaaCount, gl.RGBA8, fullW, fullH);
        const depthRb = gl.createRenderbuffer();
        gl.bindRenderbuffer(gl.RENDERBUFFER, depthRb);
        gl.renderbufferStorageMultisample(gl.RENDERBUFFER, msaaCount, gl.DEPTH_COMPONENT24, fullW, fullH);
        const fbo = gl.createFramebuffer();
        gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);
        gl.framebufferRenderbuffer(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.RENDERBUFFER, colorRb);
        gl.framebufferRenderbuffer(gl.FRAMEBUFFER, gl.DEPTH_ATTACHMENT, gl.RENDERBUFFER, depthRb);
        const completeStatus = gl.checkFramebufferStatus(gl.FRAMEBUFFER) === gl.FRAMEBUFFER_COMPLETE;
        // Some ANGLE/D3D11 builds report a complete multisample target yet resolve only
        // the edge pixels, leaving covered interiors at the clear colour. Prove the
        // resolve with a full-screen triangle before trusting MSAA.
        let resolves = false;
        if (completeStatus) {
          gl.viewport(0, 0, fullW, fullH);
          gl.disable(gl.DEPTH_TEST); gl.disable(gl.BLEND); gl.disable(gl.CULL_FACE);
          gl.useProgram(programs.probe.p);
          gl.bindVertexArray(probeVao);
          gl.drawArrays(gl.TRIANGLES, 0, 3);
          gl.bindFramebuffer(gl.READ_FRAMEBUFFER, fbo);
          gl.bindFramebuffer(gl.DRAW_FRAMEBUFFER, sceneFbo);
          gl.blitFramebuffer(0, 0, fullW, fullH, 0, 0, fullW, fullH, gl.COLOR_BUFFER_BIT, gl.NEAREST);
          gl.bindFramebuffer(gl.FRAMEBUFFER, sceneFbo);
          const probe = new Uint8Array(4);
          gl.readPixels(fullW >> 1, fullH >> 1, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, probe);
          resolves = Math.abs(probe[0] - 51) <= 3 && Math.abs(probe[1] - 102) <= 3 && Math.abs(probe[2] - 153) <= 3;
          gl.bindVertexArray(null);
        }
        gl.bindFramebuffer(gl.FRAMEBUFFER, null);
        if (completeStatus && resolves) msaa = { fbo, colorRb, depthRb };
        else { gl.deleteFramebuffer(fbo); gl.deleteRenderbuffer(colorRb); gl.deleteRenderbuffer(depthRb); }
      }

      Object.assign(targets, {
        sceneTex, sceneFbo, idsTex, clearTex, idDepth, idFbo, clearFbo,
        distanceTex, aoTex, blurTex, distanceFbo, distanceDepth, aoFbo, blurFbo,
        halfW, halfH, msaa,
      });
    }

    function upload(geometry) {
      let record = geoCache.get(geometry);
      if (record) return record;
      const vao = gl.createVertexArray();
      gl.bindVertexArray(vao);
      const buffers = [];
      const attach = (data, location, size) => {
        const buffer = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
        gl.bufferData(gl.ARRAY_BUFFER, data, gl.STATIC_DRAW);
        gl.enableVertexAttribArray(location);
        gl.vertexAttribPointer(location, size, gl.FLOAT, false, 0, 0);
        buffers.push(buffer);
      };
      attach(geometry.positions, 0, 3);
      attach(geometry.normals, 1, 3);
      attach(geometry.uvs, 2, 2);
      const index = gl.createBuffer();
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, index);
      gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, geometry.indices, gl.STATIC_DRAW);
      gl.bindVertexArray(null);
      record = { vao, index, count: geometry.indices.length };
      geoCache.set(geometry, record);
      return record;
    }

    function bindFullscreen() {
      gl.bindVertexArray(emptyVao);
    }

    const scratch4 = new Float32Array(4);
    function upload4(location, value) {
      if (!location) return;
      if (value && value.length === 4) { gl.uniform4fv(location, value); return; }
      scratch4[0] = (value && value[0]) || 0;
      scratch4[1] = (value && value[1]) || 0;
      scratch4[2] = (value && value[2]) || 0;
      scratch4[3] = (value && value[3]) || 0;
      gl.uniform4fv(location, scratch4);
    }

    function setFrameUniforms(p, frame, camera) {
      gl.uniformMatrix4fv(p.u.uViewProjection, false, camera.viewProjection);
      gl.uniformMatrix4fv(p.u.uLightViewProjection, false, camera.lightViewProjection);
      gl.uniform4f(p.u.uEye, camera.eye[0], camera.eye[1], camera.eye[2], 0);
      gl.uniform4f(p.u.uViewForward, camera.forward[0], camera.forward[1], camera.forward[2], 0);
      gl.uniform4f(p.u.uKey, KEY_DIR[0], KEY_DIR[1], KEY_DIR[2], camera.keyScale);
      gl.uniform4f(p.u.uKeyColor, KEY_COLOR[0] * KEY_INTENSITY, KEY_COLOR[1] * KEY_INTENSITY, KEY_COLOR[2] * KEY_INTENSITY, 1);
      gl.uniform4f(p.u.uRim, RIM_DIR[0], RIM_DIR[1], RIM_DIR[2], frame.debug === 4 ? 1 : 0);
      gl.uniform4f(p.u.uRimColor, RIM_COLOR[0] * RIM_INTENSITY, RIM_COLOR[1] * RIM_INTENSITY, RIM_COLOR[2] * RIM_INTENSITY, 1);
      gl.uniform4f(p.u.uEnvironment, Math.cos(camera.yaw), Math.sin(camera.yaw), ENV_INTENSITY, EXPOSURE);
      gl.uniform4f(p.u.uShadow, 1 / SHADOW_SIZE, 0.0015, 0.004 * frame.extent, 1.6);
      gl.uniform4f(p.u.uOcclusion, 0.2 * frame.extent, 2.2, 1.0, 0.0);
      gl.uniform4f(p.u.uGrade, 1.0, LOOK_POWER, LOOK_SATURATION, 0.0);
      gl.uniform4f(p.u.uCutHatch, camera.hatchSpacing, 0, 0, 0);
      gl.uniform3f(p.u.uShadowDirection, SHADOW_DIR[0], SHADOW_DIR[1], SHADOW_DIR[2]);
    }

    function drawObject(p, object, camera, useProgramIsStudio) {
      const geo = upload(object.geometry);
      gl.bindVertexArray(geo.vao);
      gl.uniformMatrix4fv(p.u.uModel, false, object.model);
      if (p.u.uNormalMatrix) gl.uniformMatrix3fv(p.u.uNormalMatrix, false, object.normal);
      if (useProgramIsStudio) {
        upload4(p.u.uBaseColor, object.base);
        upload4(p.u.uEmissive, object.emissive);
        upload4(p.u.uSurface, object.surface);
        upload4(p.u.uCoat, object.coat);
        upload4(p.u.uFlags, object.flags);
        upload4(p.u.uCut, object.cut);
        const bands = p.sizes.uBands || 16;
        if (p.u.uBands) gl.uniform4fv(p.u.uBands, object.bandData.length === bands * 4 ? object.bandData : object.bandData.subarray(0, bands * 4));
      } else {
        upload4(p.u.uCut, object.cut);
        upload4(p.u.uFlags, object.flags);
      }
      if (p.u.uId) gl.uniform1ui(p.u.uId, object.id);
      gl.frontFace(object.flip ? gl.CW : gl.CCW);
      if (object.doubleSided) gl.disable(gl.CULL_FACE); else gl.enable(gl.CULL_FACE);
      gl.drawElements(gl.TRIANGLES, geo.count, gl.UNSIGNED_INT, 0);
    }

    function makeCamera(frame) {
      const c = frame.camera;
      const eye = c.eye;
      const view = lookAt(eye, c.target, [0, 1, 0]);
      const proj = perspective(c.fov, width / height, 0.1, 100);
      const viewProjection = mul(proj, view);
      const forward = norm([c.target[0] - eye[0], c.target[1] - eye[1], c.target[2] - eye[2]]);
      const right = norm(cross(forward, [0, 1, 0]));
      const up = cross(right, forward);
      const lightDistance = 3 * frame.extent + 4;
      const lightEye = [
        frame.center[0] + SHADOW_DIR[0] * lightDistance,
        frame.center[1] + SHADOW_DIR[1] * lightDistance,
        frame.center[2] + SHADOW_DIR[2] * lightDistance,
      ];
      const lightUp = Math.abs(SHADOW_DIR[1]) > 0.9 ? [0, 0, 1] : [0, 1, 0];
      const lightView = lookAt(lightEye, frame.center, lightUp);
      const radius = frame.extent * 1.7;
      const lightProj = ortho(-radius, radius, -radius, radius, 0.1, lightDistance * 2);
      const lightViewProjection = mul(lightProj, lightView);
      const worldPerPixel = (2 * c.distance * Math.tan((c.fov * PI) / 360)) / height;
      const hatchSpacing = 9 * Math.max(1, width / 1600) * worldPerPixel;
      return {
        eye, target: c.target, forward, right, up, viewProjection, lightViewProjection,
        yaw: c.yaw, keyScale: lightDistance * 2 - 0.1, hatchSpacing,
        tanHalf: Math.tan((c.fov * PI) / 360), aspect: width / height,
      };
    }

    function drawFrame(frame) {
      if (!frame || !frame.objects) return;
      const camera = makeCamera(frame);
      const objects = frame.objects;
      const halfW = targets.halfW, halfH = targets.halfH;

      // Shadow map.
      gl.bindFramebuffer(gl.FRAMEBUFFER, shadowFbo);
      gl.viewport(0, 0, SHADOW_SIZE, SHADOW_SIZE);
      gl.clear(gl.DEPTH_BUFFER_BIT);
      gl.enable(gl.DEPTH_TEST); gl.depthFunc(gl.LEQUAL); gl.depthMask(true);
      gl.disable(gl.BLEND); gl.disable(gl.CULL_FACE);
      gl.useProgram(programs.shadow.p);
      gl.uniformMatrix4fv(programs.shadow.u.uViewProjection, false, camera.lightViewProjection);
      for (const object of objects) {
        const geo = upload(object.geometry);
        gl.bindVertexArray(geo.vao);
        gl.uniformMatrix4fv(programs.shadow.u.uModel, false, object.model);
        gl.uniform4fv(programs.shadow.u.uCut, object.cut);
        gl.frontFace(object.flip ? gl.CW : gl.CCW);
        gl.drawElements(gl.TRIANGLES, geo.count, gl.UNSIGNED_INT, 0);
      }

      // Half-res linear distance.
      gl.bindFramebuffer(gl.FRAMEBUFFER, targets.distanceFbo);
      gl.viewport(0, 0, halfW, halfH);
      gl.clearColor(0, 0, 0, 1);
      gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
      gl.useProgram(programs.distance.p);
      gl.uniformMatrix4fv(programs.distance.u.uViewProjection, false, camera.viewProjection);
      gl.uniform3f(programs.distance.u.uEye, camera.eye[0], camera.eye[1], camera.eye[2]);
      gl.uniform3f(programs.distance.u.uForward, camera.forward[0], camera.forward[1], camera.forward[2]);
      for (const object of objects) {
        const geo = upload(object.geometry);
        gl.bindVertexArray(geo.vao);
        gl.uniformMatrix4fv(programs.distance.u.uModel, false, object.model);
        gl.uniform4fv(programs.distance.u.uCut, object.cut);
        gl.frontFace(object.flip ? gl.CW : gl.CCW);
        gl.disable(gl.CULL_FACE);
        gl.drawElements(gl.TRIANGLES, geo.count, gl.UNSIGNED_INT, 0);
      }

      // AO and its bilateral blur.
      gl.disable(gl.DEPTH_TEST); gl.depthMask(false); gl.disable(gl.BLEND);
      gl.bindFramebuffer(gl.FRAMEBUFFER, targets.aoFbo);
      gl.viewport(0, 0, halfW, halfH);
      gl.useProgram(programs.ao.p);
      gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, targets.distanceTex);
      gl.uniform1i(programs.ao.u.uDistance, 0);
      gl.uniform2f(programs.ao.u.uHalfSize, halfW, halfH);
      gl.uniform3f(programs.ao.u.uEye, camera.eye[0], camera.eye[1], camera.eye[2]);
      gl.uniform3f(programs.ao.u.uForward, camera.forward[0], camera.forward[1], camera.forward[2]);
      gl.uniform3f(programs.ao.u.uRight, camera.right[0], camera.right[1], camera.right[2]);
      gl.uniform3f(programs.ao.u.uUp, camera.up[0], camera.up[1], camera.up[2]);
      gl.uniform1f(programs.ao.u.uTanHalf, camera.tanHalf);
      gl.uniform1f(programs.ao.u.uAspect, camera.aspect);
      gl.uniform1f(programs.ao.u.uReach, 0.2 * frame.extent);
      gl.uniform1f(programs.ao.u.uStrength, 2.2);
      bindFullscreen();
      gl.drawArrays(gl.TRIANGLES, 0, 3);

      gl.bindFramebuffer(gl.FRAMEBUFFER, targets.blurFbo);
      gl.useProgram(programs.blur.p);
      gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, targets.aoTex);
      gl.uniform1i(programs.blur.u.uRaw, 0);
      gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D, targets.distanceTex);
      gl.uniform1i(programs.blur.u.uDistance, 1);
      gl.uniform2f(programs.blur.u.uHalfSize, halfW, halfH);
      gl.uniform3f(programs.blur.u.uEye, camera.eye[0], camera.eye[1], camera.eye[2]);
      gl.uniform3f(programs.blur.u.uForward, camera.forward[0], camera.forward[1], camera.forward[2]);
      gl.uniform3f(programs.blur.u.uRight, camera.right[0], camera.right[1], camera.right[2]);
      gl.uniform3f(programs.blur.u.uUp, camera.up[0], camera.up[1], camera.up[2]);
      gl.uniform1f(programs.blur.u.uTanHalf, camera.tanHalf);
      gl.uniform1f(programs.blur.u.uAspect, camera.aspect);
      gl.uniform1f(programs.blur.u.uReach, 0.2 * frame.extent);
      bindFullscreen();
      gl.drawArrays(gl.TRIANGLES, 0, 3);

      // Studio pass into the MSAA target (or the resolve target when MSAA is unavailable).
      const sceneFbo = targets.msaa ? targets.msaa.fbo : targets.sceneFbo;
      gl.bindFramebuffer(gl.FRAMEBUFFER, sceneFbo);
      gl.viewport(0, 0, width, height);
      gl.clearColor(frame.paper[0], frame.paper[1], frame.paper[2], 1);
      // Clear obeys the depth write mask, so restore it before clearing: the AO pass
      // above leaves depthMask(false), and the MSAA target is the only one with depth.
      gl.depthMask(true);
      gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
      gl.enable(gl.DEPTH_TEST); gl.depthFunc(gl.LEQUAL); gl.depthMask(true);
      gl.enable(gl.CULL_FACE); gl.cullFace(gl.BACK);
      gl.disable(gl.BLEND);

      // Ground first.
      if (frame.ground !== false) {
        gl.useProgram(programs.ground.p);
        setFrameUniforms(programs.ground, frame, camera);
        gl.uniform4f(programs.ground.u.uGround, frame.groundY - 0.004 * frame.extent, frame.center[0], frame.center[2], 1.9 * frame.extent);
        const groundColor = frame.groundColor || [0.055, 0.050, 0.045];
        gl.uniform4f(programs.ground.u.uGroundColor, groundColor[0], groundColor[1], groundColor[2], frame.groundDebug ? -1 : GROUND_OPACITY);
        gl.activeTexture(gl.TEXTURE0);
        gl.bindTexture(gl.TEXTURE_2D, shadowTex);
        gl.uniform1i(programs.ground.u.uShadowMap, 0);
        gl.enable(gl.BLEND);
        gl.blendFuncSeparate(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA, gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
        gl.disable(gl.CULL_FACE);
        bindFullscreen();
        gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
        gl.disable(gl.BLEND);
        gl.enable(gl.CULL_FACE);
      }

      // Opaque objects, front to back.
      gl.useProgram(programs.studio.p);
      setFrameUniforms(programs.studio, frame, camera);
      gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_CUBE_MAP, envTex);
      gl.uniform1i(programs.studio.u.uEnvironmentMap, 0);
      gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_CUBE_MAP, irrTex);
      gl.uniform1i(programs.studio.u.uIrradianceMap, 1);
      gl.activeTexture(gl.TEXTURE2); gl.bindTexture(gl.TEXTURE_2D, shadowTex);
      gl.uniform1i(programs.studio.u.uShadowMap, 2);
      gl.activeTexture(gl.TEXTURE3); gl.bindTexture(gl.TEXTURE_2D, targets.blurTex);
      gl.uniform1i(programs.studio.u.uOcclusionMap, 3);
      gl.activeTexture(gl.TEXTURE4); gl.bindTexture(gl.TEXTURE_2D, targets.distanceTex);
      gl.uniform1i(programs.studio.u.uOcclusionDistances, 4);

      const ordered = objects.filter(o => !o.transparent).sort((a, b) => a.depth - b.depth);
      for (const object of ordered) drawObject(programs.studio, object, camera, true);

      // Transparent objects, back to front.
      const glass = objects.filter(o => o.transparent).sort((a, b) => b.depth - a.depth);
      if (glass.length) {
        gl.enable(gl.BLEND);
        gl.blendFuncSeparate(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA, gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
        gl.depthMask(false);
        for (const object of glass) drawObject(programs.studio, object, camera, true);
        gl.depthMask(true);
        gl.disable(gl.BLEND);
      }

      // Opaque ids, then the ids visible through glass.
      gl.bindFramebuffer(gl.FRAMEBUFFER, targets.idFbo);
      gl.viewport(0, 0, width, height);
      gl.enable(gl.DEPTH_TEST); gl.depthMask(true); gl.disable(gl.BLEND);
      gl.clearBufferuiv(gl.COLOR, 0, [0, 0, 0, 0]);
      gl.clear(gl.DEPTH_BUFFER_BIT);
      gl.useProgram(programs.ids.p);
      gl.uniformMatrix4fv(programs.ids.u.uViewProjection, false, camera.viewProjection);
      // Particles (noInk) stay out of the id buffer, so the ink pass never outlines them.
      for (const object of objects) if (!object.noInk) drawObject(programs.ids, object, camera, false);

      const readsClear = glass.length > 0;
      if (readsClear) {
        gl.bindFramebuffer(gl.FRAMEBUFFER, targets.clearFbo);
        gl.clearBufferuiv(gl.COLOR, 0, [0, 0, 0, 0]);
        gl.clear(gl.DEPTH_BUFFER_BIT);
        gl.useProgram(programs.ids.p);
        gl.uniformMatrix4fv(programs.ids.u.uViewProjection, false, camera.viewProjection);
        for (const object of objects) if (!object.transparent && !object.noInk) drawObject(programs.ids, object, camera, false);
      }

      // Resolve.
      if (targets.msaa) {
        gl.bindFramebuffer(gl.READ_FRAMEBUFFER, targets.msaa.fbo);
        gl.bindFramebuffer(gl.DRAW_FRAMEBUFFER, targets.sceneFbo);
        gl.blitFramebuffer(0, 0, width, height, 0, 0, width, height, gl.COLOR_BUFFER_BIT, gl.NEAREST);
      }

      // Ink in one composite: seams multiply the scene, silhouettes add ink.
      gl.bindFramebuffer(gl.FRAMEBUFFER, null);
      gl.viewport(0, 0, width, height);
      gl.disable(gl.DEPTH_TEST); gl.disable(gl.BLEND); gl.disable(gl.CULL_FACE);
      gl.useProgram(programs.composite.p);
      gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, targets.sceneTex);
      gl.uniform1i(programs.composite.u.uScene, 0);
      gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D, targets.idsTex);
      gl.uniform1i(programs.composite.u.uOpaqueIds, 1);
      gl.activeTexture(gl.TEXTURE2); gl.bindTexture(gl.TEXTURE_2D, targets.clearTex);
      gl.uniform1i(programs.composite.u.uClearIds, 2);
      gl.uniform2f(programs.composite.u.uTargetSize, width, height);
      const ink = frame.ink;
      const halfWidth = Math.max(0.05, ((ink.width === undefined ? 0.9 : ink.width) / 2) * dpr);
      const seamHalf = Math.max(0.05, ((ink.seamWidth === undefined ? 0.6 : ink.seamWidth) / 2) * dpr);
      gl.uniform4f(programs.composite.u.uInkColor, ink.color[0], ink.color[1], ink.color[2], ink.a === undefined ? 1 : ink.a);
      gl.uniform1f(programs.composite.u.uHalfWidth, halfWidth);
      gl.uniform1f(programs.composite.u.uSeamHalfWidth, seamHalf);
      gl.uniform1f(programs.composite.u.uSeamStrength, ink.strength);
      gl.uniform1f(programs.composite.u.uSeamShade, ink.shade);
      gl.uniform1f(programs.composite.u.uReach, Math.max(halfWidth, seamHalf) + 1.5);
      gl.uniform1i(programs.composite.u.uReadsClear, readsClear ? 1 : 0);
      gl.uniform1i(programs.composite.u.uDebug, frame.debug || 0);
      const neighbours = edgeNeighbours(Math.max(halfWidth, seamHalf) + 3);
      const packed = new Float32Array(80 * 4);
      neighbours.forEach((n, i) => { packed[i * 4] = n[0]; packed[i * 4 + 1] = n[1]; packed[i * 4 + 2] = n[2]; });
      gl.uniform1i(programs.composite.u.uNeighbourCount, neighbours.length);
      const neighbourSize = programs.composite.sizes.uNeighbours || 80;
      gl.uniform4fv(programs.composite.u.uNeighbours, packed.subarray(0, neighbourSize * 4));
      bindFullscreen();
      gl.drawArrays(gl.TRIANGLES, 0, 3);

      if (frame.debug >= 5) {
        const pick = frame.debug === 5 ? shadowTex : frame.debug === 6 ? targets.blurTex : targets.distanceTex;
        gl.useProgram(programs.show.p);
        gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, pick);
        gl.uniform1i(programs.show.u.uTex, 0);
        gl.uniform2f(programs.show.u.uSize, width, height);
        gl.uniform1i(programs.show.u.uChannel, frame.debug === 6 ? 1 : 0);
        bindFullscreen();
        gl.drawArrays(gl.TRIANGLES, 0, 3);
      }
    }

    return {
      canvas,
      gl,
      setSize(cssWidth, cssHeight, devicePixelRatio) {
        const nextDpr = Math.max(1, Math.min(3, devicePixelRatio || 1));
        const w = Math.max(80, Math.round(cssWidth)), h = Math.max(80, Math.round(cssHeight));
        const pxW = Math.round(w * nextDpr), pxH = Math.round(h * nextDpr);
        if (canvas.width !== pxW) canvas.width = pxW;
        if (canvas.height !== pxH) canvas.height = pxH;
        if (targets.sceneTex && dpr === nextDpr && width === pxW && height === pxH) return;
        dpr = nextDpr;
        makeTargets(w, h);
      },
      render(frame) { drawFrame(frame); },
      debugUniforms() {
        const out = {};
        for (const name of Object.keys(programs)) out[name] = { ...programs[name].sizes };
        return out;
      },
      probeIds() {
        const counts = {};
        gl.bindFramebuffer(gl.FRAMEBUFFER, targets.idFbo);
        const pixel = new Uint32Array(1);
        for (let y = 0; y < 12; y++) {
          for (let x = 0; x < 12; x++) {
            gl.readPixels(Math.floor(((x + 0.5) * width) / 12), Math.floor(((y + 0.5) * height) / 12), 1, 1, gl.RED_INTEGER, gl.UNSIGNED_INT, pixel);
            counts[pixel[0]] = (counts[pixel[0]] || 0) + 1;
          }
        }
        gl.bindFramebuffer(gl.FRAMEBUFFER, null);
        return counts;
      },
      dispose() {
        disposeTargets();
        gl.deleteTexture(envTex); gl.deleteTexture(irrTex);
        gl.deleteTexture(shadowTex);
        gl.deleteFramebuffer(shadowFbo);
        for (const record of geoCache.values()) {
          gl.deleteVertexArray(record.vao);
          gl.deleteBuffer(record.index);
        }
        geoCache.clear();
      },
    };
  }

  return { create, edgeNeighbours, math: { m4, identity, mul, perspective, ortho, lookAt, norm, cross, dot } };
})();
