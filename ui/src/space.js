// The void: a slow navy/indigo nebula on the inside of a huge sphere, plus a thin field of stars.
import * as THREE from "three";

export function buildNebula() {
  const mat = new THREE.ShaderMaterial({
    side: THREE.BackSide, depthWrite: false,
    uniforms: { uTime: { value: 0 }, uHeat: { value: 0 }, uRed: { value: 0 } },
    vertexShader: `varying vec3 vDir; void main(){ vDir = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }`,
    fragmentShader: /* glsl */`
      uniform float uTime, uHeat, uRed; varying vec3 vDir;
      float h(vec3 p){ p = fract(p * 0.3183099 + 0.1); p *= 17.0; return fract(p.x * p.y * p.z * (p.x + p.y + p.z)); }
      float n(vec3 x){ vec3 i = floor(x), f = fract(x); f = f*f*(3.0-2.0*f);
        return mix(mix(mix(h(i), h(i+vec3(1,0,0)), f.x), mix(h(i+vec3(0,1,0)), h(i+vec3(1,1,0)), f.x), f.y),
                   mix(mix(h(i+vec3(0,0,1)), h(i+vec3(1,0,1)), f.x), mix(h(i+vec3(0,1,1)), h(i+vec3(1,1,1)), f.x), f.y), f.z); }
      float fbm(vec3 p){ float s = 0.0, a = 0.5; for (int i = 0; i < 5; i++){ s += a * n(p); p *= 2.03; a *= 0.5; } return s; }
      void main(){
        vec3 d = vDir; float t = uTime * 0.012;
        float a = fbm(d * 2.2 + vec3(t, t * 0.6, -t));
        float b = fbm(d * 4.5 - vec3(t * 0.7, 0.0, t) + a);
        float gas = smoothstep(0.5, 1.05, a * 0.6 + b * 0.6);
        vec3 voidc = vec3(0.004, 0.006, 0.012);
        vec3 navy = vec3(0.02, 0.045, 0.11), indigo = vec3(0.05, 0.03, 0.12), grey = vec3(0.07, 0.075, 0.09);
        vec3 c = voidc + navy * gas * 0.8 + indigo * smoothstep(0.62, 1.0, b) * 0.5 + grey * pow(gas, 3.0) * 0.2;
        c += vec3(0.25, 0.5, 0.9) * pow(gas, 4.0) * uHeat * 0.6;     // the gas warms when the brain is under tension
        c += vec3(0.6, 0.12, 0.05) * pow(gas, 3.0) * uRed * 0.5;
        gl_FragColor = vec4(c, 1.0);
      }`,
  });
  return new THREE.Mesh(new THREE.SphereGeometry(60, 48, 32), mat);
}

export function buildStars(n = 2600) {
  const pos = new Float32Array(n * 3), size = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    const u = Math.random() * 2 - 1, th = Math.random() * Math.PI * 2, r = 18 + Math.random() * 30, s = Math.sqrt(1 - u * u);
    pos.set([r * s * Math.cos(th), r * u, r * s * Math.sin(th)], i * 3);
    size[i] = Math.random() < 0.04 ? 3 + Math.random() * 3 : 1 + Math.random() * 1.4;
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  g.setAttribute("aSize", new THREE.BufferAttribute(size, 1));
  const m = new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, uniforms: { uTime: { value: 0 }, uPixel: { value: 1 } },
    vertexShader: `attribute float aSize; uniform float uTime, uPixel; varying float vA;
      void main(){ vA = 0.45 + 0.4 * sin(uTime * 0.8 + position.x * 3.1); gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); gl_PointSize = aSize * uPixel; }`,
    fragmentShader: `varying float vA; void main(){ vec2 q = gl_PointCoord - 0.5; float d = dot(q,q); if (d > 0.25) discard; gl_FragColor = vec4(vec3(0.7,0.8,1.0) * exp(-d*16.0) * vA, 1.0); }`,
  });
  return new THREE.Points(g, m);
}
