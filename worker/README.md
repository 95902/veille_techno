# veille-worker

Worker Python : collecte, extraction, résumé et catégorisation des articles via vLLM.

```sh
uv sync
uv run pytest -m "not slow"   # tests unitaires
uv run pytest                 # + test réel vLLM (VLLM_BASE_URL joignable)
uv run ruff check .
docker compose run --rm worker-py python -m veille_worker.smoke   # résumé de test via vLLM
```

`worker-py` est dans le profil Compose `tools` : `docker compose up` ne le démarre pas,
`docker compose run` le lance à la demande (vllm et postgres doivent être healthy).
Il ne reçoit que `VLLM_MODEL`, `VLLM_BASE_URL`, `DB_HOST`, `DB_PORT`, `DB_DATABASE`,
`DB_USERNAME` (`veille_worker`) et `WORKER_DB_PASSWORD`.
