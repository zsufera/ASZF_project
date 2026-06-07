from dataclasses import dataclass
import os


@dataclass
class Settings:
    provider: str = os.getenv("PROVIDER", "cloud")
    sqlite_path: str = os.getenv("SQLITE_PATH", "data/app.db")
    qdrant_url: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    ollama_url: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    confidence_threshold: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.75"))
    sla_fallback_days: int = int(os.getenv("SLA_FALLBACK_DAYS", "30"))
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4.1")
    openai_embed_model: str = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-large")


settings = Settings()
