from __future__ import annotations

import numpy as np
from sentence_transformers import SentenceTransformer

_model: SentenceTransformer | None = None


def init(model_name: str) -> None:
    global _model
    _model = SentenceTransformer(model_name)


def _get_model() -> SentenceTransformer:
    if _model is None:
        raise RuntimeError("Embedder not initialized — call init() first")
    return _model


def embed_batch(texts: list[str], batch_size: int = 32) -> list[list[float]]:
    model = _get_model()
    vectors = model.encode(texts, batch_size=batch_size, convert_to_numpy=True)
    vectors = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
    return vectors.tolist()


def embed_one(text: str) -> list[float]:
    return embed_batch([text])[0]
