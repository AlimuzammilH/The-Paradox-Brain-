// Tiny tween engine driven by the render loop. The house style: fast in, overshoot, then hold still.
const live = new Set();

export const ease = {
  linear: (t) => t,
  outExpo: (t) => (t >= 1 ? 1 : 1 - Math.pow(2, -10 * t)),
  inOut: (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2),
  outBack: (t) => { const c1 = 1.9, c3 = c1 + 1; return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2); },
  inQuad: (t) => t * t,
  outQuad: (t) => 1 - (1 - t) * (1 - t),
};

export function tween(duration, fn, e = ease.outExpo) {
  return new Promise((resolve) => {
    live.add({ t0: performance.now(), duration: duration * 1000, fn, e, resolve });
  });
}

// A value that rises fast and falls back slowly, e.g. a flash.
export function pulse(up, down, fn) {
  return tween(up, (t) => fn(t), ease.outExpo).then(() => tween(down, (t) => fn(1 - t), ease.inOut));
}

export const sleep = (s) => new Promise((r) => setTimeout(r, s * 1000));

export function step(now) {
  for (const a of live) {
    const t = Math.min(1, (now - a.t0) / a.duration);
    a.fn(a.e(t), t);
    if (t >= 1) { live.delete(a); a.resolve(); }
  }
}
