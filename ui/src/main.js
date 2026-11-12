import * as THREE from "three";
import { EffectComposer } from "three/examples/jsm/postprocessing/EffectComposer.js";
import { RenderPass } from "three/examples/jsm/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/examples/jsm/postprocessing/UnrealBloomPass.js";
import { OutputPass } from "three/examples/jsm/postprocessing/OutputPass.js";
import { CSS2DRenderer } from "three/examples/jsm/renderers/CSS2DRenderer.js";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { buildBrain, buildShell, claimSpot, REGION } from "./brain.js";
import { buildNebula, buildStars } from "./space.js";
import { Effects } from "./fx.js";
import { Sound } from "./audio.js";
import { tween, ease, pulse, sleep, step } from "./anim.js";
import { MOVES, DEMO_PROMPT, engineOnline, liveEvents, demoEvents, rate } from "./source.js";

const $ = (id) => document.getElementById(id);
const small = Math.min(innerWidth, innerHeight) < 700;

// ---- renderer --------------------------------------------------------------------------------------
const canvas = $("gl");
const renderer = new THREE.WebGLRenderer({ canvas, antialias: false, powerPreference: "high-performance" });
const dpr = Math.min(devicePixelRatio, small ? 1.5 : 1.75);
renderer.setPixelRatio(dpr);
renderer.setSize(innerWidth, innerHeight);
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(55, innerWidth / innerHeight, 0.01, 200);
camera.position.set(0, 0.6, 6.5);

const labels = new CSS2DRenderer({ element: $("labels") });
labels.setSize(innerWidth, innerHeight);

const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
const bloom = new UnrealBloomPass(new THREE.Vector2(innerWidth, innerHeight), 0.7, 0.45, 0.18);
composer.addPass(bloom);
composer.addPass(new OutputPass());

const controls = new OrbitControls(camera, canvas);
controls.enableDamping = true; controls.dampingFactor = 0.06;
controls.minDistance = 0.15; controls.maxDistance = 9;
controls.enabled = false; controls.autoRotateSpeed = 0.35;

const nebula = buildNebula(); scene.add(nebula);
const stars = buildStars(); scene.add(stars);
const brain = buildBrain(small ? 26000 : 60000); scene.add(brain);
const shell = buildShell(); scene.add(shell);
const fx = new Effects(scene);
const sound = new Sound();
const U = brain.material.uniforms;

function resize() {
  camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight); composer.setSize(innerWidth, innerHeight); labels.setSize(innerWidth, innerHeight);
  U.uPixel.value = renderer.getPixelRatio() * Math.min(innerWidth, innerHeight) / 520;
  stars.material.uniforms.uPixel.value = renderer.getPixelRatio();
}
addEventListener("resize", resize); resize();

// ---- camera director: fast whip, then still drift --------------------------------------------------
const look = new THREE.Vector3();
let drift = 0;
async function fly(pos, target, dur = 0.7, e = ease.outBack) {
  controls.enabled = false; controls.autoRotate = false;
  const p0 = camera.position.clone(), l0 = look.clone(), p1 = new THREE.Vector3(...pos), l1 = new THREE.Vector3(...target);
  sound.whoosh();
  await tween(dur, (t) => { camera.position.lerpVectors(p0, p1, t); look.lerpVectors(l0, l1, t); camera.lookAt(look); }, e);
  drift = 1;
}
function freeCamera() {
  controls.target.copy(look); controls.enabled = true; controls.autoRotate = true; drift = 0;
}
let shake = 0;

// ---- region activation -----------------------------------------------------------------------------
const act = U.uAct.value;
function light(region, level = 1, up = 0.25) { return tween(up, (t) => (act[region] = Math.max(act[region], t * level)), ease.outExpo); }
function dim(region, down = 1.2) { const v = act[region]; return tween(down, (t) => (act[region] = v * (1 - t)), ease.inOut); }
function dimAll(down = 1) { for (let i = 0; i < act.length; i++) if (act[i] > 0) dim(i, down); }

