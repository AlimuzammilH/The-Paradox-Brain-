// The things that appear inside the brain while it thinks: claim stars, contradiction arcs, comets
// crossing the bridge, the supernova and its shockwave, the objection streak, and memory stars.
import * as THREE from "three";
import { CSS2DObject } from "three/examples/jsm/renderers/CSS2DRenderer.js";
import { tween, ease, pulse } from "./anim.js";

const ADD = { transparent: true, depthWrite: false, blending: THREE.AdditiveBlending };

function glowTexture() {
  const c = document.createElement("canvas"); c.width = c.height = 128;
  const g = c.getContext("2d"), r = g.createRadialGradient(64, 64, 0, 64, 64, 64);
  r.addColorStop(0, "rgba(255,255,255,1)"); r.addColorStop(0.15, "rgba(255,255,255,.75)");
  r.addColorStop(0.4, "rgba(255,255,255,.18)"); r.addColorStop(1, "rgba(255,255,255,0)");
  g.fillStyle = r; g.fillRect(0, 0, 128, 128);
  return new THREE.CanvasTexture(c);
}
const GLOW = glowTexture();

export function sprite(color, scale = 0.08) {
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: GLOW, color, ...ADD }));
  s.scale.setScalar(scale);
  return s;
}

export function label(text, cls) {
  const el = document.createElement("div");
  el.className = `lbl ${cls}`;
  el.textContent = text;
  const o = new CSS2DObject(el);
  return o;
}

export class Effects {
  constructor(scene) {
    this.scene = scene;
    this.root = new THREE.Group(); scene.add(this.root);
    this.claims = { t: [], a: [] };
    this.arcs = [];
    this.moves = null;
    this.time = 0;
  }

  clear() {
    for (const o of [...this.root.children]) {
      o.traverse((c) => { if (c.isCSS2DObject) c.element.remove(); c.geometry?.dispose?.(); });
      this.root.remove(o);
    }
    this.claims = { t: [], a: [] }; this.arcs = []; this.moves = null;
  }

  // ---- claims ------------------------------------------------------------------------------------
  addClaim(side, text, pos, delay = 0) {
    const color = side === "t" ? 0x62d6ff : 0xb88cff;
    const star = sprite(color, 0.0001);
    star.position.copy(pos);
    const lbl = label(text, side);
    lbl.position.set(side === "t" ? -0.02 : 0.02, 0, 0);
    lbl.center.set(side === "t" ? 1 : 0, 0.5);
    lbl.element.style.opacity = "0";
    star.add(lbl);
    this.root.add(star);
    this.claims[side].push(star);
    setTimeout(() => {
      lbl.element.style.opacity = "1";
      tween(0.5, (t) => star.scale.setScalar(0.0001 + t * 0.09), ease.outBack);
    }, delay * 1000);
    return star;
  }

  hideClaimLabels() { for (const s of [...this.claims.t, ...this.claims.a]) s.children[0]?.element && (s.children[0].element.style.opacity = "0.25"); }

