# Preuves d'exécution : socle technique

- Date : 2026-10-19
- Contexte : corrections de la revue r-2976, volume `veille_techno_postgres_data` supprimé avant le démarrage (init Postgres rejouée) ; `hf_cache` et `vllm_compile_cache` conservés.

## Écart constaté : vLLM à 0.85

Avec `VLLM_GPU_MEMORY_UTILIZATION=0.85` (défaut de `.env.example`), vLLM boucle en redémarrage (7 redémarrages observés) :
`torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 150.00 MiB` pendant le warm-up du sampler, après
« Available KV cache memory: 3.59 GiB » (et non ~1,4 Gio comme mesuré auparavant). `docker compose up -d --wait`
s'arrête sur `container veille_techno-vllm-1 is unhealthy`.

Les preuves c, d, g, h (pytest complet) ont été obtenues avec `VLLM_GPU_MEMORY_UTILIZATION=0.80` passé dans
l'environnement du shell, sans modifier `.env` ni `.env.example` : KV cache 3,01 Gio, 21 936 tokens, `healthy`, 0 redémarrage.
Le choix de la valeur par défaut reste à trancher.

## Résultats

| # | Commande | Sortie décisive |
| - | -------- | --------------- |
| a | `docker compose config -q` | code 0, aucune sortie |
| b | `docker compose up -d --wait` (0.80) | `postgres Healthy`, `app Healthy`, `nginx Healthy`, `vllm Healthy`, code 0 ; `docker compose ps -a` : app, nginx, postgres, vllm, pas de `worker-py` |
| b' | init Postgres | `running /docker-entrypoint-initdb.d/01-roles.sh` → `CREATE ROLE` ×2, `REVOKE` ×3, `CREATE EXTENSION`, `init process complete` |
| c | `curl -s 127.0.0.1:8000/v1/models` | `['Qwen/Qwen3-8B-AWQ']` |
| c | `ss -ltn \| grep 8000` | `LISTEN 0 4096 127.0.0.1:8000 0.0.0.0:*` |
| d | `docker compose run --rm worker-py python -m veille_worker.smoke` | code 0 ; « Un nouveau modèle de langage open-weight à 14 milliards de paramètres a été publié et peut s'exécuter sur une seule carte graphique consumer grâce à la quantisation 4-bit. […] » |
| e | `curl -w '%{http_code}' http://localhost/` | `200`, `<title>Veille techno</title>` |
| e | `curl -w '%{http_code}' http://localhost/admin/login` | `200`, `<title> Login - Veille techno </title>` |
| e | erreur forcée (avant migration, table `sessions` absente) | `500`, `<title>Server Error</title>`, 581 octets, 0 occurrence de `stack\|trace\|vendor/\|SQLSTATE\|exception` ; log : `production.ERROR: SQLSTATE[42P01] … relation "sessions" does not exist` |
| e | `php artisan about --only=environment` | `Environment … production`, `Debug Mode … OFF` (alors que `web/.env` local contient `APP_ENV=local`, `APP_DEBUG=true` : l'environnement Compose prime) |
| f | `php artisan migrate --force` | `Creating migration table … DONE`, 5 migrations `DONE` ; 10 tables, propriétaire `veille_app` |
| f | psql `veille_worker` : `CREATE TABLE t(id int)` | `ERROR: permission denied for schema public` |
| f | psql `veille_worker` : `CREATE TEMP TABLE t(id int)` | `ERROR: permission denied to create temporary tables in database "veille"` |
| f | psql `veille_worker` : `SELECT count(*) FROM users` | `0` (1 ligne), autorisé |
| g | `docker compose run --rm worker-py env \| grep -E 'PASSWORD\|APP_KEY'` | `WORKER_DB_PASSWORD` seul ; variables du worker : `DB_DATABASE DB_HOST DB_PORT DB_USERNAME VLLM_BASE_URL VLLM_MODEL WORKER_DB_PASSWORD` |
| h | `W ./vendor/bin/pint --test` | `PASS … 57 files` |
| h | `W npm run lint` | code 0 |
| h | `W ./vendor/bin/pest` | `Tests: 43 passed (141 assertions)` |
| h | `W npm run build` | `✓ built in 1.31s` |
| h | `cd worker && uv run ruff check .` | `All checks passed!` |
| h | `VLLM_BASE_URL=http://127.0.0.1:8000/v1 uv run pytest` | `5 passed` |
| — | `docker compose down` | conteneurs et réseau supprimés ; volumes `hf_cache`, `postgres_data`, `vllm_compile_cache` conservés |

`W` = `docker compose exec -T -e HOME=/tmp -w /var/www/web app`.
