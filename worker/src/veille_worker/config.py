"""Configuration du worker, lue dans les variables d'environnement."""

import os
from dataclasses import dataclass

USER_AGENT = "veille-techno-worker/0.1 (veille IA interne INNOSYS)"


@dataclass(frozen=True)
class Settings:
    vllm_base_url: str = "http://localhost:8000/v1"
    vllm_model: str = "Qwen/Qwen3-8B-AWQ"
    vllm_timeout: float = 120
    # Tokens de sortie : titre + 3 phrases tiennent largement en 700 (JSON compris).
    vllm_max_tokens: int = 700
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "veille"
    db_user: str = "veille_worker"
    db_password: str = ""
    http_timeout: float = 20
    # Fenêtre de collecte en jours. Premier passage d'une source (aucun article en base) :
    # entrées datées de la fenêtre seulement ; ensuite, entrées non datées admises en plus.
    first_run_days: int = 7
    # Un article en échec est retenté aux collectes suivantes jusqu'à ce nombre d'essais.
    max_attempts: int = 3
    # Texte envoyé au LLM, en caractères. ~12 000 caractères ≈ 3 000 à 4 000 tokens : avec le
    # prompt (~800) et la sortie (700), la requête reste sous VLLM_MAX_MODEL_LEN=8192.
    max_input_chars: int = 12_000
    # En dessous, le texte extrait de la page est jugé raté : repli sur le contenu du flux.
    min_extracted_chars: int = 500
    # En dessous, aucun texte n'est exploitable : l'article passe en échec.
    min_text_chars: int = 150

    @classmethod
    def from_env(cls) -> "Settings":
        env = os.environ.get
        return cls(
            vllm_base_url=env("VLLM_BASE_URL", cls.vllm_base_url),
            vllm_model=env("VLLM_MODEL", cls.vllm_model),
            vllm_timeout=float(env("VLLM_TIMEOUT", str(cls.vllm_timeout))),
            vllm_max_tokens=int(env("VLLM_MAX_TOKENS", str(cls.vllm_max_tokens))),
            db_host=env("DB_HOST", cls.db_host),
            db_port=int(env("DB_PORT", str(cls.db_port))),
            db_name=env("DB_DATABASE", cls.db_name),
            db_user=env("DB_USERNAME", cls.db_user),
            db_password=env("WORKER_DB_PASSWORD", cls.db_password),
            http_timeout=float(env("COLLECT_HTTP_TIMEOUT", str(cls.http_timeout))),
            max_input_chars=int(env("COLLECT_MAX_INPUT_CHARS", str(cls.max_input_chars))),
        )