// ---- HUD -------------------------------------------------------------------------------------------
const phaseEl = $("phase"), traceEl = $("trace"), candsEl = $("cands"), titleEl = $("title");
function phase(name) { phaseEl.textContent = name; }
function trace(html) {
  const d = document.createElement("div"); d.innerHTML = html; traceEl.appendChild(d);
  while (traceEl.children.length > 40) traceEl.firstChild.remove();
  traceEl.scrollTop = traceEl.scrollHeight;
}
function title(text) { titleEl.textContent = text; titleEl.classList.remove("slam"); void titleEl.offsetWidth; titleEl.classList.add("slam"); }
const esc = (s) => String(s).replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" })[c]);
const cut = (s, n = 60) => (s.length > n ? s.slice(0, n - 1) + "…" : s);
const moveName = (k) => MOVES.find((m) => m[0] === k)?.[1] ?? k;

function candCard(move) {
  const el = document.createElement("div"); el.className = "cand"; el.dataset.move = move;
  el.innerHTML = `<h4><span>${esc(moveName(move).toUpperCase())}</span><span class="sc">…</span></h4>` +
    ["grounding", "coherence", "novelty", "mush"].map((k) => `<div class="bar" data-k="${k}">${k}<i></i><span>–</span></div>`).join("");
  candsEl.appendChild(el);
  return el;
}

// ---- events -> spectacle ---------------------------------------------------------------------------
const state = { round: 0, cands: {}, best: null, conclusion: null, log: [] };

