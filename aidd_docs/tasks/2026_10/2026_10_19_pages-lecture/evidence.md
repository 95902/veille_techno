# Preuves — pages de lecture

Date : 2026-10-19. Branche `feat/pages-lecture`, rien commité. `W` = `docker compose exec -T -e HOME=/tmp -w /var/www/web app`.

## Incident : base `veille` vidée pendant l'implémentation

- **Quoi** : `W -e DB_TEST_DATABASE=veille app ./vendor/bin/pest --group=pgsql` → `Tests: 12 passed`. `RefreshDatabase` a lancé `migrate:fresh` sur `veille`.
- **Pourquoi** : la première garde de `PgsqlTestCase` comparait la base cible à `config('database.connections.pgsql.database')`, que `phpunit.xml` force à `:memory:`. `veille` ≠ `:memory:` → la garde a laissé passer.
- **Avant / après** : `articles` 171 (160 summarized, 11 failed), `users` 1 → `articles` 0, `users` 0, `sources` 0, `categories` 0. Toutes les migrations (dont `add_articles_search`) réappliquées par `migrate:fresh`, droits du worker compris.
- **Garde corrigée** : nom de base exigé `^[a-z0-9_]+_test$`, contrôlé avant tout trait puis via `current_database()` après connexion. Vérifiée sur un leurre inexistant, jamais sur `veille` :
  `W -e DB_TEST_DATABASE=nonexistent_db app ./vendor/bin/pest --group=pgsql` → `Refusing to run the pgsql tests on database "nonexistent_db": its name must end with "_test".`
- **Reconstruction (décision de l'utilisateur, hors agent)** : `db:seed --force`, 1 compte admin, nouvelle collecte → 97 articles `summarized`, tous avec `search_vector`. Le cas `DB_TEST_DATABASE=veille` n'a plus été relancé.
- **Conséquence** : le critère 7 (« 160 articles ») est vérifié sur les 97 articles de la base reconstruite.

## Critères d'acceptation

### 1. Accès

- Pest (SQLite) `ArticlePagesTest` : « a guest is sent to the login page » (`/` et `/articles/{id}`), « an unverified user is sent to the verification notice ». `AuthenticationTest` : après connexion, redirection vers `route('articles.index')`.
- Navigateur : invité sur `http://localhost/` → `/login` (`screenshots/01-invite-redirige-connexion.jpg`) ; après connexion → `http://localhost/`, liste (`02-liste.jpg`).

### 2. Liste : summarized, plus récents d'abord, 20 par page

- Pest : « the list shows 20 summarized articles per page, most recent first » (25 summarized + 1 pending + 1 failed → total 25, 20 cartes, `Article 1` puis `Article 20`, `last_page` 2) ; « an undated article falls back after the dated ones ».
- Base réelle : 20 cartes, `datetime` décroissants (`2026-10-19T14:30:00+00:00`, `14:06:58`, `13:58:41`…), pagination `Page 1 / 5` ; `/?page=2` → 20 cartes, `Précédent | Page 2 / 5 | Suivant` (`10-pagination-page-2.jpg`). 97 summarized = 5 pages.

### 3. Filtre catégorie

- Pest : « the category filter keeps that category and survives pagination » (22 securite → `next_page_url` contient `categorie=securite` et `page=2`, page 2 = 2 cartes securite) ; « an unknown category gives an empty list without error ».
- Base réelle : `/?categorie=securite` → `14 articles` (SQL : `securite|14`) (`03-filtre-securite.jpg`) ; `/?categorie=inconnue` → `0 article`, « Aucun article ne correspond à ces critères. », HTTP 200 (`09-categorie-inconnue.jpg`).

### 4. Recherche sans accents, pertinence, combinable

- `W ./vendor/bin/pest --group=pgsql` (base `veille_test`) → `Tests: 12 passed (14 assertions)` : sans accent → accentué, accentué → sans accent, titre d'origine, titre FR classé avant résumé, combinaison catégorie, saisies libres sans erreur SQL (5 cas), ordre par date sans `q`.
- Base réelle, navigateur : `?q=securite` → 14 articles (`04-…`) ; `?q=sécurité` → 14 articles, **mêmes titres dans le même ordre** (`sameOrderedAsNoAccent: true`) (`05-…`) ; `?q=sécurité&categorie=securite` → 8 articles, badges uniquement « Sécurité » (`06-…`).
- SQL de contrôle (lecture seule) : `websearch_to_tsquery('fr_unaccent','securite')` → 14, `'sécurité'` → 14, avec `slug='securite'` → 8.

### 5. Détail

- Pest : « the detail page shows a summarized article » (titre FR, titre d'origine, résumé, source, catégorie, url, date ; ni `content` ni `last_error`) ; « the detail of an article not summarized is not found » (pending, failed → 404).
- Base réelle : `/articles/114?categorie=securite&q=sécurité` depuis une carte (`07-…`) : lien d'origine `target="_blank"`, `rel="noopener noreferrer"` ; « Retour à la liste » garde `categorie` et `q`. `/articles/73` (`08-…`) : titre FR + « Titre d'origine : JB Pritzker thinks AI could help us live to 100 — or threaten us like nukes ».
- Pas d'article pending/failed dans la base reconstruite : le 404 n'est prouvé qu'en Pest.

### 6. Migration sur la base réelle sans casser le worker

- `W app php artisan migrate --force` → `INFO  Nothing to migrate.` (déjà appliquée, voir incident).
- `select status, count(*), count(search_vector) from articles group by 1` → `summarized|97|97`.
- `cd worker && DB_HOST=… WORKER_DB_PASSWORD=… uv run pytest -m db` → `13 passed, 113 deselected`.
- `migrate` en SQLite : passe à chaque test Pest (`RefreshDatabase`), la migration ne fait rien hors pgsql.

### 7. Contrôle visuel sur la base réelle (97 articles)

Captures dans `screenshots/` : 01 invité redirigé, 02 liste, 03 filtre Sécurité, 04 recherche « securite », 05 recherche « sécurité », 06 recherche + filtre, 07 détail depuis la recherche, 08 détail avec titre d'origine, 09 catégorie inconnue, 10 page 2.
Compte temporaire `capture-temp@veille.test` (vérifié) créé par tinker pour la connexion, supprimé ensuite avec ses sessions (`0 remaining; users=1`).

### 8. Gates

| Gate | Résultat |
| --- | --- |
| `W ./vendor/bin/pint --test` | `PASS … 106 files` |
| `W npm run lint` | `Found 0 warnings and 0 errors.` |
| `cd worker && uv run ruff check .` | `All checks passed!` |
| `W ./vendor/bin/pest --exclude-group=slow --exclude-group=pgsql` | `Tests: 120 passed (635 assertions)` |
| `cd worker && uv run pytest -m "not slow"` | `111 passed, 13 skipped, 2 deselected` |
| `W ./vendor/bin/pest` | `Tests: 132 passed (649 assertions)` |
| `W ./vendor/bin/pest --group=pgsql` | `Tests: 12 passed (14 assertions)` |
| `cd worker && uv run pytest` | `113 passed, 13 skipped` |
| `W npm run build` | `✓ built in 1.12s` |
| `uv run pytest -m db` | `13 passed, 113 deselected` |
| `W npm run check` (format + lint) | `All 70 files are correctly formatted` / `Found no warnings or lint errors` |
| `W npm run types:check` | sans erreur |

Groupe `pgsql` sans base (`DB_TEST_DATABASE=absent_test`, base inexistante) → `Tests: 12 skipped (0 assertions)`.
