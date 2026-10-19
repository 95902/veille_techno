import pytest

from veille_worker.llm import summarize_fr
from veille_worker.smoke import SAMPLE_TEXT


@pytest.mark.slow
def test_real_vllm_returns_non_empty_summary_without_reasoning():
    summary = summarize_fr(SAMPLE_TEXT)

    assert summary
    assert "<think>" not in summary
