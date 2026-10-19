import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from helpers import CATEGORIES
from openai import APIConnectionError, BadRequestError, NotFoundError

from veille_worker.config import Settings
from veille_worker.llm import (
    LLMInvalidOutputError,
    LLMUnavailableError,
    enrich_fr,
    parse_enrichment,
    summarize_fr,
)

SETTINGS = Settings(vllm_base_url="http://vllm:8000/v1", vllm_model="test-model", vllm_timeout=5)


def fake_client(content: str | None, finish_reason: str = "stop") -> MagicMock:
    client = MagicMock()
    message = SimpleNamespace(content=content)
    client.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=message, finish_reason=finish_reason)]
    )
    return client


def test_sends_configured_model_with_thinking_disabled():
    client = fake_client("  Un résumé.  ")

    summary = summarize_fr("Some text", settings=SETTINGS, client=client)

    assert summary == "Un résumé."
    kwargs = client.chat.completions.create.call_args.kwargs
    assert kwargs["model"] == "test-model"
    assert kwargs["extra_body"] == {"chat_template_kwargs": {"enable_thinking": False}}
    assert kwargs["messages"][-1] == {"role": "user", "content": "Some text"}
    assert "français" in kwargs["messages"][0]["content"]


def test_empty_content_returns_empty_string():
    assert summarize_fr("x", settings=SETTINGS, client=fake_client(None)) == ""


def test_connection_error_becomes_explicit_exception():
    client = MagicMock()
    client.chat.completions.create.side_effect = APIConnectionError(request=MagicMock())

    with pytest.raises(LLMUnavailableError, match="vLLM injoignable"):
        summarize_fr("x", settings=SETTINGS, client=client)


def test_api_status_error_becomes_explicit_exception():
    response = MagicMock(status_code=404)
    client = MagicMock()
    client.chat.completions.create.side_effect = NotFoundError(
        "The model `test-model` does not exist.", response=response, body=None
    )

    with pytest.raises(LLMUnavailableError, match="erreur pour le modèle test-model"):
        summarize_fr("x", settings=SETTINGS, client=client)


SLUGS = [c.slug for c in CATEGORIES]
VALID = {
    "title_fr": "Présentation du modèle X",
    "summary": ["Première phrase.", "Deuxième phrase.", "Troisième phrase."],
    "category": "modeles",
}


def test_enrich_imposes_the_json_schema_with_three_sentences_and_category_enum():
    client = fake_client(json.dumps(VALID))

    result = enrich_fr("Some text", "Introducing Model X", CATEGORIES, settings=SETTINGS,
                       client=client)

    assert result.title_fr == "Présentation du modèle X"
    assert result.summary == VALID["summary"]
    assert result.category == "modeles"

    kwargs = client.chat.completions.create.call_args.kwargs
    response_format = kwargs["response_format"]
    assert response_format["type"] == "json_schema"
    schema = response_format["json_schema"]["schema"]
    assert schema["required"] == ["title_fr", "summary", "category"]
    assert schema["additionalProperties"] is False
    assert schema["properties"]["summary"]["minItems"] == 3
    assert schema["properties"]["summary"]["maxItems"] == 3
    assert schema["properties"]["category"]["enum"] == SLUGS
    assert kwargs["max_tokens"] == SETTINGS.vllm_max_tokens
    assert kwargs["extra_body"] == {"chat_template_kwargs": {"enable_thinking": False}}


def test_enrich_prompt_lists_categories_with_descriptions_and_the_article():
    client = fake_client(json.dumps(VALID))

    enrich_fr("Body of the article", "Title", CATEGORIES, settings=SETTINGS, client=client)

    system, user = client.chat.completions.create.call_args.kwargs["messages"]
    assert "outils-dev : Outils dev — Outils pour développeurs" in system["content"]
    assert "« autre » est un dernier recours" in system["content"]
    assert "que si aucune autre catégorie" in system["content"]
    assert "3 phrases" in system["content"]
    assert user["content"] == "Titre : Title\n\nTexte :\nBody of the article"


@pytest.mark.parametrize(
    ("content", "error"),
    [
        ("not json", "JSON invalide"),
        ("[]", "objet JSON"),
        (json.dumps({**VALID, "category": "sport"}), "catégorie inconnue"),
        (json.dumps({**VALID, "summary": ["Une.", "Deux."]}), "exactement 3 phrases"),
        (json.dumps({**VALID, "summary": ["Une.", "Deux.", "Trois.", "Quatre."]}),
         "exactement 3 phrases"),
        (json.dumps({**VALID, "summary": ["Une.", " ", "Trois."]}), "exactement 3 phrases"),
        (json.dumps({**VALID, "title_fr": ""}), "title_fr"),
        (json.dumps({**VALID, "title_fr": "T" * 301}), "title_fr trop long"),
        (json.dumps({**VALID, "summary": ["Une.", "D" * 501, "Trois."]}),
         "phrase de résumé trop longue"),
    ],
)
def test_output_outside_the_schema_is_rejected(content, error):
    with pytest.raises(LLMInvalidOutputError, match=error):
        parse_enrichment(content, SLUGS)


def test_truncated_output_is_rejected():
    client = fake_client('{"title_fr": "Tit', finish_reason="length")

    with pytest.raises(LLMInvalidOutputError, match="tronquée"):
        enrich_fr("x", "t", CATEGORIES, settings=SETTINGS, client=client)


def test_bad_request_is_an_article_failure_not_an_outage():
    client = MagicMock()
    client.chat.completions.create.side_effect = BadRequestError(
        "maximum context length exceeded", response=MagicMock(status_code=400), body=None
    )

    with pytest.raises(LLMInvalidOutputError, match="refusée"):
        enrich_fr("x", "t", CATEGORIES, settings=SETTINGS, client=client)


def test_enrich_connection_error_is_an_outage():
    client = MagicMock()
    client.chat.completions.create.side_effect = APIConnectionError(request=MagicMock())

    with pytest.raises(LLMUnavailableError, match="vLLM injoignable"):
        enrich_fr("x", "t", CATEGORIES, settings=SETTINGS, client=client)


def test_outputs_at_the_schema_bounds_are_accepted():
    content = json.dumps({**VALID, "title_fr": "T" * 300, "summary": ["U" * 500] * 3})

    result = parse_enrichment(content, SLUGS)

    assert len(result.title_fr) == 300 and all(len(s) == 500 for s in result.summary)
