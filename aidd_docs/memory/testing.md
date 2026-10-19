# Testing

Stratégie prévue ; aucun test n'existe encore. Commandes : `coding-assertions.md`.

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
