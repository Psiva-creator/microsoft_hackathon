from app.config import get_settings


def test_settings_loaded() -> None:
    settings = get_settings()
    assert settings.EMBED_DIM == 384
    assert settings.ALLOW_ACTIONS is False
    assert settings.DATABASE_URL.startswith("postgresql://")
    assert settings.REDIS_URL.startswith("redis://")
