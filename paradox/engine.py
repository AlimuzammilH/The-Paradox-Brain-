"""The dialectic engine.

One round:
  1. frame      the language model states both sides in their strongest form
  2. atomise    each side is broken into short claims that stand on their own
  3. tension    the NLI model scores every claim against every other claim and finds the core clash
  4. diagnose   the language model judges which dialectical moves fit; learned weights reorder them
  5. synthesise one candidate per chosen move, each forced into that move's shape
  6. evaluate   the NLI model scores every candidate: does it keep both sides, contradict itself,
                collapse into "both have a point", or just repeat one side?
  7. object     the best candidate gets its strongest objection. If the objection really contradicts
                it (NLI, not the model's opinion), that objection becomes the next antithesis.
Rounds continue until no real contradiction is left or the depth limit is reached, then the
answer is written from the last surviving synthesis.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Callable

from . import config
from .llm import LLM
from .nli import NLI, split_sentences
from .patterns import BY_KEY, MOVES, Move, menu

VOICE = ("You are Paradox, an engine for hard thoughts. You dissect arguments; you do not flatter, "
         "hedge, moralise or perform balance. Be concrete and exact.")

MUSH = [
    "Both sides have valid points and the truth lies somewhere in the middle.",
    "The right answer depends on the situation and on personal values.",
    "What is needed is a balance between the two positions.",
    # the positive-sounding version: "both together make it richer"
    "Both elements can coexist and each contributes to a richer, more complete whole.",
    "Combining the two perspectives produces a better result than either alone.",
]
MUSH_PHRASES = re.compile(r"\b(it depends|strike a balance|finding a balance|both sides have|middle ground|"
                          r"nuanced approach|best of both worlds|there is no easy answer|richer,? more nuanced|"
                          r"can (both )?(coexist|embody both)|both .{0,40} and .{0,40} contribut|remains? (an )?open|"
                          r"open question|left unresolved|remains unresolved|consider both|neither overshadows|"
                          r"the key is to recogni[sz]e|acknowledges? the importance)", re.I)

Emit = Callable[[str, dict], None]


@dataclass
class Candidate:
    move: str
    synthesis: str
    claim: str = ""
    from_thesis: str = ""
    from_antithesis: str = ""
    cost: str = ""
    scores: dict = field(default_factory=dict)
    score: float = 0.0


@dataclass
class Round:
    thesis: str
    antithesis: str
    thesis_claims: list[str]
    antithesis_claims: list[str]
    tension: float
    core: tuple[str, str]
    crux: str
    fits: dict
    candidates: list[Candidate]
    best: Candidate
    objection: str = ""
    objection_tension: float = 0.0


@dataclass
class Result:
    question: str
    kind: str
    answer: str
    rounds: list[Round]
    calls: int = 0
    seconds: float = 0.0

    @property
    def final(self) -> Candidate | None:
        return self.rounds[-1].best if self.rounds else None

    def to_dict(self) -> dict:
        return asdict(self)


def _clean_list(items, limit: int) -> list[str]:
    out = [str(x).strip() for x in items or [] if str(x).strip()]
    return out[:limit]


class Dialectic:
    def __init__(self, llm: LLM, nli: NLI, weights: Callable[[str], float] | None = None,
                 emit: Emit | None = None, max_depth: int = config.MAX_DEPTH,
                 tension_min: float = config.TENSION_MIN, per_round: int = config.PATTERNS_PER_ROUND):
        self.llm, self.nli = llm, nli
        self.weights = weights or (lambda key: 1.0)
        self.emit = emit or (lambda phase, data: None)
        self.max_depth, self.tension_min, self.per_round = max_depth, tension_min, per_round

    # 1. frame -----------------------------------------------------------------------------------

    def frame(self, text: str, context: str = "", recalled: list[str] | None = None) -> dict:
        memory = ""
        if recalled:
            memory = ("\n\nConclusions you reached earlier on related questions (use them only if they "
                      "really apply):\n" + "\n".join(f"- {r}" for r in recalled))
        ctx = f"\n\nRecent conversation:\n{context}" if context else ""
        data = self.llm.ask_json(
            VOICE,
            f"Input:\n{text}{ctx}{memory}\n\n"
            "Find the tension in this input. If it states two positions, those ARE the thesis and antithesis: keep "
            "their exact meaning and only sharpen the wording, never swap in a different debate. If it states one position, "
            "the antithesis is the strongest serious opposing position. If it is a question or dilemma, give "
            "the two strongest opposing answers. State each side in its strongest form, as its best defender "
            "would, in one or two sentences, without straw men.\n"
            'Return keys: "question" (the underlying question in one line), "thesis", "antithesis", '
            '"kind" ("dilemma", "paradox", "claim", "question", or "none" if there is no real tension to work on).',
            keys=["question", "thesis", "antithesis", "kind"], temperature=0.3)
        self.emit("frame", data)
        return data

    # 2. atomise ---------------------------------------------------------------------------------

    def atomise(self, thesis: str, antithesis: str) -> tuple[list[str], list[str]]:
        data = self.llm.ask_json(
            VOICE,
            f"Thesis: {thesis}\nAntithesis: {antithesis}\n\n"
            "Break each side into 2 to 4 short claims. Each claim is one plain declarative sentence that "
            "makes sense on its own (no 'it', 'this' or 'they' pointing outside the sentence).\n"
            'Return keys: "thesis_claims", "antithesis_claims" (lists of strings).',
            keys=["thesis_claims", "antithesis_claims"], temperature=0.2)
        t = _clean_list(data["thesis_claims"], 4) or [thesis]
        a = _clean_list(data["antithesis_claims"], 4) or [antithesis]
        self.emit("atomise", {"thesis_claims": t, "antithesis_claims": a})
        return t, a

    # 3. tension ---------------------------------------------------------------------------------

    def tension(self, t_claims: list[str], a_claims: list[str]) -> tuple[float, tuple[str, str], list]:
        m = self.nli.matrix(t_claims, a_claims)
        i, j = divmod(int(m.argmax()), m.shape[1])
        score, core = float(m[i, j]), (t_claims[i], a_claims[j])
        self.emit("tension", {"score": score, "core": core, "matrix": m.round(3).tolist(),
                              "thesis_claims": t_claims, "antithesis_claims": a_claims})
        return score, core, m.tolist()

    # 4. diagnose --------------------------------------------------------------------------------

    def diagnose(self, thesis: str, antithesis: str, core: tuple[str, str], score: float) -> tuple[str, dict, list[Move]]:
        clash = ("These two claims flatly contradict each other" if score >= self.tension_min
                 else "These claims barely contradict each other logically, so the sides may be talking "
                      "past each other or the conflict may be practical rather than logical")
        data = self.llm.ask_json(
            VOICE,
            f"Thesis: {thesis}\nAntithesis: {antithesis}\n"
            f"Core clash: \"{core[0]}\" versus \"{core[1]}\". {clash} (contradiction score {score:.2f}).\n\n"
            f"Possible moves:\n{menu()}\n\n"
            "Rate how well each move fits THIS tension, 0 to 10. Most moves should score low; only a few fit.\n"
            'Return keys: "crux" (one sentence: what the disagreement really turns on), '
            '"fits" (object mapping every move name to an integer 0-10).',
            keys=["crux", "fits"], temperature=0.2)
        raw = data["fits"]
        if isinstance(raw, list):   # some models answer [{"move": ..., "score": ...}, ...]
            raw = {str(x.get("move") or x.get("name")): x.get("score", x.get("fit", 0)) for x in raw if isinstance(x, dict)}
        by_name = {m.name.lower(): m.key for m in MOVES}
        norm = {by_name.get(str(k).lower(), str(k).lower().strip()): v for k, v in dict(raw).items()}
        fits = {}
        for key in BY_KEY:
            try:
                fits[key] = max(0, min(10, int(float(norm.get(key, 0)))))
            except (TypeError, ValueError):
                fits[key] = 0
        ranked = sorted(MOVES, key=lambda m: fits[m.key] / 10 * self.weights(m.key), reverse=True)
        # Always let at least two moves compete; a single candidate has nothing to be judged against.
        chosen = [m for m in ranked if fits[m.key] >= 4][: self.per_round]
        if len(chosen) < min(2, self.per_round):
            chosen = ranked[: min(2, self.per_round)]
        self.emit("diagnose", {"crux": data["crux"], "fits": fits,
                               "weights": {k: round(self.weights(k), 3) for k in BY_KEY},
                               "chosen": [m.key for m in chosen]})
        return str(data["crux"]), fits, chosen

    # 5. synthesise ------------------------------------------------------------------------------

    def synthesise(self, thesis: str, antithesis: str, crux: str, move: Move) -> Candidate:
        data = self.llm.ask_json(
            VOICE,
            f"Thesis: {thesis}\nAntithesis: {antithesis}\nCrux: {crux}\n\n"
            f"Resolve this with one specific move: {move.name}.\nHow: {move.build}\n\n"
            "Write the synthesis in 3 to 6 sentences. It must say something neither side said. "
            "No averaging, no 'it depends', no 'both sides have a point'.\n"
            'Return keys: "synthesis", "claim" (the synthesis in one plain sentence), '
            '"from_thesis" (what survives from the thesis, one sentence), '
            '"from_antithesis" (what survives from the antithesis, one sentence), '
            '"cost" (what is given up or still unresolved, one sentence).',
            keys=["synthesis", "claim"], temperature=0.7)
        cand = Candidate(move.key, str(data["synthesis"]).strip(), str(data["claim"]).strip(),
                         str(data.get("from_thesis", "")).strip(), str(data.get("from_antithesis", "")).strip(),
                         str(data.get("cost", "")).strip())
        self.emit("synthesise", {"move": move.key, "synthesis": cand.synthesis})
        return cand

    # 6. evaluate --------------------------------------------------------------------------------

    def evaluate(self, cand: Candidate, thesis: str, antithesis: str,
                 t_claims: list[str], a_claims: list[str]) -> Candidate:
        """Score a candidate with the NLI model only. Sentence-by-sentence checks are useless here, because a
        good synthesis names both sides and any NLI model reads that as a contradiction. So the candidate is
        judged through its one-line claim and the two things it says it keeps:
          grounding   what it says it keeps from each side really is in that side
          coherence   its claim does not contradict what it says it keeps
          novelty     it is not just one side restated
          mush        it does not collapse into 'both have a point' / 'it depends' (this one is a gate)
        """
        side = BY_KEY[cand.move].takes_side
        claim = cand.claim or first_sentences(cand.synthesis, 1)
        keeps = [(cand.from_thesis, thesis), (cand.from_antithesis, antithesis)]
        present = [(k, src) for k, src in keeps if k]
        pairs: list[tuple[str, str]] = []
        pairs += [(src, k) for k, src in present] + [(k, src) for k, src in present]       # grounding
        pairs += [(claim, k) for k, _ in present] + [(k, claim) for k, _ in present]       # coherence
        pairs += [(thesis, claim), (claim, thesis), (antithesis, claim), (claim, antithesis)]  # novelty
        pairs += [(cand.synthesis, m) for m in MUSH]                                       # mush
        rel = self.nli.relations(pairs)
        n = len(present)
        g = [1 - max(rel[i].contradiction, rel[n + i].contradiction) for i in range(n)]
        c = [1 - max(rel[2 * n + i].contradiction, rel[3 * n + i].contradiction) for i in range(n)]
        nv = rel[4 * n: 4 * n + 4]
        if side:   # a move that may reject one side only has to keep the side that stands
            grounding, coherence = max(g, default=0.0), max(c, default=0.0)
        else:      # every other move must keep something real from both sides
            grounding = sum(g) / 2
            coherence = min(c) if n == 2 else 0.0
        # Restating a side means mutual entailment with it; one-way entailment is fine.
        novelty = 1 - max(min(nv[0].entailment, nv[1].entailment), min(nv[2].entailment, nv[3].entailment))
        mush = max(r.entailment for r in rel[4 * n + 4:])
        if MUSH_PHRASES.search(cand.synthesis):
            mush = max(mush, 0.6)
        cand.scores = {k: round(v, 3) for k, v in dict(grounding=grounding, coherence=coherence,
                                                        novelty=novelty, mush=mush).items()}
        # Mush is a gate, not one factor among many: a compromise that is coherent is still a compromise.
        cand.score = round((0.3 * grounding + 0.35 * coherence + 0.35 * novelty) * (1 - mush), 4)
        self.emit("evaluate", {"move": cand.move, "scores": cand.scores, "score": cand.score})
        return cand

    # 7. object ----------------------------------------------------------------------------------

    def object(self, cand: Candidate) -> tuple[str, float]:
        objection = self.llm.ask(
            VOICE,
            f"Position: {cand.synthesis}\n\nState the single strongest objection to this position as one or two "
            "sentences that directly contradict it. Only the objection, nothing else.", temperature=0.6).strip()
        score = self.nli.contradiction(cand.synthesis, objection)
        self.emit("object", {"objection": objection, "tension": score})
        return objection, score

    # answer -------------------------------------------------------------------------------------

    def write_answer(self, question: str, rounds: list[Round], challenge: str = "") -> str:
        last = rounds[-1]
        best = last.best
        lines = [f"Question: {question}",
                 f"Original thesis: {rounds[0].thesis}",
                 f"Original antithesis: {rounds[0].antithesis}",
                 f"What it turns on: {rounds[0].crux}"]
        for n, r in enumerate(rounds[1:], 2):
            lines.append(f"Round {n} challenge: {r.antithesis}")
        lines += [f"Final resolution ({BY_KEY[best.move].name}): {best.synthesis}",
                  f"Kept from the thesis: {best.from_thesis}",
                  f"Kept from the antithesis: {best.from_antithesis}",
                  f"Cost: {best.cost}"]
        if last.objection and last.objection_tension >= self.tension_min * 0.6:
            lines.append(f"Strongest objection to the resolution: {last.objection}")
        if challenge:
            lines.append(f"The user just pushed back with: {challenge}\n"
                         "Your reply must answer that challenge head-on in its first two sentences. "
                         "If it asks a direct question, give a direct answer to it.")
        shape = ("Write the reply to the user in plain prose, 150 to 250 words, in this order. "
                 "First, the strongest honest case for each side, one or two sentences each, specific enough that "
                 "someone holding that view would recognise it. "
                 "Then your verdict, stated as a claim you stand behind: say which way it goes, or what both sides "
                 "get wrong, and why, naming what the disagreement really turns on. "
                 "Then the cost: what this verdict gives up, said plainly. "
                 "If an objection is listed, end by answering it in one or two sentences: say why the verdict holds "
                 "anyway, or exactly where it stops holding. Never end on an open question. ")
        rules = ("Talk about the subject itself: never use the words thesis, antithesis, synthesis or resolution, "
                 "and never describe your own process. No headings, no lists, no praise of the question. "
                 "Never write 'both have merits', 'balance', 'it depends', 'depends on the context', "
                 "'remains open', 'consider both' or 'the key is to recognise'.")
        if challenge:
            shape = shape.replace("First, the strongest", "After answering the challenge, give the strongest")
        answer = self.llm.ask(VOICE, "\n".join(lines) + "\n\n" + shape + rules, temperature=0.5)
        if self._mushy(answer):   # the writer can undo the synthesis by hedging; give it one strict retry
            answer = self.llm.ask(
                VOICE,
                "\n".join(lines) + f"\n\nThis draft hedged instead of committing:\n{answer}\n\n"
                "Rewrite it, 150 to 230 words: the strongest case for each side in a sentence or two, then a verdict "
                "you stand behind with the reason, then the cost, then why the verdict survives the objection. "
                "No 'both', no 'balance', no 'context', no 'merits', no 'remains open', no closing question.",
                temperature=0.4)
        self.emit("answer", {"answer": answer, "move": best.move, "move_name": BY_KEY[best.move].name, "cost": best.cost})
        return answer

    def _mushy(self, text: str) -> bool:
        if MUSH_PHRASES.search(text) or re.search(r"\b(have (their )?merits|balance between|specific context|depend(s|ing)? (up)?on (the )?(context|situation|circumstances))\b", text, re.I):
            return True
        return max(r.entailment for r in self.nli.relations([(text, m) for m in MUSH])) > 0.5

    # run ----------------------------------------------------------------------------------------

    def round(self, thesis: str, antithesis: str) -> Round:
        t_claims, a_claims = self.atomise(thesis, antithesis)
        score, core, _ = self.tension(t_claims, a_claims)
        crux, fits, moves = self.diagnose(thesis, antithesis, core, score)
        cands = [self.evaluate(self.synthesise(thesis, antithesis, crux, m), thesis, antithesis, t_claims, a_claims)
                 for m in moves]
        best = max(cands, key=lambda c: c.score)
        return Round(thesis, antithesis, t_claims, a_claims, score, core, crux, fits, cands, best)

    def run(self, text: str, context: str = "", recalled: list[str] | None = None,
            thesis: str | None = None, antithesis: str | None = None) -> Result:
        calls0, secs0 = self.llm.calls, self.llm.seconds
        objection, antithesis_in = bool(thesis and antithesis), antithesis or ""
        if thesis and antithesis:
            question, kind = text, "objection"
            self.emit("frame", {"question": text, "thesis": thesis, "antithesis": antithesis, "kind": kind})
        else:
            f = self.frame(text, context, recalled)
            question, kind, thesis, antithesis = f["question"], f["kind"], f["thesis"], f["antithesis"]
            if str(kind).lower() == "none":
                answer = self.llm.ask(VOICE, f"{context}\n\nUser: {text}\n\nAnswer briefly and directly.")
                self.emit("answer", {"answer": answer})
                return Result(question, "none", answer, [], self.llm.calls - calls0, self.llm.seconds - secs0)
        rounds: list[Round] = []
        for depth in range(self.max_depth):
            r = self.round(thesis, antithesis)
            rounds.append(r)
            r.objection, r.objection_tension = self.object(r.best)
            if r.objection_tension < self.tension_min or depth == self.max_depth - 1:
                break
            self.emit("recurse", {"depth": depth + 1, "thesis": r.best.synthesis, "antithesis": r.objection})
            thesis, antithesis = r.best.synthesis, r.objection
        answer = self.write_answer(question, rounds, challenge=antithesis_in if objection else "")
        return Result(question, kind, answer, rounds, self.llm.calls - calls0, self.llm.seconds - secs0)


def first_sentences(text: str, n: int = 2) -> str:
    return " ".join(split_sentences(text)[:n])
