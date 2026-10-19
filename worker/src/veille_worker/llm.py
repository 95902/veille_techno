"""Point d'appel unique à vLLM (API compatible OpenAI)."""

import json
from dataclasses import dataclass
from typing import Any

from openai import APIConnectionError, APIError, BadRequestError, OpenAI

from veille_worker.config import Settings
from veille_worker.db import Category

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


class LLMInvalidOutputError(RuntimeError):
    """Réponse hors schéma, ou requête refusée par vLLM pour cet article."""


@dataclass(frozen=True)
class Enrichment:
    title_fr: str
    summary: list[str]
    category: str


ENRICH_SYSTEM_PROMPT = (
    "Tu es un assistant de veille technologique sur l'intelligence artificielle, "
    "pour des lecteurs francophones (développeurs, chefs de projet, commerciaux, direction).\n"
    "À partir de l'article fourni, réponds uniquement avec un objet JSON contenant :\n"
    "- title_fr : le titre de l'article traduit en français naturel, sans guillemets ;\n"
    "- summary : exactement 3 phrases en français correct, une phrase par élément, "
    "factuelles, sans introduction (« Cet article… ») ni opinion ; garde les noms propres, "
    "noms de produits et sigles d'origine ;\n"
    "- category : l'identifiant de la catégorie la plus pertinente parmi :\n"
    "{categories}\n"
    "Choisis la catégorie qui correspond au sujet principal de l'article, même imparfaitement. "
    "« {fallback} » est un dernier recours : ne l'utilise que si aucune autre catégorie "
    "ne convient, même partiellement."
)

FALLBACK_CATEGORY = "autre"
# Bornes partagées par le schéma imposé à vLLM et la revalidation Python.
TITLE_MAX_CHARS = 300
SENTENCE_MAX_CHARS = 500


def enrichment_schema(slugs: list[str]) -> dict[str, Any]:
    """Schéma JSON imposé par décodage contraint : 3 phrases, catégorie parmi les slugs."""
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["title_fr", "summary", "category"],
        "properties": {
            "title_fr": {"type": "string", "minLength": 1, "maxLength": TITLE_MAX_CHARS},
            "summary": {
                "type": "array",
                "minItems": 3,
                "maxItems": 3,
                "items": {"type": "string", "minLength": 1, "maxLength": SENTENCE_MAX_CHARS},
            },
            "category": {"type": "string", "enum": slugs},
        },
    }


def build_enrich_messages(text: str, title: str, categories: list[Category]) -> list[dict]:
    lines = "\n".join(
        f"  - {c.slug} : {c.name}" + (f" — {c.description}" if c.description else "")
        for c in categories
    )
    slugs = [c.slug for c in categories]
    fallback = FALLBACK_CATEGORY if FALLBACK_CATEGORY in slugs else slugs[-1]
    return [
        {
            "role": "system",
            "content": ENRICH_SYSTEM_PROMPT.format(categories=lines, fallback=fallback),
        },
        {"role": "user", "content": f"Titre : {title}\n\nTexte :\n{text}"},
    ]


def enrich_fr(
    text: str,
    title: str,
    categories: list[Category],
    settings: Settings | None = None,
    client: OpenAI | None = None,
) -> Enrichment:
    """Titre FR, résumé de 3 phrases et slug de catégorie, en un seul appel vLLM."""
    if not categories:
        raise ValueError("aucune catégorie en base : impossible de classer l'article")
    settings = settings or Settings.from_env()
    client = client or make_client(settings)
    slugs = [c.slug for c in categories]
    try:
        response = client.chat.completions.create(
            model=settings.vllm_model,
            messages=build_enrich_messages(text, title, categories),
            temperature=0.2,
            max_tokens=settings.vllm_max_tokens,
            # Sortie structurée vLLM (API OpenAI) : décodage contraint par le schéma JSON.
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "article_enrichment",
                    "strict": True,
                    "schema": enrichment_schema(slugs),
                },
            },
            extra_body=NO_THINKING,
        )
    except BadRequestError as exc:  # requête refusée pour cet article (ex. contexte trop long)
        raise LLMInvalidOutputError(f"requête refusée par vLLM : {exc}") from exc
    except APIConnectionError as exc:  # inclut APITimeoutError
        raise LLMUnavailableError(f"vLLM injoignable à {settings.vllm_base_url} : {exc}") from exc
    except APIError as exc:
        raise LLMUnavailableError(
            f"vLLM a renvoyé une erreur pour le modèle {settings.vllm_model} : {exc}"
        ) from exc
    choice = response.choices[0]
    if choice.finish_reason == "length":
        raise LLMInvalidOutputError(
            f"sortie tronquée (max_tokens={settings.vllm_max_tokens} atteint)"
        )
    return parse_enrichment(choice.message.content or "", slugs)


def parse_enrichment(content: str, slugs: list[str]) -> Enrichment:
    """Revalide la sortie côté Python, sans se fier au seul décodage contraint."""
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise LLMInvalidOutputError(f"JSON invalide : {exc}") from exc
    if not isinstance(data, dict):
        raise LLMInvalidOutputError("la sortie n'est pas un objet JSON")

    title_fr = data.get("title_fr")
    if not isinstance(title_fr, str) or not title_fr.strip():
        raise LLMInvalidOutputError("title_fr manquant ou vide")
    if len(title_fr) > TITLE_MAX_CHARS:
        raise LLMInvalidOutputError(
            f"title_fr trop long ({len(title_fr)} caractères, maximum {TITLE_MAX_CHARS})"
        )

    summary = data.get("summary")
    if (
        not isinstance(summary, list)
        or len(summary) != 3
        or not all(isinstance(s, str) and s.strip() for s in summary)
    ):
        raise LLMInvalidOutputError("summary doit contenir exactement 3 phrases non vides")
    for sentence in summary:
        if len(sentence) > SENTENCE_MAX_CHARS:
            raise LLMInvalidOutputError(
                f"phrase de résumé trop longue ({len(sentence)} caractères,"
                f" maximum {SENTENCE_MAX_CHARS})"
            )

    category = data.get("category")
    if category not in slugs:
        raise LLMInvalidOutputError(f"catégorie inconnue : {category!r}")

    return Enrichment(
        title_fr=title_fr.strip(),
        summary=[s.strip() for s in summary],
        category=category,
    )
