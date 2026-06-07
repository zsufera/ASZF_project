from dataclasses import dataclass
import os


@dataclass
class Settings:
    provider: str = os.getenv("PROVIDER", "cloud")
    sqlite_path: str = os.getenv("SQLITE_PATH", "data/app.db")
    qdrant_url: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    qdrant_mode: str = os.getenv("QDRANT_MODE", "local")
    qdrant_path: str = os.getenv("QDRANT_PATH", "data/qdrant_local")
    openai_embed_dim: int | None = (
        int(os.environ["OPENAI_EMBED_DIM"]) if os.getenv("OPENAI_EMBED_DIM") else None
    )
    ollama_url: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    confidence_threshold: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.75"))
    sla_fallback_days: int = int(os.getenv("SLA_FALLBACK_DAYS", "30"))
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4.1")
    openai_embed_model: str = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-large")
    langfuse_enabled: bool = os.getenv("LANGFUSE_ENABLED", "false").lower() == "true"
    langfuse_host: str = os.getenv("LANGFUSE_HOST", "http://localhost:3000")
    trace_dir: str = os.getenv("TRACE_DIR", "data/traces")


settings = Settings()
