# Testing

Tests de fonctionnalité Pest dans `web/tests/` (auth, réglages, back-office Filament) et tests pytest dans `worker/tests/`. Commandes : `coding-assertions.md`.

## Strategy

- Unitaires : logique métier Laravel (filtres, recherche, sélection du digest) et étapes du worker (parsing, extraction, construction des prompts).
- Intégration : jobs et notifications Laravel contre PostgreSQL ; écriture du worker en base avec le rôle sans DDL.
- Les appels vLLM sont simulés dans les tests ; un test marqué `slow` peut viser le vLLM local.

## Tools

- Pest côté Laravel.
- pytest côté worker.

## Conventions

- Tests Laravel dans `web/tests/`, tests worker dans `worker/tests/`.
- Les tests lents ou dépendant de vLLM sont regroupés (`slow`) et exclus du gate avant commit.
- Les fixtures RSS et HTML sont des fichiers figés, jamais des appels réseau réels.
- Pest tourne dans le conteneur `app`, où compose injecte la vraie base : `web/phpunit.xml` force (`force="true"`) `APP_ENV=testing` et SQLite en mémoire. Sans ça, `RefreshDatabase` vide la base `veille`.