const handlers = {
  async frame(d) {
    phase("FRAME");
    trace(`<b>${esc(cut(d.question, 70))}</b>`);
    trace(`<span class="t">THESIS</span> ${esc(cut(d.thesis, 80))}`);
    trace(`<span class="a">ANTITHESIS</span> ${esc(cut(d.antithesis, 80))}`);
    if (state.round === 0) {
      await fly([0.9, 0.45, 1.6], [0, 0.05, 0], 0.5, ease.inQuad);      // rush at the shell
      tween(0.6, (t) => (shell.userData.mat.uniforms.uOpacity.value = 1 - t * 0.6));
      await fly([0.12, 0.3, 0.95], [0, 0.1, -0.1], 0.65, ease.outExpo);  // through it, inside
    }
    light(REGION.frontal, 0.9);
    tween(1.2, (t) => U.uSide.value.set(t * 0.8, t * 0.8), ease.outExpo);
    sound.tension(0.15);
    await sleep(0.6);
  },

  async atomise(d) {
    phase("ATOMISE");
    dim(REGION.frontal);
    light(REGION.temporal, 0.8);
    d.thesis_claims.forEach((c, i) => { fx.addClaim("t", c, claimSpot("t", i, d.thesis_claims.length), i * 0.18); setTimeout(() => sound.ping(i, "t"), i * 180); });
    d.antithesis_claims.forEach((c, i) => { fx.addClaim("a", c, claimSpot("a", i, d.antithesis_claims.length), 0.5 + i * 0.18); setTimeout(() => sound.ping(i, "a"), 500 + i * 180); });
    trace(`claims: <span class="t">${d.thesis_claims.length}</span> vs <span class="a">${d.antithesis_claims.length}</span>`);
    await sleep(1.4);
    dim(REGION.temporal);
  },

  async tension(d) {
    phase("TENSION");
    await fly([0, 1.05, 1.0], [0, 0.1, 0.05], 0.55);
    light(REGION.acc, 1);
    const T = fx.claims.t, A = fx.claims.a;
    const order = [];
    d.matrix.forEach((row, i) => row.forEach((v, j) => order.push([v, i, j])));
    order.sort((a, b) => a[0] - b[0]);
    for (const [v, i, j] of order) {
      if (!T[i] || !A[j]) continue;
      const core = d.core[0] === d.thesis_claims[i] && d.core[1] === d.antithesis_claims[j];
      fx.arc(T[i].position, A[j].position, v, core);
      if (core) { shake = 0.6 * v; sound.crackle(1.4); bloom.strength = 1.3; tween(1.2, (t) => (bloom.strength = 1.3 - t * 0.6)); }
      else if (v > 0.5) sound.crackle(v * 0.5);
      await sleep(core ? 0.5 : 0.12);
    }
    U.uTension.value = d.score; nebula.material.uniforms.uHeat.value = d.score;
    sound.tension(0.3 + d.score * 0.7);
    trace(`core clash <span class="g">${d.score.toFixed(2)}</span>  ${esc(cut(d.core[0], 34))} <span class="r">×</span> ${esc(cut(d.core[1], 34))}`);
    await sleep(1.2);
  },

  async diagnose(d) {
    phase("DIAGNOSE");
    fx.hideClaimLabels();
    dim(REGION.acc); light(REGION.parietal, 0.9);
    fx.showMoves(MOVES);
    await fly([0, 1.55, 2.5], [0, 0.45, 0], 0.7);
    await sleep(0.6);
    fx.scoreMoves(d.fits, d.chosen);
    trace(`crux: ${esc(cut(d.crux, 90))}`);
    trace(`trying <span class="g">${d.chosen.map(moveName).join(" · ")}</span>`);
    await sleep(1.6);
    dim(REGION.parietal);
  },

  async synthesise(d) {
    phase("SYNTHESISE");
    if (fx.moves) { const g = fx.moves.group; tween(0.6, (t) => g.children.forEach((o) => (o.element.style.opacity = String(1 - t)))).then(() => fx.root.remove(g)); fx.moves = null; }
    if (!state.inSynth) { state.inSynth = true; await fly([0.5, 0.45, 1.25], [0, 0.1, 0], 0.6); }
    light(REGION.callosum, 1);
    state.cands[d.move] = candCard(d.move);
    trace(`<span class="g">${esc(moveName(d.move))}</span> ${esc(cut(d.synthesis, 70))}`);
    await fx.comet(0xffe2a8);
  },

  async evaluate(d) {
    phase("EVALUATE");
    light(REGION.orbito, 0.8);
    const el = state.cands[d.move] ?? candCard(d.move);
    el.querySelector(".sc").textContent = d.score.toFixed(2);
    for (const [k, v] of Object.entries(d.scores)) {
      const bar = el.querySelector(`.bar[data-k="${k}"]`);
      if (!bar) continue;
      bar.querySelector("i").style.setProperty("--v", v);
      if (k === "mush") bar.querySelector("i").style.setProperty("--c", "#ff5a36");
      bar.querySelector("span").textContent = v.toFixed(2);
    }
    if (!state.best || d.score > state.best.score) state.best = d;
    for (const c of candsEl.children) { c.classList.toggle("won", c.dataset.move === state.best.move); c.classList.toggle("lost", c.dataset.move !== state.best.move); }
    await sleep(0.6);
    dim(REGION.orbito); dim(REGION.callosum);
  },

  async object(d) {
    if (!state.novaDone) await supernova();
    phase("OBJECT");
    await fly([1.1, 0.5, 1.35], [0, 0.08, 0.05], 0.55);
    sound.sting();
    U.uObject.value = 1; tween(1.4, (t) => (U.uObject.value = 1 - t));
    nebula.material.uniforms.uRed.value = 1; tween(2, (t) => (nebula.material.uniforms.uRed.value = 1 - t));
    shake = 0.35;
    await fx.objection(d.objection);
    trace(`<span class="r">OBJECTION ${d.tension.toFixed(2)}</span> ${esc(cut(d.objection, 70))}`);
    state.lastObjection = d;
    await sleep(1.2);
  },

  async recurse(d) {
    state.round = d.depth;
    title(`ROUND ${d.depth + 1}`);
    trace(`<span class="g">ROUND ${d.depth + 1}</span> the objection becomes the antithesis`);
    resetRound(false);
    await fly([0.12, 0.3, 0.95], [0, 0.1, -0.1], 0.7);
  },

  async answer(d) {
    if (!state.novaDone && d.move) await supernova();
    phase("ANSWER");
    dimAll();
    tween(1.5, (t) => U.uSide.value.multiplyScalar(1 - t * 0.5));
    sound.tension(0.1);
    if (fx.objectionLabel) { fx.objectionLabel.traverse((o) => o.element?.remove()); fx.root.remove(fx.objectionLabel); fx.objectionLabel = null; }
    await fly([1.9, 0.6, 2.1], [0, 0.0, 0], 0.8, ease.outExpo);
    showAnswer(d);
    freeCamera();
  },

  async reply(d) {
    state.conclusion = d.conclusion_id;
    if (d.intent === "explain" || d.intent === "chat" || !state.answered) showAnswer({ answer: d.text });
    phase("READY");
    $("ask").classList.remove("busy");
  },

  async error(d) { trace(`<span class="r">${esc(d.message)}</span>`); phase("ERROR"); $("ask").classList.remove("busy"); },
};

