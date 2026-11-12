// A procedural brain made of points: two folded hemispheres, cerebellum and brainstem, plus a gas of
// interior points. Nothing is loaded from outside, so there is no model licence to worry about.
// Coordinates: x = left(-)/right(+), y = up, z = front(+).
import * as THREE from "three";

// ---- small 3D value noise -------------------------------------------------------------------------
function hash(x, y, z) {
  let h = (x * 374761393 + y * 668265263 + z * 2147483647) | 0;
  h = (h ^ (h >>> 13)) * 1274126177;
  return ((h ^ (h >>> 16)) >>> 0) / 4294967295;
}
const fade = (t) => t * t * (3 - 2 * t);
function vnoise(x, y, z) {
  const xi = Math.floor(x), yi = Math.floor(y), zi = Math.floor(z);
  const xf = fade(x - xi), yf = fade(y - yi), zf = fade(z - zi);
  let out = 0;
  for (let dx = 0; dx < 2; dx++) for (let dy = 0; dy < 2; dy++) for (let dz = 0; dz < 2; dz++) {
    const w = (dx ? xf : 1 - xf) * (dy ? yf : 1 - yf) * (dz ? zf : 1 - zf);
    out += w * hash(xi + dx, yi + dy, zi + dz);
  }
  return out * 2 - 1;
}
// Ridged noise gives sulci and gyri: sharp creases with rounded ridges between them.
function folds(x, y, z) {
  let f = 0, amp = 0.55, fr = 4.2;
  for (let o = 0; o < 3; o++) {
    f += amp * (1 - Math.abs(vnoise(x * fr, y * fr, z * fr)));
    amp *= 0.45; fr *= 2.1;
  }
  return f;
}

// ---- shape -----------------------------------------------------------------------------------------
// Point on a hemisphere surface for direction d (unit vector), side s = -1 left, +1 right.
function hemisphere(d, s, wrinkle = 1) {
  let { x, y, z } = d;
  let rx = 0.6, ry = 0.66, rz = 0.92;
  // temporal lobe: lower front-side bulge
  const temporal = Math.max(0, -y) * Math.max(0, 1 - Math.abs(z - 0.1) * 1.4) * Math.max(0, x * s);
  rx += 0.08 * temporal;
  // flat underside, flat medial wall (the longitudinal fissure)
  let p = new THREE.Vector3(x * rx, y * ry, z * rz);
  if (p.y < -0.18) p.y = -0.18 + (p.y + 0.18) * 0.45;
  if (p.x * s < 0) p.x *= 0.12;
  // frontal lobe slightly narrower and lower than the parietal dome
  p.y += 0.06 * Math.max(0, -z) * (1 - Math.abs(x));
  p.x += s * 0.34;
  const f = folds(p.x * 1.3 + s * 3.1, p.y * 1.3, p.z * 1.3);
  const n = p.clone().sub(new THREE.Vector3(s * 0.34, 0, 0)).normalize();
  const out = p.addScaledVector(n, (f - 0.62) * 0.12 * wrinkle);
  out.fold = f;
  return out;
}
function cerebellum(d) {
  const p = new THREE.Vector3(d.x * 0.5, d.y * 0.24, d.z * 0.3);
  p.y += 0.024 * Math.sin(p.y * 90);           // horizontal folia
  return p.add(new THREE.Vector3(0, -0.36, -0.58));
}
function brainstem(t, a) {
  const r = 0.11 - t * 0.03;
  return new THREE.Vector3(Math.cos(a) * r, -0.3 - t * 0.55, -0.22 - t * 0.12 + Math.sin(a) * r * 0.8);
}
function randDir() {
  const u = Math.random() * 2 - 1, th = Math.random() * Math.PI * 2, r = Math.sqrt(1 - u * u);
  return new THREE.Vector3(r * Math.cos(th), u, r * Math.sin(th));
}

// ---- regions ---------------------------------------------------------------------------------------
export const REGION = { cortex: 0, frontal: 1, temporal: 2, acc: 3, parietal: 4, callosum: 5, orbito: 6, hippo: 7, occipital: 8 };
function regionOf(p, interior) {
  const ax = Math.abs(p.x);
  if (interior) {
    if (ax < 0.16 && p.y > -0.02 && p.y < 0.26 && p.z > -0.5 && p.z < 0.45) return REGION.callosum;
    if (ax > 0.18 && ax < 0.48 && p.y < -0.06 && p.z > -0.35 && p.z < 0.12) return REGION.hippo;
    if (ax < 0.26 && p.z > 0.05 && p.z < 0.6 && p.y > 0.0 && p.y < 0.5) return REGION.acc;
  }
  if (p.z > 0.55 && p.y < 0.05) return REGION.orbito;
  if (p.z > 0.35) return REGION.frontal;
  if (p.y < -0.05 && ax > 0.5 && p.z > -0.35) return REGION.temporal;
  if (p.z < -0.55) return REGION.occipital;
  if (p.y > 0.3) return REGION.parietal;
  return REGION.cortex;
}

