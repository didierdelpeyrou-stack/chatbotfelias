"""Configuration V2 — pydantic-settings.

Toutes les variables d'env sont déclarées ici, validées au boot.
Pas de string hardcodée en prod : le Settings échoue clairement si une
variable critique manque.

Usage :
    from app.settings import get_settings
    settings = get_settings()
    print(settings.claude_model)
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration de l'application V2.

    Hérité du fichier .env (cf. v2/.env.example).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore les vars non déclarées (V1 partage le .env)
    )

    # ── Application ──
    app_name: str = "Chatbot ELISFA V2"
    environment: Literal["development", "staging", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # ── Server ──
    host: str = "127.0.0.1"
    port: int = 8000  # Différent du V1 (8080) — cohabitation locale possible

    # ── Anthropic / Claude ──
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    claude_model: str = Field(default="claude-haiku-4-5-20251001", alias="CLAUDE_MODEL")
    claude_max_tokens: int = Field(default=2000, alias="CLAUDE_MAX_TOKENS")
    claude_timeout_seconds: float = 60.0

    # ── Voyage AI (Sprint 5.2-stack — embeddings sémantiques) ──
    # Si vide, fallback gracieux sur TF-IDF seul (pas d'embeddings).
    voyage_api_key: str = Field(default="", alias="VOYAGE_API_KEY")
    voyage_model: str = Field(default="voyage-3-large", alias="VOYAGE_MODEL")
    # α : pondération hybride score = α·tfidf_norm + (1-α)·cosine_sim
    # 0.0 = embeddings seuls, 1.0 = TF-IDF seul. Calibré via grid search.
    rag_hybrid_alpha: float = Field(default=0.5, alias="RAG_HYBRID_ALPHA")
    # Si tfidf_normalized > seuil, on skip les embeddings (gain latence)
    rag_skip_embedding_threshold: float = Field(default=0.85, alias="RAG_SKIP_EMBEDDING_THRESHOLD")

    # ── RAG ──
    # Cf. audit RAG 2026-04-21 : seuils calibrés Sprint 4 (benchmark V1↔V2).
    rag_top_k: int = 5
    rag_score_min_hors_corpus: float = 1.5
    rag_max_liens_par_reponse: int = 6
    rag_max_fiches_par_reponse: int = 5

    # ── Observability ──
    metrics_port: int = 9092  # Différent de Félias (9091) pour éviter collision
    metrics_enabled: bool = True

    # ── KB ──
    kb_data_dir: str = "../data"  # Réutilise les KB du V1 pendant la cohabitation
    # Sprint 4.6 — chemin séparé pour le cache embeddings (write nécessaire).
    # Si vide → cache écrit dans kb_data_dir (legacy). En staging Docker, le KB
    # est mounté :ro et le cache va dans un volume RW dédié (/app/var/embeddings).
    embedding_cache_dir: str = Field(default="", alias="EMBEDDING_CACHE_DIR")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Settings singleton — chargé une fois, mis en cache."""
    return Settings()
