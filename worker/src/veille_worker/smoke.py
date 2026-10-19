"""Commande de test : résume un texte figé en français via vLLM.

Usage : python -m veille_worker.smoke
"""

import sys

from veille_worker.llm import LLMUnavailableError, summarize_fr

SAMPLE_TEXT = (
    "Researchers have released a new open-weight language model that runs on a single "
    "consumer GPU. Thanks to 4-bit quantization, the 14-billion-parameter model fits in "
    "12 GB of video memory while keeping most of its accuracy on reasoning benchmarks. "
    "The team says the model is aimed at companies that want to keep their data in-house "
    "and avoid paying for cloud APIs. Early adopters report that summarization and "
    "classification tasks work well, although long documents still require chunking."
)


def main() -> int:
    try:
        summary = summarize_fr(SAMPLE_TEXT)
    except LLMUnavailableError as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 1
    if not summary:
        print("Erreur : vLLM a renvoyé un résumé vide.", file=sys.stderr)
        return 1
    print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