// ---- build -----------------------------------------------------------------------------------------
export function buildBrain(count) {
  const surface = Math.floor(count * 0.78), inner = count - surface;
  const target = new Float32Array(count * 3), start = new Float32Array(count * 3);
  const region = new Float32Array(count), seed = new Float32Array(count), kind = new Float32Array(count), fold = new Float32Array(count);
  const towers = [];
  for (let i = 0; i < 26; i++) {                 // PS2-style columns standing in a ring
    const a = (i / 26) * Math.PI * 2 + Math.random() * 0.12, r = 1.9 + Math.random() * 1.4;
    towers.push({ x: Math.cos(a) * r, z: Math.sin(a) * r - 0.3, h: 0.6 + Math.random() * 2.2, w: 0.04 + Math.random() * 0.07 });
  }
  const v = new THREE.Vector3();
  for (let i = 0; i < count; i++) {
    let p, interior = false;
    if (i < surface) {
      const roll = Math.random();
      if (roll < 0.86) p = hemisphere(randDir(), Math.random() < 0.5 ? -1 : 1);
      else if (roll < 0.96) p = cerebellum(randDir());
      else p = brainstem(Math.random(), Math.random() * Math.PI * 2);
    } else {
      interior = true;
      const s = Math.random() < 0.5 ? -1 : 1;
      p = hemisphere(randDir(), s, 0).sub(new THREE.Vector3(s * 0.34, 0, 0)).multiplyScalar(Math.cbrt(Math.random()) * 0.88)
        .add(new THREE.Vector3(s * 0.3, 0, 0));
      if (Math.random() < 0.25) p.set((Math.random() - 0.5) * 0.3, Math.random() * 0.26, Math.random() * 0.95 - 0.5);  // callosum band
    }
    p.toArray(target, i * 3);
    fold[i] = p.fold ?? 0.6;
    region[i] = regionOf(p, interior);
    kind[i] = interior ? 1 : 0;
    seed[i] = Math.random();
    const t = towers[i % towers.length];
    v.set(t.x + (Math.random() - 0.5) * t.w, Math.random() * t.h - 1.2, t.z + (Math.random() - 0.5) * t.w);
    v.toArray(start, i * 3);
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.BufferAttribute(target, 3));
  geo.setAttribute("aStart", new THREE.BufferAttribute(start, 3));
  geo.setAttribute("aRegion", new THREE.BufferAttribute(region, 1));
  geo.setAttribute("aSeed", new THREE.BufferAttribute(seed, 1));
  geo.setAttribute("aKind", new THREE.BufferAttribute(kind, 1));
  geo.setAttribute("aFold", new THREE.BufferAttribute(fold, 1));
  geo.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 3.5);

  const mat = new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    uniforms: {
      uTime: { value: 0 }, uBoot: { value: 0 }, uPixel: { value: 1 }, uSize: { value: 1 },
      uAct: { value: new Array(9).fill(0) },
      uSide: { value: new THREE.Vector2(0, 0) },   // thesis (left) / antithesis (right) glow
      uTension: { value: 0 }, uCollapse: { value: 0 }, uNova: { value: 0 }, uObject: { value: 0 },
    },
    vertexShader: /* glsl */`
      attribute vec3 aStart; attribute float aRegion; attribute float aSeed; attribute float aKind; attribute float aFold;
      uniform float uTime, uBoot, uPixel, uSize, uTension, uCollapse, uNova, uObject;
      uniform float uAct[9]; uniform vec2 uSide;
      varying vec3 vColor; varying float vAlpha;
      float easeOutExpo(float t){ return t >= 1.0 ? 1.0 : 1.0 - pow(2.0, -10.0 * t); }
      float easeInOut(float t){ return t < 0.5 ? 4.0*t*t*t : 1.0 - pow(-2.0*t + 2.0, 3.0) / 2.0; }
      void main(){
        // boot: columns shoot up out of the dark, hang, then pull together into the brain
        float rise = easeOutExpo(clamp((uBoot - aSeed * 0.45) / 0.4, 0.0, 1.0));
        vec3 p = mix(aStart - vec3(0.0, 3.5, 0.0), aStart, rise);
        float gather = easeInOut(clamp((uBoot - 1.25 - aSeed * 0.55) / 0.75, 0.0, 1.0));
        p = mix(p, position, gather);
        // breathing and shimmer
        p += normalize(position + 0.0001) * sin(uTime * 0.7 + aSeed * 6.283) * 0.004;
        p += vec3(sin(uTime*1.3+aSeed*40.0), cos(uTime*1.1+aSeed*30.0), sin(uTime*0.9+aSeed*20.0)) * 0.006 * aKind;
        // tension makes the cortex tremble
        p += vec3(sin(uTime*37.0+aSeed*90.0), cos(uTime*41.0+aSeed*70.0), 0.0) * 0.004 * uTension;
        // collapse before the supernova, then the blast throws everything outward and it settles back
        p = mix(p, p * 0.18 + vec3(0.0, 0.05, 0.0), uCollapse * (0.35 + 0.65 * aKind));
        p += normalize(p + 0.0001) * uNova * (0.25 + aSeed * 0.5);

        int r = int(aRegion + 0.5);
        float act = uAct[r];
        float side = position.x < 0.0 ? uSide.x : uSide.y;
        // gyri glow, sulci fall into shadow, so the folds read as lines of light
        float ridge = smoothstep(0.5, 0.82, aFold);
        vec3 base = mix(vec3(0.1, 0.13, 0.21) + vec3(0.36, 0.46, 0.66) * ridge, vec3(0.08, 0.11, 0.26), aKind);
        vec3 thesis = vec3(0.38, 0.84, 1.0), anti = vec3(0.72, 0.55, 1.0);
        vec3 c = base;
        c = mix(c, position.x < 0.0 ? thesis : anti, side * 0.55);
        vec3 hot = r == 3 ? vec3(1.0, 0.85, 0.6) : r == 7 ? vec3(0.5, 1.0, 0.85) : r == 5 ? vec3(1.0, 0.95, 0.85) : vec3(0.55, 0.85, 1.0);
        c = mix(c, hot, act);
        c = mix(c, vec3(1.0, 0.92, 0.75), uNova * 0.8 + uCollapse * 0.5);
        c = mix(c, vec3(1.0, 0.35, 0.2), uObject * 0.35 * (1.0 - aKind));
        float twinkle = 0.75 + 0.25 * sin(uTime * (1.0 + aSeed * 3.0) + aSeed * 50.0);
        vColor = c * twinkle * (0.85 + act * 1.3 + side * 0.3 + uNova * 1.3);
        vec4 mv = modelViewMatrix * vec4(p, 1.0);
        // points right next to the camera fade out instead of ballooning into blobs
        float nearFade = smoothstep(0.05, 0.35, -mv.z);
        vAlpha = mix(0.8, 0.28, aKind) * smoothstep(0.0, 0.2, uBoot) * nearFade;
        gl_Position = projectionMatrix * mv;
        float size = (aKind > 0.5 ? 1.8 : 1.6) * (1.0 + act * 0.9 + uNova * 1.5) * uSize;
        gl_PointSize = clamp(size * uPixel * (1.6 / -mv.z), 0.0, 6.0);
      }`,
    fragmentShader: /* glsl */`
      varying vec3 vColor; varying float vAlpha;
      void main(){
        vec2 q = gl_PointCoord - 0.5; float d = dot(q, q);
        if (d > 0.25) discard;
        float a = exp(-d * 14.0) * vAlpha;
        gl_FragColor = vec4(vColor * a, a);
      }`,
  });
  const points = new THREE.Points(geo, mat);
  points.frustumCulled = false;
  return points;
}

