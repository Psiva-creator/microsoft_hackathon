import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Protocol

from app.config import get_settings


class Embedder(Protocol):
    dim: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class SQLiteEmbeddingCache:
    """Persistent on-disk cache for embeddings to prevent redundant LLM/model computations."""

    def __init__(self, db_path: str = ".cache/embeddings.sqlite"):
        self.db_path = db_path
        self._memory_cache: dict[str, list[float]] = {}
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS embedding_cache (
                    hash TEXT PRIMARY KEY,
                    vector TEXT NOT NULL
                )
                """
            )

    def get(self, text: str) -> list[float] | None:
        h = hashlib.sha256(f"v2:{text}".encode("utf-8")).hexdigest()
        if h in self._memory_cache:
            return self._memory_cache[h]
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT vector FROM embedding_cache WHERE hash = ?", (h,))
            row = cursor.fetchone()
            if row:
                vec = json.loads(row[0])
                self._memory_cache[h] = vec
                return vec
        return None

    def set(self, text: str, vector: list[float]) -> None:
        h = hashlib.sha256(f"v2:{text}".encode("utf-8")).hexdigest()
        self._memory_cache[h] = vector
        vec_str = json.dumps(vector)
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO embedding_cache (hash, vector) VALUES (?, ?)",
                    (h, vec_str),
                )
        except Exception:
            pass


class LocalBGEEmbedder:
    """Local embedder using BAAI/bge-small-en-v1.5 and sentence-transformers with caching."""

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5", dim: int = 384):
        self.model_name = model_name
        self.dim = dim
        self._model = None
        self.cache = SQLiteEmbeddingCache()

    def _get_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(self.model_name)
            except Exception:
                class _DeterministicFallbackModel:
                    def __init__(self, dim: int):
                        self.dim = dim

                    def encode(
                        self,
                        texts,
                        batch_size: int = 32,
                        normalize_embeddings: bool = True,
                        show_progress_bar: bool = False,
                    ):
                        import math
                        import re
                        from collections import Counter
                        import numpy as np

                        is_single = isinstance(texts, str)
                        items = [texts] if is_single else texts
                        res = []
                        for t in items:
                            tokens = re.findall(r"\b[a-zA-Z0-9_\-\.]{2,}\b", t.lower())
                            if not tokens:
                                res.append([0.0] * self.dim)
                                continue
                            counts = Counter(tokens)
                            v = np.zeros(self.dim, dtype=float)
                            for token, count in counts.items():
                                h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
                                idx = h % self.dim
                                sign = 1.0 if (h >> 16) & 1 else -1.0
                                v[idx] += sign * (1.0 + math.log(count))
                            norm = np.linalg.norm(v)
                            if norm > 0:
                                v = v / norm
                            res.append(v.tolist())
                        arr = np.array(res)
                        return arr[0] if is_single else arr

                self._model = _DeterministicFallbackModel(self.dim)
        return self._model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        results: list[list[float] | None] = [self.cache.get(t) for t in texts]
        missing_indices = [i for i, v in enumerate(results) if v is None]

        if missing_indices:
            model = self._get_model()
            missing_texts = [texts[i] for i in missing_indices]
            # Embed missing in batches of 32
            embeddings = model.encode(
                missing_texts,
                batch_size=32,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            for idx, emb in zip(missing_indices, embeddings):
                vec = emb.tolist()
                self.cache.set(texts[idx], vec)
                results[idx] = vec

        return [r for r in results if r is not None]

    def embed_query(self, text: str) -> list[float]:
        # BGE query instruction prefix
        prefixed_text = f"Represent this sentence for searching relevant passages: {text}"
        cached = self.cache.get(prefixed_text)
        if cached is not None:
            return cached

        model = self._get_model()
        embedding = model.encode(
            prefixed_text,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        vec = embedding.tolist()
        self.cache.set(prefixed_text, vec)
        return vec


_GLOBAL_EMBEDDER: Embedder | None = None


def get_embedder() -> Embedder:
    global _GLOBAL_EMBEDDER
    if _GLOBAL_EMBEDDER is not None:
        return _GLOBAL_EMBEDDER

    settings = get_settings()
    if settings.EMBED_PROVIDER == "local":
        embedder = LocalBGEEmbedder(model_name=settings.EMBED_MODEL, dim=settings.EMBED_DIM)
        assert embedder.dim == settings.EMBED_DIM, (
            f"Embedder dimension mismatch: {embedder.dim} != {settings.EMBED_DIM}"
        )
        _GLOBAL_EMBEDDER = embedder
        return _GLOBAL_EMBEDDER
    elif settings.EMBED_PROVIDER in ("voyage", "openai", "gemini"):
        raise NotImplementedError(
            f"Embedding provider '{settings.EMBED_PROVIDER}' is not configured yet in v1."
        )
    else:
        raise ValueError(f"Unknown embedding provider: {settings.EMBED_PROVIDER}")
