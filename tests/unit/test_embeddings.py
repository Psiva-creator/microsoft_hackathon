import os
import tempfile

from app.core.embeddings import LocalBGEEmbedder, SQLiteEmbeddingCache, get_embedder


def test_sqlite_embedding_cache():
    f = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
    db_path = f.name
    f.close()

    try:
        cache = SQLiteEmbeddingCache(db_path=db_path)
        text = "HikariPool connection timeout error"
        fake_vector = [0.123] * 384

        assert cache.get(text) is None
        cache.set(text, fake_vector)
        cached = cache.get(text)
        assert cached is not None
        assert len(cached) == 384
        assert cached[0] == 0.123
    finally:
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except Exception:
                pass


def test_embedder_factory():
    embedder = get_embedder()
    assert embedder.dim == 384
    assert isinstance(embedder, LocalBGEEmbedder)


def test_real_embedding_length_and_cache():
    embedder = get_embedder()
    vec = embedder.embed_query("checkout-api pool timeout")
    assert len(vec) == 384
    # Verify cached retrieval
    vec2 = embedder.embed_query("checkout-api pool timeout")
    assert vec == vec2
