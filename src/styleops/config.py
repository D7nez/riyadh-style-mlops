import os
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
ROOT = Path(os.getenv("PROJECT_ROOT", str(Path(__file__).resolve().parents[2])))
@dataclass
class Settings:
    backend: str = field(default_factory=lambda: os.getenv("MODEL_BACKEND", "mock"))
    retrieval: str = field(default_factory=lambda: os.getenv("RETRIEVAL_BACKEND", "tfidf"))
    model: str = field(default_factory=lambda: os.getenv("GENERATION_MODEL", "openai/gpt-oss-120b"))
    analysis_model: str = field(default_factory=lambda: os.getenv("ANALYSIS_MODEL", "openai/gpt-oss-20b"))
    embedding_model: str = field(default_factory=lambda: os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-base"))
    data: str = field(default_factory=lambda: os.getenv("DATA_PATH", str(ROOT / "data.csv")))
    prompt: str = field(default_factory=lambda: os.getenv("STYLE_PROMPT_PATH", str(ROOT / "prompts/style_v2.txt")))
    cache: str = field(default_factory=lambda: os.getenv("CACHE_PATH", str(ROOT / ".cache")))
    top_k: int = field(default_factory=lambda: int(os.getenv("TOP_K", "3")))
    temperature: float = field(default_factory=lambda: float(os.getenv("TEMPERATURE", "0.6")))
    ollama_url: str = field(default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
    ollama_timeout: float = field(default_factory=lambda: float(os.getenv("OLLAMA_TIMEOUT", "600")))
    ollama_context: int = field(default_factory=lambda: int(os.getenv("OLLAMA_NUM_CTX", "8192")))
    def validate(self):
        if self.backend not in {"mock", "groq", "ollama"}: raise ValueError("Invalid MODEL_BACKEND")
        if self.retrieval not in {"tfidf", "e5"}: raise ValueError("Invalid RETRIEVAL_BACKEND")
        if not 1 <= self.top_k <= 10: raise ValueError("TOP_K must be 1..10")
        if self.backend == "groq" and not os.getenv("GROQ_API_KEY"):
            raise ValueError("Set GROQ_API_KEY in .env")
        if self.ollama_context < 2048: raise ValueError("Invalid Ollama token limits")
        if self.ollama_timeout <= 0: raise ValueError("OLLAMA_TIMEOUT must be positive")
        from urllib.parse import urlsplit
        url=urlsplit(self.ollama_url)
        if url.scheme not in {"http","https"} or not url.hostname or url.username or url.password:
            raise ValueError("OLLAMA_BASE_URL must be an HTTP URL without credentials")
        return self