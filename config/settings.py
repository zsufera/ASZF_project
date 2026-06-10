from dataclasses import dataclass, field
import os

try:
    from dotenv import find_dotenv, load_dotenv

    # Load .env (searched from the current working directory upward) into the
    # process environment before the dataclass defaults below read it.
    # Does not override variables already set in the environment.
    load_dotenv(find_dotenv(usecwd=True))
except ImportError:  # python-dotenv optional at runtime
    pass


def _optional_int_env(name: str) -> int | None:
    value = os.getenv(name)
    return int(value) if value else None


@dataclass
class Settings:
    provider: str = os.getenv("PROVIDER", "cloud")
    sqlite_path: str = os.getenv("SQLITE_PATH", "data/app.db")
    qdrant_url: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    qdrant_mode: str = os.getenv("QDRANT_MODE", "local")
    qdrant_path: str = os.getenv("QDRANT_PATH", "data/qdrant_local")
    openai_embed_dim: int | None = field(default_factory=lambda: _optional_int_env("OPENAI_EMBED_DIM"))
    ollama_url: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    confidence_threshold: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.75"))
    sla_fallback_days: int = int(os.getenv("SLA_FALLBACK_DAYS", "30"))
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4.1")
    openai_embed_model: str = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-large")
    llm_enabled: bool = os.getenv("LLM_ENABLED", "true").lower() == "true"
    # LLM-alapú groundedness-ellenőrzés (faithfulness judge) a verify lépésben.
    # +1 LLM-hívás/futás; kikapcsolható, ha a latencia fontosabb a pontos verify-jelzésnél.
    llm_verify_enabled: bool = os.getenv("LLM_VERIFY_ENABLED", "true").lower() == "true"
    # LLM-as-judge in the reference-free eval: dimension-level draft scoring.
    # +1 LLM call per eval sample; disabled runs keep only the heuristic judge.
    llm_judge_enabled: bool = os.getenv("LLM_JUDGE_ENABLED", "true").lower() == "true"
    openai_temperature: float = float(os.getenv("OPENAI_TEMPERATURE", "0.2"))
    langfuse_enabled: bool = os.getenv("LANGFUSE_ENABLED", "false").lower() == "true"
    langfuse_host: str = os.getenv("LANGFUSE_HOST", "http://localhost:3000")
    trace_dir: str = os.getenv("TRACE_DIR", "data/traces")

    grounding_token_overlap: float = float(os.getenv("GROUNDING_TOKEN_OVERLAP", "0.3"))
    retrieval_sparse_weight: float = float(os.getenv("RETRIEVAL_SPARSE_WEIGHT", "0.55"))
    retrieval_dense_weight: float = float(os.getenv("RETRIEVAL_DENSE_WEIGHT", "0.45"))
    retrieval_category_boost: float = float(os.getenv("RETRIEVAL_CATEGORY_BOOST", "0.2"))
    retrieval_section_boost: float = float(os.getenv("RETRIEVAL_SECTION_BOOST", "0.1"))


settings = Settings()
