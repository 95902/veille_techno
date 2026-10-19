# Coding Assertions

PHP et front tournent dans le conteneur `app` (PHP 8.4 + Node ; le PHP de l'hôte est trop ancien pour les dépendances verrouillées). Préfixe `W` = `docker compose exec -e HOME=/tmp -w /var/www/web app`. Le worker tourne sur l'hôte avec `uv`.

## Before commit

| Order | Command                                            | Checks                  |
| ----- | -------------------------------------------------- | ----------------------- |
| 1     | `W ./vendor/bin/pint --test`                       | style PHP               |
| 2     | `W npm run lint`                                   | lint Vue/TS             |
| 3     | `cd worker && uv run ruff check .`                 | lint Python             |
| 4     | `W ./vendor/bin/pest`                              | tests Laravel (SQLite, groupe `pgsql` exclu) |
| 5     | `cd worker && uv run pytest -m "not slow"`         | tests unitaires worker  |

## Before push

| Order | Command                          | Checks                                  |
| ----- | -------------------------------- | --------------------------------------- |
| 1     | `W ./vendor/bin/pest`            | suite Laravel en SQLite (groupe `pgsql` exclu) |
| 1b    | `W ./vendor/bin/pest --group=pgsql` | recherche plein texte contre `veille_test` (doit afficher `passed`, pas `skipped`) |
| 2     | `cd worker && uv run pytest`     | suite complète worker (vLLM démarré)    |
| 3     | `W npm run build`                | build du front                          |
| 4     | `cd worker && DB_HOST=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' veille_techno-postgres-1) WORKER_DB_PASSWORD=$(grep ^WORKER_DB_PASSWORD= ../.env \| cut -d= -f2) uv run pytest -m db` | SQL de `Repository` contre le Postgres de Compose (`docker compose up -d postgres`), en `veille_worker` |

Groupe `pgsql` : base `veille_test` du Postgres de Compose (connexion `pgsql_testing`, `DB_TEST_DATABASE`). Créée par `infra/postgres/init` sur un volume neuf ; sur un volume existant, une fois : `docker compose exec postgres psql -U postgres -c "CREATE DATABASE veille_test OWNER veille_app"`. Exclu par défaut (`phpunit.xml`) ; toute option `--exclude-group` remplace cette exclusion et Pest ne garde que la dernière (`--exclude-group=slow --exclude-group=pgsql` lance quand même `pgsql`) : pas de `--exclude-group` sur `pest`. Ne jamais pointer `DB_TEST_DATABASE` vers `veille` : `RefreshDatabase` la vide (`PgsqlTestCase` refuse tout nom sans suffixe `_test`).

Les tests `db` sont ignorés sans `WORKER_DB_PASSWORD` dans l'environnement : `pytest -m "not slow"` reste vert sans Compose. Postgres n'est pas publié sur l'hôte, d'où l'IP du conteneur.

## Behavior

I fix is needed, spawn 1 agent per assertion to fix (e.g typechecking / tests / rules violated on category UI = 3 agents).
