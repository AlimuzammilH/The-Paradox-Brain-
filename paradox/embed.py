"""Sentence embeddings for memory recall."""
from __future__ import annotations

import numpy as np

from . import config


class Embedder:
    def __init__(self, model: str = config.EMBED_MODEL, device: str = config.DEVICE):
        self.model_name, self.device = model, device
        self._model = None

    def encode(self, texts: list[str]) -> np.ndarray:
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name, device=self.device)
        vecs = np.asarray(self._model.encode(texts, normalize_embeddings=True), dtype=np.float32)
        return vecs
