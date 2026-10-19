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
- Marqueur `db` (`worker/tests/test_repository_db.py`) : SQL réel de `Repository` en `veille_worker` contre le Postgres de Compose ; ignoré sans `WORKER_DB_PASSWORD` ou base injoignable. Chaque test tourne dans une transaction annulée (le rôle n'a pas DELETE) : aucune ligne ne reste, seule la séquence `articles_id_seq` avance. Commande : `coding-assertions.md`.
- Côté worker, la résolution DNS est simulée (fixture `dns` autouse de `worker/tests/conftest.py`) : tout hôte résout vers une IP publique sauf surcharge ; le transport simulé route par l'en-tête Host, les pages partant vers l'IP validée.
- Les fixtures RSS et HTML sont des fichiers figés, jamais des appels réseau réels.
- Groupe Pest `pgsql` (`web/tests/Pgsql/`, `PgsqlTestCase`) : SQL propre à Postgres (recherche plein texte) contre la base dédiée `veille_test`, migrée par `RefreshDatabase` (`migrate:fresh` puis une transaction annulée par test). Refus si le nom de la base ne finit pas par `_test` ; ignoré (`skipped`) si la base est injoignable. Exclu du gate avant commit, lancé avant push. Les autres tests restent en SQLite et n'envoient jamais de recherche `q`.
- Pest tourne dans le conteneur `app`, où compose injecte la vraie base : `web/phpunit.xml` force (`force="true"`) `APP_ENV=testing` et SQLite en mémoire. Sans ça, `RefreshDatabase` vide la base `veille`.