async function supernova() {
  state.novaDone = true;
  phase("SYNTHESIS");
  await fly([0.6, 0.35, 1.9], [0, 0.08, 0.05], 0.5);
  await fx.collapseClaims();
  tween(0.45, (t) => (U.uCollapse.value = t), ease.inQuad);
  await sleep(0.45);
  sound.nova();
  const flash = $("flash");
  pulse(0.06, 1.1, (t) => (flash.style.opacity = String(t * 0.85)));
  bloom.strength = 2.2; tween(2.2, (t) => (bloom.strength = 2.2 - t * 1.5), ease.outQuad);
  shake = 1;
  fx.nova();
  tween(0.25, (t) => (U.uCollapse.value = 1 - t), ease.outExpo);
  pulse(0.15, 2.2, (t) => (U.uNova.value = t));
  U.uTension.value = 0; nebula.material.uniforms.uHeat.value = 0.15;
  if (state.best) trace(`<span class="g">SYNTHESIS</span> ${esc(moveName(state.best.move))} · ${state.best.score.toFixed(2)}`);
  await sleep(1.2);
}

function showAnswer(d) {
  state.answered = true;
  const box = $("answer"), txt = $("answer-text");
  box.classList.remove("hidden");
  $("answer-move").textContent = d.move_name ?? (d.move ? moveName(d.move) : "");
  $("answer-cost").textContent = d.cost ? `cost: ${d.cost}` : "";
  txt.innerHTML = "";
  (d.answer || "").split(/(\s+)/).forEach((w, i) => {
    const s = document.createElement("span"); s.className = "w"; s.textContent = w; s.style.animationDelay = `${Math.min(i * 0.012, 2.4)}s`; txt.appendChild(s);
  });
  const ob = $("objection");
  if (state.lastObjection && state.lastObjection.tension >= 0.27) {
    ob.textContent = `still standing (${state.lastObjection.tension.toFixed(2)}): ${state.lastObjection.objection}`; ob.classList.remove("hidden");
  } else ob.classList.add("hidden");
  document.querySelectorAll("#rate button[data-r]").forEach((b) => b.classList.remove("on"));
}

function resetRound(full = true) {
  fx.clear();
  candsEl.innerHTML = "";
  state.cands = {}; state.best = null; state.novaDone = false; state.inSynth = false;
  if (fx.objectionLabel) fx.objectionLabel = null;
  if (fx.core) fx.core = null;
  if (full) { state.round = 0; state.answered = false; state.lastObjection = null; $("answer").classList.add("hidden"); traceEl.innerHTML = ""; }
  dimAll(0.4);
}

// ---- driving it ------------------------------------------------------------------------------------
let online = false;
const session = (() => { try { return localStorage.getItem("paradox.session") || (localStorage.setItem("paradox.session", crypto.randomUUID()), localStorage.getItem("paradox.session")); } catch { return crypto.randomUUID(); } })();

async function run(stream, record = true) {
  for await (const ev of stream) {
    if (record) state.log.push(ev);
    const h = handlers[ev.phase];
    if (h) await h(ev.data);
  }
}

