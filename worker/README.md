# veille-worker

Worker Python : collecte, extraction, résumé et catégorisation des articles via vLLM.

```sh
uv sync
uv run pytest -m "not slow"   # tests unitaires
uv run pytest                 # + test réel vLLM (VLLM_BASE_URL joignable)
uv run ruff check .
docker compose run --rm worker-py python -m veille_worker.smoke     # résumé de test via vLLM
docker compose run --rm worker-py python -m veille_worker.collect   # collecte manuelle
```

## Collecte

`python -m veille_worker.collect` lit les sources actives, insère les nouveaux articles
(`pending`), extrait leur texte puis demande à vLLM un titre français, un résumé de 3 phrases
et une catégorie (sortie JSON imposée). Bilan affiché en fin de passe ; code de sortie 1 si la
base ou vLLM sont indisponibles. Prérequis : base migrée et seedée côté Laravel
(`php artisan migrate --force`, `php artisan db:seed --force`).

## Planification

Le service `worker-cron` (lancé par `docker compose up -d`) exécute la collecte avec
supercronic selon `COLLECT_SCHEDULE` (défaut `0 6 * * *`) dans le fuseau `COLLECT_TZ`
(défaut `Europe/Paris`). Il ne lance rien au démarrage ; ses logs : `docker compose logs worker-cron`.

`worker-py` est dans le profil Compose `tools` : `docker compose up` ne le démarre pas,
`docker compose run` le lance à la demande (vllm et postgres doivent être healthy).
Il ne reçoit que `VLLM_MODEL`, `VLLM_BASE_URL`, `DB_HOST`, `DB_PORT`, `DB_DATABASE`,
`DB_USERNAME` (`veille_worker`) et `WORKER_DB_PASSWORD`.
