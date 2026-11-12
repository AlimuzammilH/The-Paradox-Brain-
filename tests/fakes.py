"""Deterministic stand-ins for the language model and the NLI model."""
import json
import re

import numpy as np

from paradox.nli import NLI, Relation


class FakeLLM:
    def __init__(self, objection_contradicts=False, frame_kind="dilemma"):
        self.calls, self.seconds, self.model, self.url = 0, 0.0, "fake", "fake://"
        self.objection_contradicts = objection_contradicts
        self.frame_kind = frame_kind
        self.prompts = []

    def chat(self, messages, json_mode=False, temperature=None, max_tokens=None):
        self.calls += 1
        p = messages[-1]["content"]
        self.prompts.append(p)
        if "Find the tension" in p:
            return json.dumps({"question": "Is freedom individual or collective?",
                               "thesis": "Freedom requires individualism.",
                               "antithesis": "Freedom requires collective action.", "kind": self.frame_kind})
        if "Break each side" in p:
            return json.dumps({"thesis_claims": ["Freedom is individual.", "The state limits people."],
                               "antithesis_claims": ["Freedom is not individual.", "People act together."]})
        if "Rate how well each move fits" in p:
            return json.dumps({"crux": "Who the subject of freedom is.",
                               "fits": {"levels": 9, "sublation": 7, "tradeoff": 2, "one_wrong": 1}})
        if "Resolve this with one specific move" in p:
            move = re.search(r"one specific move: (.+?)\.", p).group(1)
            return json.dumps({"synthesis": f"Synthesis by {move}. Individuals are free only inside institutions they build together.",
                               "claim": "Individuals are free only inside institutions they build together.",
                               "from_thesis": "Freedom is individual.", "from_antithesis": "People act together.", "cost": "speed"})
        if "strongest objection" in p:
            return "Institutions are not free." if self.objection_contradicts else "Some institutions are slow."
        if "Classify the user message" in p:
            return json.dumps({"intent": "objection" if "wrong" in p.lower() else "chat"})
        if "Write the reply to the user" in p:
            return "Freedom lives at two levels."
        return "plain reply"

    def ask(self, system, user, temperature=None):
        return self.chat([{"role": "system", "content": system}, {"role": "user", "content": user}])

    def ask_json(self, system, user, keys=None, temperature=None, retries=2):
        data = json.loads(self.chat([{"role": "user", "content": user}], json_mode=True))
        assert all(k in data for k in keys or []), (keys, data)
        return data


class FakeNLI(NLI):
    """Contradiction when exactly one side contains 'not'; entailment when the hypothesis is contained."""

    def __init__(self):
        super().__init__()

    def relations(self, pairs):
        out = []
        for a, b in pairs:
            neg = (" not " in f" {a.lower()} ") != (" not " in f" {b.lower()} ")
            ent = b.lower().strip(".") in a.lower()
            c = 0.9 if neg else 0.05
            e = 0.9 if ent and not neg else 0.05
            out.append(Relation(c, e, max(0.0, 1 - c - e)))
        return out


class FakeEmbedder:
    def encode(self, texts):
        vecs = []
        for t in texts:
            v = np.zeros(64, dtype=np.float32)
            for w in re.findall(r"\w+", t.lower()):
                v[hash(w) % 64] += 1
            vecs.append(v / (np.linalg.norm(v) or 1))
        return np.stack(vecs)
