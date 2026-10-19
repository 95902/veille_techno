# Coding Assertions

Gates prévus ; les commandes deviennent exécutables une fois `web/` et `worker/` créés.

## Before commit

| Order | Command                                       | Checks                  |
| ----- | --------------------------------------------- | ----------------------- |
| 1     | `cd web && ./vendor/bin/pint --test`          | style PHP               |
| 2     | `cd web && npm run lint`                      | lint Vue/TS             |
| 3     | `cd worker && ruff check .`                   | lint Python             |
| 4     | `cd web && ./vendor/bin/pest --exclude-group=slow` | tests unitaires Laravel |
| 5     | `cd worker && pytest -m "not slow"`           | tests unitaires worker  |

## Before push

| Order | Command                          | Checks                     |
| ----- | -------------------------------- | -------------------------- |
| 1     | `cd web && ./vendor/bin/pest`    | suite complète Laravel     |
| 2     | `cd worker && pytest`            | suite complète worker      |
| 3     | `cd web && npm run build`        | build du front             |

## Behavior

I fix is needed, spawn 1 agent per assertion to fix (e.g typechecking / tests / rules violated on category UI = 3 agents).
