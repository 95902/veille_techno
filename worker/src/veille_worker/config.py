"""Configuration du worker, lue dans les variables d'environnement."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    vllm_base_url: str
    vllm_model: str
    vllm_timeout: float

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            vllm_base_url=os.environ.get("VLLM_BASE_URL", "http://localhost:8000/v1"),
            vllm_model=os.environ.get("VLLM_MODEL", "Qwen/Qwen3-8B-AWQ"),
            vllm_timeout=float(os.environ.get("VLLM_TIMEOUT", "120")),
        )
