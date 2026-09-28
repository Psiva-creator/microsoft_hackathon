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
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS embedding_cache (
                    hash TEXT PRIMARY KEY,
                    vector TEXT NOT NULL
                )
                """
            )

    def get(self, text: str) -> list[float] | None:
        h = hashlib.sha256(text.encode("utf-8")).hexdigest()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT vector FROM embedding_cache WHERE hash = ?", (h,))
            row = cursor.fetchone()
            if row:
                return json.loads(row[0])
        return None

    def set(self, text: str, vector: list[float]) -> None:
        h = hashlib.sha256(text.encode("utf-8")).hexdigest()
        vec_str = json.dumps(vector)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO embedding_cache (hash, vector) VALUES (?, ?)",
                (h, vec_str),
            )


class LocalBGEEmbedder:
    """Local embedder using BAAI/bge-small-en-v1.5 and sentence-transformers with caching."""

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5", dim: int = 384):
        self.model_name = model_name
        self.dim = dim
        self._model = None
        self.cache = SQLiteEmbeddingCache()

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
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
