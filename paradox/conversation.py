"""A conversation with Paradox.

Every message is one of four things:
  new        a new claim, question, dilemma or paradox: run the full dialectic
  objection  you push back on the last answer: your objection becomes the next antithesis,
             and the last synthesis becomes the thesis (the dialectic continues with you as the opponent)
  explain    you ask how it got there: it walks you through its own trace (it does not explain unasked)
  chat       anything else: a short plain reply
"""
from __future__ import annotations

import json
import re
import time
import uuid
from dataclasses import dataclass
from types import SimpleNamespace

from .engine import VOICE, Dialectic, Emit, Result
from .llm import LLM
from .memory import Memory
from .nli import NLI
from .patterns import BY_KEY

OBJECTION = re.compile(r"^\s*(no\b|nope|wrong|that'?s (wrong|not|false|bullshit)|that’s (wrong|not|false)|i disagree|disagree|but\b|not true|"
                       r"rubbish|nonsense|you'?re wrong|you’re wrong)", re.I)
EXPLAIN = re.compile(r"^\s*(/why|why\b|how did you|explain (your|that|this|how)|show (me )?(your|the) (reasoning|working|steps))", re.I)


@dataclass
class Reply:
    text: str
    intent: str
    conclusion_id: int | None = None
    result: Result | None = None


class Session:
    def __init__(self, llm: LLM, nli: NLI, memory: Memory, session_id: str | None = None, emit: Emit | None = None,
                 **engine_kwargs):
        self.llm, self.nli, self.memory = llm, nli, memory
        self.id = session_id or uuid.uuid4().hex[:12]
        self.engine = Dialectic(llm, nli, weights=memory.move_weight, emit=emit, **engine_kwargs)
        self.last: Result | None = None
        self.last_id: int | None = None
        self.restored = False
        self._restore()

    def _restore(self) -> None:
        """After a restart, reload the last answer of this session so pushback still lands on it."""
        row = self.memory.last_conclusion(self.id)
        if row is None:
            return
        answer = self.memory.db.execute("SELECT text FROM turns WHERE session=? AND role='paradox' ORDER BY id DESC LIMIT 1",
                                        (self.id,)).fetchone()["text"]
        final = SimpleNamespace(synthesis=row["synthesis"], move=row["move"], cost=row["cost"] or "")
        self.last = SimpleNamespace(question=row["question"], answer=answer, rounds=[final], final=final)
        self.last_id = row["id"]
        self.restored = True

    def _context(self) -> str:
        return "\n".join(f"{r['role']}: {r['text']}" for r in self.memory.recent(self.id, 6))

    def classify(self, text: str) -> str:
        if self.last is None or not self.last.rounds:
            return "new"
        if EXPLAIN.search(text):
            return "explain"
        if OBJECTION.search(text):   # don't leave an obvious pushback to the model's judgement
            return "objection"
        data = self.llm.ask_json(
            VOICE,
            f"Your last answer: {self.last.answer}\n\nUser now says: {text}\n\n"
            'Classify the user message. "objection": it disagrees with or challenges your last answer. '
            '"explain": it asks how or why you reached it. "new": it raises a different claim, question or '
            'dilemma. "chat": anything else.\nReturn key "intent".', keys=["intent"], temperature=0.0)
        intent = str(data["intent"]).lower().strip()
        if intent == "objection":
            # The small model calls almost anything an objection. Only accept it if the message really
            # contradicts the last synthesis; otherwise it is a new question.
            if self.nli.contradiction(self.last.final.synthesis, text) < 0.4:
                return "new"
        return intent if intent in {"new", "objection", "explain", "chat"} else "new"

    def send(self, text: str) -> Reply:
        intent = self.classify(text)
        context = self._context()
        self.memory.add_turn(self.id, "user", text)
        if intent == "explain":
            reply = Reply(self.explain(), intent, self.last_id, self.last)
        elif intent == "chat":
            reply = Reply(self.llm.ask(VOICE, f"{context}\nuser: {text}\n\nReply briefly and plainly."), intent)
        else:
            if intent == "objection":
                best = self.last.final
                result = self.engine.run(self.last.question, context, thesis=best.synthesis, antithesis=text)
            else:
                recalled = [f"{h['question']} -> {h['synthesis']}" for h in self.memory.recall(text)]
                result = self.engine.run(text, context, recalled)
            self._keep_trace(text, intent, result)
            cid = None
            if result.rounds:
                first, best = result.rounds[0], result.final
                cid = self.memory.save(result.question, first.thesis, first.antithesis, best.move,
                                       best.synthesis, best.cost, best.score)
                self.last, self.last_id, self.restored = result, cid, False
            reply = Reply(result.answer, intent, cid, result)
        self.memory.add_turn(self.id, "paradox", reply.text, reply.conclusion_id)
        return reply

    def _keep_trace(self, text: str, intent: str, result: Result) -> None:
        """Every answer's full reasoning goes to HOME/traces as JSON, so runs can be inspected and tuned."""
        try:
            from . import config
            folder = config.HOME / "traces"
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / f"{time.strftime('%Y%m%d-%H%M%S')}-{self.id}.json"
            path.write_text(json.dumps({"input": text, "intent": intent, "model": self.llm.model, **result.to_dict()},
                                       ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        except Exception:
            pass   # tracing must never break a conversation

    def rate(self, rating: int, note: str = "", conclusion_id: int | None = None) -> None:
        cid = conclusion_id or self.last_id
        if cid is None:
            raise ValueError("nothing to rate yet")
        self.memory.rate(cid, rating, note)

    def trace(self) -> str:
        """The raw reasoning trace, without the language model in between."""
        if not self.last or not self.last.rounds:
            return "No reasoning to show yet."
        if self.restored:
            return (f"Question: {self.last.question}\nThe detailed reasoning for this answer was in an earlier run.\n"
                    f"Final synthesis ({self.last.final.move}): {self.last.final.synthesis}")
        out = [f"Question: {self.last.question}"]
        for n, r in enumerate(self.last.rounds, 1):
            out += [f"\nRound {n}",
                    f"  thesis      {r.thesis}",
                    f"  antithesis  {r.antithesis}",
                    f"  core clash  \"{r.core[0]}\" vs \"{r.core[1]}\"  (contradiction {r.tension:.2f})",
                    f"  crux        {r.crux}"]
            for c in sorted(r.candidates, key=lambda c: -c.score):
                mark = "*" if c is r.best else " "
                out.append(f"  {mark} {BY_KEY[c.move].name:<28} score {c.score:.2f}  {c.scores}")
            out.append(f"  objection   {r.objection}  (contradiction {r.objection_tension:.2f})")
        out.append(f"\n{self.last.calls} model calls, {self.last.seconds:.0f}s")
        return "\n".join(out)

    def explain(self) -> str:
        return self.llm.ask(
            VOICE,
            f"This is the trace of how you reached your last answer:\n{self.trace()}\n\nYour answer was:\n"
            f"{self.last.answer}\n\nExplain to the user, in plain prose, how you got there: what the clash was, "
            "which kind of resolution you chose and why it beat the alternatives, and what objection was tested. "
            "Under 200 words.")