  // ---- contradiction arcs ------------------------------------------------------------------------
  arc(a, b, strength, core = false) {
    const mid = a.clone().add(b).multiplyScalar(0.5);
    mid.y += 0.18 + 0.25 * strength; mid.z += 0.1;
    const curve = new THREE.QuadraticBezierCurve3(a.clone(), mid, b.clone());
    const geo = new THREE.TubeGeometry(curve, 64, core ? 0.0035 : 0.0008 + 0.0018 * strength, 6, false);
    const mat = new THREE.ShaderMaterial({
      ...ADD,
      uniforms: { uTime: { value: 0 }, uReveal: { value: 0 }, uStrength: { value: strength }, uCore: { value: core ? 1 : 0 } },
      vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }`,
      fragmentShader: /* glsl */`
        uniform float uTime, uReveal, uStrength, uCore; varying vec2 vUv;
        float h(float x){ return fract(sin(x * 91.7) * 43758.5); }
        void main(){
          if (vUv.x > uReveal) discard;
          float flow = 0.5 + 0.5 * sin(vUv.x * 40.0 - uTime * 9.0);
          float crackle = uCore * step(0.55, h(floor(uTime * 24.0) + floor(vUv.x * 30.0)));
          vec3 c = mix(vec3(0.55, 0.75, 1.0), vec3(1.0, 0.86, 0.6), uCore);
          float a = (0.08 + 0.6 * uStrength * uStrength + 0.5 * uCore) * (0.55 + 0.45 * flow) + crackle * 0.6;
          gl_FragColor = vec4(c * a, a);
        }`,
    });
    const m = new THREE.Mesh(geo, mat);
    this.root.add(m);
    this.arcs.push(m);
    tween(core ? 0.9 : 0.55, (t) => (mat.uniforms.uReveal.value = t), ease.outExpo);
    return m;
  }

  // ---- the ring of moves -------------------------------------------------------------------------
  showMoves(names) {
    const g = new THREE.Group(); g.position.set(0, 0.95, 0); this.root.add(g);
    const items = {};
    names.forEach(([key, name], i) => {
      const a = (i / names.length) * Math.PI * 2;
      const el = document.createElement("div"); el.className = "move"; el.innerHTML = `${name}<span class="fit"></span>`;
      const o = new CSS2DObject(el); o.position.set(Math.cos(a) * 1.35, 0, Math.sin(a) * 1.35);
      el.style.opacity = "0"; setTimeout(() => (el.style.opacity = "1"), i * 60);
      g.add(o); items[key] = el;
    });
    this.moves = { group: g, items };
  }
  scoreMoves(fits, chosen) {
    if (!this.moves) return;
    for (const [k, el] of Object.entries(this.moves.items)) {
      const v = (fits[k] ?? 0) / 10;
      el.querySelector(".fit").style.setProperty("--v", v);
      el.classList.toggle("lit", v >= 0.4);
      el.classList.toggle("chosen", chosen.includes(k));
    }
  }

  // ---- a comet across the corpus callosum --------------------------------------------------------
  comet(color = 0xffe2a8) {
    const curve = new THREE.CatmullRomCurve3([
      new THREE.Vector3(-0.42, 0.12, 0.25), new THREE.Vector3(-0.12, 0.14, 0.05), new THREE.Vector3(0, 0.13, -0.05),
      new THREE.Vector3(0.12, 0.14, 0.05), new THREE.Vector3(0.42, 0.12, 0.25), new THREE.Vector3(0, 0.18, 0.4)]);
    const trail = [];
    for (let i = 0; i < 14; i++) { const s = sprite(color, 0.07 * (1 - i / 14)); s.material.opacity = 1 - i / 14; this.root.add(s); trail.push(s); }
    return tween(1.6, (t) => {
      trail.forEach((s, i) => s.position.copy(curve.getPointAt(Math.max(0, t - i * 0.012))));
    }, ease.inOut).then(() => tween(0.5, (t) => trail.forEach((s) => (s.material.opacity *= 1 - t)))).then(() => trail.forEach((s) => this.root.remove(s)));
  }

  // ---- supernova ---------------------------------------------------------------------------------
  async collapseClaims() {
    const stars = [...this.claims.t, ...this.claims.a];
    const from = stars.map((s) => s.position.clone());
    for (const s of stars) s.children[0] && (s.children[0].element.style.opacity = "0");
    for (const a of this.arcs) tween(0.5, (t) => (a.material.uniforms.uStrength.value *= 1 - t * 0.2));
    await tween(0.9, (t) => stars.forEach((s, i) => s.position.lerpVectors(from[i], new THREE.Vector3(0, 0.08, 0.05), t)), ease.inOut);
  }

  nova(center = new THREE.Vector3(0, 0.08, 0.05)) {
    // burst particles
    const n = 2400, pos = new Float32Array(n * 3), vel = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) {
      const u = Math.random() * 2 - 1, th = Math.random() * Math.PI * 2, s = Math.sqrt(1 - u * u), sp = 0.6 + Math.random() * 2.2;
      vel.set([s * Math.cos(th) * sp, u * sp * 0.8, s * Math.sin(th) * sp], i * 3);
      pos.set([center.x, center.y, center.z], i * 3);
    }
    const g = new THREE.BufferGeometry(); g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    const m = new THREE.PointsMaterial({ map: GLOW, size: 0.05, color: 0xffe9c2, ...ADD, opacity: 1 });
    const burst = new THREE.Points(g, m); burst.frustumCulled = false; this.root.add(burst);
    const c0 = [center.x, center.y, center.z];
    tween(3.2, (t, raw) => {
      for (let i = 0; i < n * 3; i++) pos[i] = c0[i % 3] + vel[i] * t * 1.1;
      g.attributes.position.needsUpdate = true;
      m.opacity = 1 - raw; m.size = 0.05 * (1 - raw * 0.7);
      m.color.setRGB(1, 0.9 - raw * 0.5, 0.75 - raw * 0.6);
    }, ease.outExpo).then(() => this.root.remove(burst));
    // shockwave ring (always faces the camera)
    const ring = new THREE.Mesh(new THREE.RingGeometry(0.96, 1, 128), new THREE.MeshBasicMaterial({ color: 0xffd9a0, ...ADD, side: THREE.DoubleSide, opacity: 0.9 }));
    ring.position.copy(center); ring.userData.billboard = true; this.root.add(ring);
    tween(1.8, (t, raw) => { ring.scale.setScalar(0.01 + t * 3.2); ring.material.opacity = 0.9 * (1 - raw); ring.material.color.setRGB(1, 0.85 - raw * 0.3, 0.6 + raw * 0.3); }, ease.outExpo)
      .then(() => this.root.remove(ring));
    // core: the new star that stays
    const core = sprite(0xfff1d6, 0.0001); core.position.copy(center); this.root.add(core);
    pulse(0.12, 1.4, (t) => core.scale.setScalar(0.0001 + t * 1.6)).then(() => tween(0.8, (t) => core.scale.setScalar(0.18 + 0.02 * Math.sin(t * 6)), ease.outExpo));
    this.core = core;
    // old claims and arcs burn away
    for (const s of [...this.claims.t, ...this.claims.a]) this.root.remove(s);
    for (const a of this.arcs) this.root.remove(a);
    this.claims = { t: [], a: [] }; this.arcs = [];
  }

  // ---- objection streak --------------------------------------------------------------------------
  async objection(text) {
    const target = (this.core?.position ?? new THREE.Vector3(0, 0.08, 0.05)).clone();
    const dir = new THREE.Vector3(1.2, 0.6, 0.9).normalize();
    const from = target.clone().addScaledVector(dir, 3.2);
    const head = sprite(0xff5a36, 0.12); head.position.copy(from); this.root.add(head);
    const trail = [];
    for (let i = 0; i < 18; i++) { const s = sprite(0xff7a4a, 0.09 * (1 - i / 18)); s.material.opacity = 0.8 * (1 - i / 18); this.root.add(s); trail.push(s); }
    await tween(0.55, (t) => {
      head.position.lerpVectors(from, target, t);
      trail.forEach((s, i) => s.position.lerpVectors(from, target, Math.max(0, t - i * 0.02)));
    }, ease.inQuad);
    const lbl = label(text, "r"); lbl.center.set(0, 1.2);
    const anchor = new THREE.Object3D(); anchor.position.copy(target).add(new THREE.Vector3(0.08, 0.12, 0)); anchor.add(lbl); this.root.add(anchor);
    pulse(0.08, 0.6, (t) => head.scale.setScalar(0.12 + t * 0.6));
    tween(0.8, (t) => trail.forEach((s) => (s.material.opacity *= 1 - t))).then(() => { trail.forEach((s) => this.root.remove(s)); this.root.remove(head); });
    this.objectionLabel = anchor;
  }

  // ---- memory: stars in orbit outside the brain --------------------------------------------------
  memoryStars(n) {
    if (this.memory) return this.memory;
    const g = new THREE.Group(); this.scene.add(g);
    for (let i = 0; i < n; i++) {
      const s = sprite(0xa8c6ff, 0.05 + Math.random() * 0.04);
      s.userData = { r: 1.7 + Math.random() * 0.9, a: Math.random() * 6.28, y: (Math.random() - 0.5) * 1.2, w: 0.05 + Math.random() * 0.08 };
      g.add(s);
    }
    this.memory = g;
    return g;
  }
  async recall() {
    const s = this.memory?.children[0];
    if (!s) return;
    const from = s.position.clone(), to = new THREE.Vector3(-0.32, -0.12, -0.08);
    s.userData.pinned = true;
    await tween(1.1, (t) => s.position.lerpVectors(from, to, t), ease.inOut);
    pulse(0.1, 1, (t) => s.scale.setScalar(0.07 + t * 0.15));
  }

  update(dt, camera) {
    this.time += dt;
    for (const a of this.arcs) a.material.uniforms.uTime.value = this.time;
    this.root.traverse((o) => { if (o.userData.billboard) o.quaternion.copy(camera.quaternion); });
    if (this.memory) for (const s of this.memory.children) {
      if (s.userData.pinned) continue;
      const u = s.userData; u.a += u.w * dt;
      s.position.set(Math.cos(u.a) * u.r, u.y + Math.sin(u.a * 2) * 0.1, Math.sin(u.a) * u.r);
    }
  }
}