async function ask(text) {
  $("ask").classList.add("busy");
  const followUp = state.answered && online;
  if (!followUp) { resetRound(true); state.log = []; }
  else { resetRound(false); state.round = 0; }
  phase("THINKING");
  trace(`<b>› ${esc(cut(text, 80))}</b>`);
  if (!online) trace(`<span class="r">engine offline: replaying the recorded example</span>`);
  await run(online ? liveEvents(session, text) : demoEvents());
  $("ask").classList.remove("busy");
}

// "why": replay the last thinking slowly, from the record
async function replay() {
  if (!state.log.length) return;
  const log = state.log.slice();
  resetRound(true);
  title("REPLAY");
  $("ask").classList.add("busy");
  async function* slow() { for (const ev of log) { await sleep(1.2); yield ev; } }
  await run(slow(), false);
  $("ask").classList.remove("busy");
}

$("ask").addEventListener("submit", (e) => {
  e.preventDefault();
  const v = $("input").value.trim() || (online ? "" : DEMO_PROMPT);
  if (!v) return;
  $("input").value = "";
  if (/^\/?why\??$/i.test(v) && !online) return replay();
  ask(v);
});
$("why").addEventListener("click", () => (online ? ask("why?") : replay()));
document.querySelectorAll("#rate button[data-r]").forEach((b) => b.addEventListener("click", () => {
  const r = +b.dataset.r;
  document.querySelectorAll("#rate button[data-r]").forEach((x) => x.classList.toggle("on", +x.dataset.r <= r));
  sound.ping(r, "t");
  if (online) rate(session, r, state.conclusion);
}));
$("mute").addEventListener("click", () => {
  const on = sound.toggle();
  $("mute").classList.toggle("on", on); $("mute").parentElement.classList.toggle("open", on);
});
$("volume").addEventListener("input", (e) => sound.setVolume(+e.target.value));

// ---- boot ------------------------------------------------------------------------------------------
async function boot() {
  phase("BOOT");
  fx.memoryStars(9);
  online = await engineOnline();
  const mode = $("mode");
  mode.textContent = online ? "ENGINE LIVE" : "DEMO REPLAY";
  mode.classList.toggle("live", online);
  if (!online) $("input").placeholder = `Engine offline. Press enter to watch: "${DEMO_PROMPT}"`;
  sound.swell();
  look.set(0, 0.4, 0); camera.lookAt(look);
  await tween(4.2, (t) => (U.uBoot.value = t * 2.6), ease.linear);
  tween(1.5, (t) => (shell.userData.mat.uniforms.uOpacity.value = t));
  await fly([2.35, 0.75, 1.75], [0, -0.02, 0], 1.6, ease.inOut);
  title("PARADOX");
  phase("READY");
  freeCamera();
  $("input").focus({ preventScroll: true });
}
boot();

// ---- loop ------------------------------------------------------------------------------------------
const clock = new THREE.Timer();
renderer.setAnimationLoop(() => {
  clock.update(); const dt = Math.min(clock.getDelta(), 0.05), t = clock.getElapsed();
  step(performance.now());
  U.uTime.value = t;
  nebula.material.uniforms.uTime.value = t;
  stars.material.uniforms.uTime.value = t;
  brain.rotation.y = Math.sin(t * 0.05) * 0.06;
  shell.rotation.y = brain.rotation.y;
  fx.root.rotation.y = brain.rotation.y;
  if (controls.enabled) controls.update();
  else if (drift) { camera.position.x += Math.sin(t * 0.3) * 0.0006; camera.position.y += Math.cos(t * 0.25) * 0.0004; camera.lookAt(look); }
  if (shake > 0.001) {
    camera.position.x += (Math.random() - 0.5) * 0.02 * shake; camera.position.y += (Math.random() - 0.5) * 0.02 * shake;
    shake *= 0.9;
  }
  fx.update(dt, camera);
  composer.render();
  labels.render(scene, camera);
});
