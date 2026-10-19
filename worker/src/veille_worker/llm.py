"""Point d'appel unique à vLLM (API compatible OpenAI)."""

from openai import APIConnectionError, APIError, OpenAI

from veille_worker.config import Settings

SUMMARY_SYSTEM_PROMPT = (
    "Tu es un assistant de veille technologique. "
    "Résume le texte fourni en français, en 3 phrases, sans introduction ni commentaire."
)

# Qwen3 raisonne par défaut ; un résumé n'en a pas besoin.
NO_THINKING = {"chat_template_kwargs": {"enable_thinking": False}}


class LLMUnavailableError(RuntimeError):
    """vLLM est injoignable, n'a pas répondu à temps ou a renvoyé une erreur."""


def make_client(settings: Settings) -> OpenAI:
    # vLLM n'a pas d'authentification ; le client exige néanmoins une clé.
    return OpenAI(base_url=settings.vllm_base_url, api_key="unused", timeout=settings.vllm_timeout)


def summarize_fr(text: str, settings: Settings | None = None, client: OpenAI | None = None) -> str:
    settings = settings or Settings.from_env()
    client = client or make_client(settings)
    try:
        response = client.chat.completions.create(
            model=settings.vllm_model,
            messages=[
                {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            temperature=0.3,
            extra_body=NO_THINKING,
        )
    except APIConnectionError as exc:  # inclut APITimeoutError
        raise LLMUnavailableError(f"vLLM injoignable à {settings.vllm_base_url} : {exc}") from exc
    except APIError as exc:  # APIStatusError (modèle non servi, 4xx/5xx), réponse invalide
        raise LLMUnavailableError(
            f"vLLM a renvoyé une erreur pour le modèle {settings.vllm_model} : {exc}"
        ) from exc
    return (response.choices[0].message.content or "").strip()
