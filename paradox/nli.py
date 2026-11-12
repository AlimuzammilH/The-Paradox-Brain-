"""Contradiction scoring with a natural-language-inference model.

The language model writes; this model judges. It is a small cross-encoder trained only to answer
"does sentence B contradict, follow from, or say nothing about sentence A?", so it cannot be talked
into calling something a contradiction. That separation is what keeps Paradox from grading itself.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np

from . import config


@dataclass
class Relation:
    contradiction: float
    entailment: float
    neutral: float


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z\"'(])", text.strip())
    return [p.strip() for p in parts if len(p.strip()) > 3]


class NLI:
    def __init__(self, model: str = config.NLI_MODEL, device: str = config.DEVICE):
        self.model_name, self.device = model, device
        self._model = None
        self._labels: list[str] | None = None

    def _load(self):
        if self._model is None:
            from sentence_transformers import CrossEncoder
            try:  # full precision: half precision on a CPU is slower, not faster
                self._model = CrossEncoder(self.model_name, device=self.device, model_kwargs={"dtype": "float32"})
            except TypeError:
                self._model = CrossEncoder(self.model_name, device=self.device)
            id2label = getattr(self._model.model.config, "id2label", None) or {}
            labels = [str(id2label.get(i, "")).lower() for i in range(len(id2label))]
            # The common NLI cross-encoders use contradiction / entailment / neutral in this order.
            self._labels = labels if set(labels) >= {"contradiction", "entailment", "neutral"} \
                else ["contradiction", "entailment", "neutral"]
        return self._model

    def relations(self, pairs: list[tuple[str, str]]) -> list[Relation]:
        if not pairs:
            return []
        logits = np.asarray(self._load().predict(pairs, apply_softmax=False))
        logits = logits - logits.max(axis=1, keepdims=True)
        probs = np.exp(logits) / np.exp(logits).sum(axis=1, keepdims=True)
        idx = {name: self._labels.index(name) for name in ("contradiction", "entailment", "neutral")}
        return [Relation(float(p[idx["contradiction"]]), float(p[idx["entailment"]]), float(p[idx["neutral"]]))
                for p in probs]

    # Convenience helpers built on relations(); fakes in the tests only need to implement relations().

    def contradiction(self, a: str, b: str) -> float:
        """Symmetric contradiction score: NLI is directional, so take the stronger of both directions."""
        r1, r2 = self.relations([(a, b), (b, a)])
        return max(r1.contradiction, r2.contradiction)

    def matrix(self, left: list[str], right: list[str]) -> np.ndarray:
        pairs = [(a, b) for a in left for b in right] + [(b, a) for a in left for b in right]
        rel = self.relations(pairs)
        n = len(left) * len(right)
        fwd = np.array([r.contradiction for r in rel[:n]]).reshape(len(left), len(right))
        bwd = np.array([r.contradiction for r in rel[n:]]).reshape(len(left), len(right))
        return np.maximum(fwd, bwd)

    def self_contradiction(self, text: str) -> float:
        """Highest contradiction between any two sentences of one text: 0 means internally consistent."""
        sents = split_sentences(text)[:12]
        pairs = [(sents[i], sents[j]) for i in range(len(sents)) for j in range(len(sents)) if i != j]
        rel = self.relations(pairs)
        return max((r.contradiction for r in rel), default=0.0)

    def entails(self, premise: str, hypothesis: str) -> float:
        return self.relations([(premise, hypothesis)])[0].entailment
