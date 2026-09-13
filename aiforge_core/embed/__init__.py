"""Embedder (local MiniLM, 384 dims) and StubEmbedder (hash based, for tests)."""

import hashlib
import math

DIM = 384


class Embedder:
    """sentence-transformers all-MiniLM-L6-v2 on CPU. No key, no quota.

    Requires the `embeddings` extra: pip install "aiforge-core[embeddings]".
    """

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            raise RuntimeError(
                "sentence-transformers is not installed; "
                'install with pip install "aiforge-core[embeddings]"'
            ) from e
        self.model = SentenceTransformer(model_name, device="cpu")

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = self.model.encode(texts, normalize_embeddings=True)
        return [v.tolist() for v in vectors]

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]


class StubEmbedder:
    """Deterministic hash-based vectors, fixed size 384. Same text -> same vector.

    Token-overlap based, so texts sharing words land near each other — enough
    signal for offline tests without any model download.
    """

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_one(t) for t in texts]

    def embed_one(self, text: str) -> list[float]:
        vec = [0.0] * DIM
        for token in text.lower().split():
            h = int.from_bytes(hashlib.sha256(token.encode()).digest()[:8], "big")
            vec[h % DIM] += 1.0
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]
