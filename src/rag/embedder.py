import numpy as np
from sentence_transformers import SentenceTransformer


class Embedder:
    def __init__(self, model_name: str):
        self._model = SentenceTransformer(model_name)

    def embed_batch(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        vectors = self._model.encode(texts, batch_size=batch_size, convert_to_numpy=True)
        vectors_norm = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
        return vectors_norm.tolist()

    def embed_one(self, text: str) -> list[float]:
        return self.embed_batch([text])[0]
