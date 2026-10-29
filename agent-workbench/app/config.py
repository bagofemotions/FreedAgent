import os
from dataclasses import dataclass

def env(name, default=""):
    return os.getenv(name, default).strip()

@dataclass(frozen=True)
class Settings:
    data_dir: str = env("DATA_DIR", "/data")
    workspace_dir: str = env("WORKSPACE_DIR", "/workspace")
    providers: tuple = tuple(x.strip() for x in env("MODEL_PROVIDERS").split(",") if x.strip())
    timeout: float = float(env("MODEL_TIMEOUT_SECONDS", "60"))
    max_attempts: int = max(1, int(env("MAX_MODEL_ATTEMPTS", "3")))
    sandbox_url: str = env("SANDBOX_URL", "http://sandbox:8090")
    research_max_bytes: int = int(env("RESEARCH_MAX_BYTES", "1500000"))
    sandbox_max_seconds: int = int(env("SANDBOX_MAX_SECONDS", "120"))

settings = Settings()
