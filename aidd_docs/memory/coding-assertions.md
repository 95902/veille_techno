# Coding Assertions

PHP et front tournent dans le conteneur `app` (PHP 8.4 + Node ; le PHP de l'hôte est trop ancien pour les dépendances verrouillées). Préfixe `W` = `docker compose exec -e HOME=/tmp -w /var/www/web app`. Le worker tourne sur l'hôte avec `uv`.

## Before commit

| Order | Command                                            | Checks                  |
| ----- | -------------------------------------------------- | ----------------------- |
| 1     | `W ./vendor/bin/pint --test`                       | style PHP               |
| 2     | `W npm run lint`                                   | lint Vue/TS             |
| 3     | `cd worker && uv run ruff check .`                 | lint Python             |
| 4     | `W ./vendor/bin/pest --exclude-group=slow`         | tests unitaires Laravel |
| 5     | `cd worker && uv run pytest -m "not slow"`         | tests unitaires worker  |

## Before push

| Order | Command                          | Checks                                  |
| ----- | -------------------------------- | --------------------------------------- |
| 1     | `W ./vendor/bin/pest`            | suite complète Laravel                  |
| 2     | `cd worker && uv run pytest`     | suite complète worker (vLLM démarré)    |
| 3     | `W npm run build`                | build du front                          |

## Behavior

I fix is needed, spawn 1 agent per assertion to fix (e.g typechecking / tests / rules violated on category UI = 3 agents).