// Glass shell: smooth hemispheres lit only at the edges (fresnel), so the brain reads as a vessel.
export function buildShell() {
  const group = new THREE.Group();
  const mat = new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide,
    uniforms: { uOpacity: { value: 0 }, uColor: { value: new THREE.Color(0.35, 0.5, 0.9) } },
    vertexShader: `varying vec3 vN; varying vec3 vV;
      void main(){ vec4 mv = modelViewMatrix * vec4(position,1.0); vN = normalize(normalMatrix * normal); vV = normalize(-mv.xyz); gl_Position = projectionMatrix * mv; }`,
    fragmentShader: `uniform float uOpacity; uniform vec3 uColor; varying vec3 vN; varying vec3 vV;
      void main(){ float f = pow(1.0 - abs(dot(vN, vV)), 5.0) * 0.22; gl_FragColor = vec4(uColor * f * uOpacity, f * uOpacity); }`,
  });
  for (const s of [-1, 1]) {
    const g = new THREE.IcosahedronGeometry(1, 5);
    const pos = g.attributes.position, v = new THREE.Vector3();
    for (let i = 0; i < pos.count; i++) {
      v.fromBufferAttribute(pos, i).normalize();
      hemisphere(v, s, 0.6).multiplyScalar(1.035).toArray(pos.array, i * 3);
    }
    g.computeVertexNormals();
    group.add(new THREE.Mesh(g, mat));
  }
  group.userData.mat = mat;
  return group;
}

// Points inside each hemisphere where claims can sit.
export function claimSpot(side, i, n) {
  const s = side === "t" ? -1 : 1;
  const spread = n > 1 ? i / (n - 1) - 0.5 : 0;
  return new THREE.Vector3(s * (0.38 + 0.06 * Math.cos(i * 2.1)), 0.12 + spread * 0.42, 0.28 - Math.abs(spread) * 0.35 + 0.08 * Math.sin(i * 1.7));
}
