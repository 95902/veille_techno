# veille-worker

Worker Python : collecte, extraction, résumé et catégorisation des articles via vLLM.

```sh
uv sync
uv run pytest -m "not slow"   # tests unitaires
uv run pytest                 # + test réel vLLM (VLLM_BASE_URL joignable)
uv run ruff check .
docker compose run --rm worker-py python -m veille_worker.smoke   # résumé de test via vLLM
```
