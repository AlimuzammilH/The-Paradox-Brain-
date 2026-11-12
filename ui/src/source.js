// Where thinking events come from: the live engine (paradox.api) when it is running, otherwise a
// recorded demo so the interface can be seen without a model. The demo is labelled as such on screen.

export const MOVES = [
  ["equivocation", "Split the term"], ["scope", "Draw the boundary"], ["shared_premise", "Shared premise"],
  ["stages", "Sequence"], ["levels", "Separate levels"], ["means_ends", "Shared end"],
  ["sublation", "Larger whole"], ["tradeoff", "Trade-off"], ["one_wrong", "False tension"], ["ill_formed", "Repair question"],
];

const params = new URLSearchParams(location.search);
// Served by the engine itself (http://localhost:8100) -> same origin; opened as a file or from the dev server -> localhost:8100.
export const API = params.get("api") || (location.protocol.startsWith("http") && location.port !== "5173" ? location.origin : "http://localhost:8100");

export async function engineOnline() {
  if (params.has("demo")) return false;
  try {
    const ctl = new AbortController(); setTimeout(() => ctl.abort(), 1500);
    const r = await fetch(`${API}/api/health`, { signal: ctl.signal });
    return r.ok;
  } catch { return false; }
}

export async function* liveEvents(session, text) {
  const r = await fetch(`${API}/api/chat`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ session, text }),
  });
  const reader = r.body.getReader(), dec = new TextDecoder();
  let buf = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    let i;
    while ((i = buf.indexOf("\n\n")) >= 0) {
      const chunk = buf.slice(0, i); buf = buf.slice(i + 2);
      const ev = /^event: (.*)$/m.exec(chunk)?.[1], data = /^data: (.*)$/m.exec(chunk)?.[1];
      if (ev && data) yield { phase: ev, data: JSON.parse(data) };
    }
  }
}

export async function rate(session, rating, conclusion_id) {
  try {
    await fetch(`${API}/api/rate`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ session, rating, conclusion_id }) });
  } catch { /* demo or offline */ }
}

// ---- recorded demo ---------------------------------------------------------------------------------
export const DEMO_PROMPT = "Freedom requires individualism. Freedom requires collective action.";

const T = ["Freedom is the absence of interference.", "Each person should decide for themselves.", "The group is a threat to individual choice."];
const A = ["Freedom has to be built and defended collectively.", "Alone, a person cannot secure their own rights.", "Choice depends on conditions only a group can provide."];
const DEMO = [
  [2.0, "frame", { question: "Is freedom an individual condition or a collective achievement?",
    thesis: "Freedom means each person deciding for themselves, free from interference by the group or the state.",
    antithesis: "Freedom only exists where people act together to build and defend the conditions that let anyone choose at all.", kind: "dilemma" }],
  [2.5, "atomise", { thesis_claims: T, antithesis_claims: A }],
  [3.0, "tension", { score: 0.94, core: [T[0], A[0]], thesis_claims: T, antithesis_claims: A,
    matrix: [[0.94, 0.41, 0.66], [0.22, 0.58, 0.31], [0.81, 0.47, 0.72]] }],
  [3.5, "diagnose", { crux: "Whether freedom is a private condition each person holds, or a shared achievement that has to be kept up.",
    fits: { equivocation: 6, scope: 4, shared_premise: 5, stages: 2, levels: 8, means_ends: 3, sublation: 9, tradeoff: 3, one_wrong: 1, ill_formed: 1 },
    chosen: ["sublation", "levels"] }],
  [3.0, "synthesise", { move: "sublation", synthesis: "Freedom is a capacity a person exercises alone but can only hold inside structures many people keep alive." }],
  [1.4, "evaluate", { move: "sublation", score: 0.71, scores: { grounding: 0.97, coherence: 0.81, novelty: 0.88, mush: 0.03 } }],
  [3.0, "synthesise", { move: "levels", synthesis: "At the level of the person, freedom is non-interference; at the level of society, it is an institution." }],
  [1.4, "evaluate", { move: "levels", score: 0.62, scores: { grounding: 0.99, coherence: 0.66, novelty: 0.74, mush: 0.06 } }],
  [2.5, "object", { objection: "Shared structures always end up deciding for the individual, so a freedom that depends on them is permission, not freedom.", tension: 0.38 }],
  [3.0, "answer", { move: "sublation", move_name: "Lift both into a larger whole", cost: "Your freedom now depends on other people keeping their side of it.",
    answer: "Freedom is something you exercise alone and can only keep together. The choosing is always individual: nobody can decide for you without it stopping being your freedom. But the room to choose, the rights, the courts, the fact that a stronger neighbour can't simply take what's yours, is built and maintained by many people acting in concert, and it decays when they stop. So collective action isn't the rival of individual freedom, it's the scaffolding it stands on. The individualist is right about who holds freedom; the collectivist is right about what keeps it standing. The cost is dependence: your freedom now rests on others keeping their side of it. Still standing: shared structures tend to start deciding for the people inside them, and the line between protection and permission has to be guarded, not assumed." }],
  [0.2, "reply", { text: "", intent: "new", conclusion_id: null }],
];

export async function* demoEvents(speed = 1) {
  for (const [wait, phase, data] of DEMO) {
    await new Promise((r) => setTimeout(r, (wait * 1000) / speed));
    yield { phase, data };
  }
}
