from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from openai import APIConnectionError

from veille_worker.config import Settings
from veille_worker.llm import LLMUnavailableError, summarize_fr

SETTINGS = Settings(vllm_base_url="http://vllm:8000/v1", vllm_model="test-model", vllm_timeout=5)


def fake_client(content: str | None) -> MagicMock:
    client = MagicMock()
    message = SimpleNamespace(content=content)
    client.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=message)]
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
