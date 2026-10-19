# Review: pages de lecture

- Rounds: 2
- Started: 2026-10-19

## Round 1 · r-3e5c

- Date: 2026-10-19
- By: 95902
- Diff: `main...ba70034`
- Axes: code, functional, relevancy
- Verdict: changes-requested
- Score: 10/15 met, 0 unmet, 5 unverified at runtime, 0 out of the diff

### Criteria

- [x] P1.1 `veille_test` existe, possédée par `veille_app` ; `veille` non modifiée par le groupe `pgsql` — `pg_database` relu en revue : `veille_test|veille_app` ; `web/tests/Pgsql/PgsqlTestCase.php:29-45` ; leurres relancés en revue : `DB_TEST_DATABASE=decoy_nonexistent_db` et `Decoy_Upper_test` → 12 failed sur `PgsqlTestCase.php:32` (refus avant tout trait), `decoy_absent_test` → 12 skipped
- Unverified at runtime: P1.2 `migrate --force` sur `veille` peuplée — la migration a été appliquée par le `migrate:fresh` de l'incident sur une base vide, puis `Nothing to migrate` (evidence.md §6) : l'ajout de la colonne générée sur une table remplie n'a jamais tourné ; `down()` jamais joué
- Unverified at runtime: P1.2 le worker écrit toujours (`pytest -m db`) — evidence.md §6, enregistré avant commit, non relancé (interdit contre `veille`)
- [x] P1.3 Sans `q` plus récents d'abord, avec `q` par pertinence — `web/app/Models/Article.php:106-118` ; `web/tests/Pgsql/ArticleSearchTest.php:60,96` (`pest --group=pgsql` 12 passed, 14 assertions, relancé en revue sur ba70034)
- [x] P1.4 `pest --group=pgsql` vert avec la base, ignoré sans échec sinon — relancé en revue : 12 passed ; `decoy_absent_test` → 12 skipped
- Unverified at runtime: P1.4 `pest --exclude-group=slow` passe en SQLite — cette commande exécute aussi la suite `Pgsql` contre Postgres (voir findings) ; non relancée en revue (règle : aucun test hors `--group=pgsql`)
- [x] P1.5 Mémoire : commande et convention du groupe `pgsql` — `aidd_docs/memory/coding-assertions.md`, `testing.md`, `architecture.md` (diff)
- [x] P2.1 Invité redirigé vers la connexion ; après connexion arrivée sur `/` — `web/routes/web.php:6-9`, `web/config/fortify.php:76` ; `web/tests/Feature/ArticlePagesTest.php:35`, `web/tests/Feature/Auth/AuthenticationTest.php`
- [x] P2.1 20 par page, summarized, plus récents d'abord, filtres conservés en page 2 — `web/app/Http/Controllers/ArticleController.php:27-33` ; `ArticlePagesTest.php:48,98`
- [x] P2.1 Catégorie inconnue vide sans erreur ; pending/failed → 404 — `ArticleController.php:44` ; `ArticlePagesTest.php:122,164`
- [x] P2.1 Props sans `content` ni `last_error` — `ArticleController.php:60-70` ; `ArticlePagesTest.php:81,140`
- [x] P2.2 Liste et détail suivent le wireframe ; lien d'origine en nouvel onglet — `web/resources/js/pages/articles/Show.vue:74` ; `screenshots/02-liste.jpg`, `08-detail-titre-origine.jpg` (07 antérieur au code final, voir findings)
- [x] P2.3 Aucun lien Dashboard, Repository, Documentation — grep en revue sur `resources/js`, `app`, `routes` : aucune occurrence ; `npm run types:check` relancé sans erreur
- Unverified at runtime: P2.4 `pest --exclude-group=slow` vert — non relancé en revue ; `pint --test` (PASS 106 files) et `npm run lint` (0 warnings, 0 errors) relancés verts
- Unverified at runtime: P2.5 Captures avec et sans accent, mêmes articles — `screenshots/04-…`, `05-…` (14 articles chacune) ; captures prises avant commit, 07 prouve qu'au moins une précède le code final

### Findings

- `web/tests/Pest.php:18-20` : la suite `Feature` ne protège `veille` que par le forçage d'environnement de `phpunit.xml:29-30,41-43`. Si `bootstrap/cache/config.php` existe (`php artisan optimize`/`config:cache`, réflexe de déploiement en production ; le conteneur `app` tourne en `APP_ENV=production` sur le même volume `./web`), `LoadConfiguration` charge la config en cache et ignore l'environnement : `database.default` = `pgsql`, base `veille`, et `RefreshDatabase` lance `migrate:fresh` sur la production, même scénario que l'incident par un autre chemin. Préexistant, mais c'est la seule voie restante vers `veille` et le critère P1.1 promet que les tests ne la modifient pas → dans `Tests\TestCase::createApplication`, refuser si `$app->configurationIsCached()` ou si la connexion par défaut n'est pas `sqlite` `:memory:` (`PgsqlTestCase` appelle le parent puis bascule, donc compatible) — 🟡 major, security
- `web/phpunit.xml:14-16` : la suite `Pgsql` tourne dans tout `pest` sans `--group=pgsql`. Dans un même processus, les tests `Feature` (SQLite) passent `RefreshDatabaseState::$migrated` à `true` (`RefreshDatabase.php:83-90`) ; les tests `Pgsql` qui suivent ne migrent donc jamais `veille_test` et tournent sur le schéma laissé par le dernier `--group=pgsql` : échec sur un volume neuf (tables absentes), faux vert sur un schéma périmé après une nouvelle migration. Le `132 passed` de `pest` (evidence §8) ne tient que parce que `veille_test` venait d'être migrée. Même cause : le gate historique `pest --exclude-group=slow` (critère P1.4) atteint Postgres → soit exclure le groupe par défaut (`<groups><exclude><group>pgsql</group></exclude></groups>`, vérifier que `--group=pgsql` le réinclut) et retirer « groupe `pgsql` compris » de `coding-assertions.md`, soit dans `PgsqlTestCase::createApplication` remettre `RefreshDatabaseState::$migrated = false` au premier test Pgsql du processus (drapeau statique ; une surcharge de `refreshTestDatabase` serait masquée par le trait) — 🟡 major, code-health
- `web/resources/js/components/AppSidebar.vue:46-48` : le retrait de `<NavFooter>` laisse `web/resources/js/components/NavFooter.vue` sans aucun import → supprimer le composant — 🟢 minor, rot
- `web/resources/js/pages/articles/Show.vue:60-63` : « Titre d'origine » est toujours affiché ; quand `title_fr` est nul, `ArticleController.php:64` y met déjà `title`, d'où le même titre deux fois → `v-if="article.title !== article.title_fr"` — 🟢 minor, frontend
- `web/resources/js/pages/articles/Index.vue:29` : `?categorie=inconnue` lie le `select` à une valeur sans option, le menu s'affiche vide (`screenshots/09-categorie-inconnue.jpg`) → renvoyer `categorie` vide dans `filters` quand le slug n'existe pas (`ArticleController.php:38`), ou initialiser à `''` si absent de `categories` — 🟢 minor, frontend
- `web/app/Models/Article.php:115-117` : le contrat dit « tri par date de publication décroissante (repli sur la date de collecte) », le plan dit `published_at DESC NULLS LAST` puis `created_at` : un article non daté collecté aujourd'hui (le worker en admet 3 par source et par passage) part en fin de liste alors que sa carte affiche sa date de collecte (`ArticleController.php:66`), donc des dates non monotones et des nouveautés enterrées en page 5. 0 article non daté en base aujourd'hui. Critère ambigu entre contrat et plan → trancher ; si « repli » veut dire tri sur la date affichée : `ORDER BY COALESCE(published_at, created_at) DESC, id DESC` — 🟢 minor, fit
- `aidd_docs/tasks/2026_10/2026_10_19_pages-lecture/screenshots/07-detail-depuis-recherche.jpg` : montre le détail sans la ligne « Titre d'origine » que `Show.vue:60-63` affiche désormais toujours : capture antérieure au code commité. Sans effet sur le critère 7 (08 montre le rendu actuel, Pest couvre `title`), mais evidence.md la présente comme preuve du code final → la refaire ou noter qu'elle précède l'ajout de la ligne — 🟢 minor, rot
- `web/tests/Feature/ArticlePagesTest.php:133` : aucun test ne passe `?q=` par le contrôleur sur Postgres (validation, `withQueryString` qui garde `q` dans `next_page_url`, `filters.q` rogné) ; `ArticleSearchTest` n'appelle que les scopes → un test HTTP dans `tests/Pgsql` (`get('/?q=sécurité&categorie=securite')`, pagination comprise) — 🟢 minor, code-health

## Round 2 · r-7ec1

- Date: 2026-10-19
- By: 95902
- Diff: `main...d15c2cc` (fixes `d15c2cc~3..d15c2cc`)
- Axes: code, functional, relevancy
- Verdict: approve
- Score: 11/15 met, 0 unmet, 4 unverified at runtime, 0 out of the diff

Suivi du round 1 (relancé en revue, jamais contre `veille`) :

1. Config en cache → corrigé, `web/tests/TestCase.php:14-38`. Leurre : `config:cache` écrit dans `APP_CONFIG_CACHE=/tmp/decoy_config.php` avec `DB_DATABASE=decoy_nonexistent_db` (rien dans `bootstrap/cache/`), puis `pest tests/Feature/ArticleOrderTest.php` → `Refusing to run the tests with a cached configuration (/tmp/decoy_config.php)` ; fichier supprimé.
2. Groupe `pgsql` dans tout `pest` / `$migrated` → corrigé, `web/phpunit.xml:15-20` + `web/tests/Pgsql/PgsqlTestCase.php:50-55`. OID de `articles` dans `veille_test` : 18769 avant, 18769 après `pest` (123 passed, `veille_test` intouchée), 18929 après `pest --exclude-group=slow` (140 passed : `migrate:fresh` a bien tourné). Reste un sens non couvert (finding ci-dessous).
3. `NavFooter.vue` orphelin → supprimé.
4. Titre d'origine en double → corrigé, `web/resources/js/pages/articles/Show.vue:60-63`.
5. `select` vide sur slug inconnu → corrigé, `web/app/Http/Controllers/ArticleController.php:43`, `web/tests/Feature/ArticlePagesTest.php:131`.
6. Tri des non datés → `COALESCE(published_at, created_at) DESC, id DESC`, `web/app/Models/Article.php:115-116` ; `web/tests/Feature/ArticleOrderTest.php`, `web/tests/Pgsql/ArticleSearchTest.php:96-113`.
7. Capture 07 antérieure → justifié, `evidence.md:41`.
8. Pas de `?q=` HTTP sur Postgres → `web/tests/Pgsql/ArticleSearchHttpTest.php` (trim, validation, `next_page_url` avec `q` et `categorie`).

### Criteria

- [x] P1.1 `veille_test` possédée par `veille_app` ; `veille` non modifiée par les tests — `PgsqlTestCase.php:33-49`, `TestCase.php:14-38` ; leurres relancés : `DB_TEST_DATABASE=decoy_nonexistent_db` → 17 failed (refus), `decoy_absent_test` → 17 skipped
- Unverified at runtime: P1.2 `migrate --force` sur `veille` peuplée — non relançable (règle). Rejoué en revue sur `veille_test`, en `veille_app`, dans une transaction annulée : SQL de `down()` puis de `up()` sur 200 articles insérés → `200|200|200` (lignes, `search_vector` remplis, trouvés par `securite`) ; reste à voir sur `veille` via `artisan migrate`
- Unverified at runtime: P1.2 le worker écrit toujours (`pytest -m db`) — evidence §6, autre tête ; migration et worker inchangés depuis ; non relancé (écrit dans `veille`)
- [x] P1.3 Sans `q` plus récents d'abord (repli date de collecte), avec `q` par pertinence — `Article.php:110-116` ; `pest --group=pgsql` → 17 passed (72 assertions)
- [x] P1.4 `pest --group=pgsql` vert avec la base, ignoré sinon — 17 passed ; `decoy_absent_test` → 17 skipped
- [x] P1.4 `pest --exclude-group=slow` passe — 140 passed, `veille_test` re-migrée (OID changé)
- [x] P1.5 Mémoire : commande et convention du groupe `pgsql` — `coding-assertions.md:12-25`, `testing.md:23-24` (une affirmation fausse, voir findings)
- [x] P2.1 Invité redirigé ; après connexion `/` — `web/routes/web.php:6-9`, `web/config/fortify.php:76`, `ArticlePagesTest.php:35`
- [x] P2.1 20 par page, summarized, plus récents d'abord, filtres en page 2 — `ArticleController.php:27-33`, `ArticlePagesTest.php:48,98`, `ArticleSearchHttpTest.php:62`
- [x] P2.1 Catégorie inconnue vide sans erreur ; pending/failed → 404 — `ArticleController.php:43,50`, `ArticlePagesTest.php:122,165`
- [x] P2.1 Props sans `content` ni `last_error` — `ArticleController.php:66-76`, `ArticlePagesTest.php:81`
- Unverified at runtime: P2.2 Liste et détail suivent le wireframe — lien nouvel onglet vérifié au code (`Show.vue`) ; captures prises avant `Show.vue:60-63` (07 explicitement)
- [x] P2.3 Aucun lien Dashboard, Repository, Documentation ; build ok — grep `resources/js app routes` : seules les actions Wayfinder générées de Filament ; `npm run build` → `built in 1.10s`, `types:check` rc 0
- [x] P2.4 `pest --exclude-group=slow`, `npm run lint`, `pint --test` verts — 140 passed ; `0 warnings and 0 errors` ; `PASS 108 files`
- Unverified at runtime: P2.5 Captures avec et sans accent, mêmes articles — `screenshots/04-…`, `05-…`, autre tête

### Findings

- `web/tests/Pgsql/PgsqlTestCase.php:50-55` : la remise à zéro ne couvre qu'un sens. Si un test `Pgsql` passe avant un test SQLite dans le même processus, `$migrated` reste `true` et SQLite n'est jamais migrée : `pest --exclude-group=none tests/Pgsql/ArticleSearchTest.php tests/Feature/ArticleOrderTest.php` → 3 FAIL `no such table: sources` ; `pest --exclude-group=slow --order-by=random --random-order-seed=1` → 113 failed. Échec bruyant, pas d'ordre par défaut, aucun risque pour `veille` → déplacer le mécanisme dans `Tests\TestCase::createApplication` : retenir en statique la connexion migrée et remettre `RefreshDatabaseState::$migrated = false` quand la connexion par défaut change (supprime le drapeau propre à `PgsqlTestCase`) — 🟢 minor, code-health
- `aidd_docs/memory/coding-assertions.md:25` : « Pest ne garde que la dernière (`--exclude-group=slow --exclude-group=pgsql` lance quand même `pgsql`) » est faux sur Pest 5.3.3 : cette commande et l'ordre inverse donnent 123 passed (groupe `pgsql` exclu). Seul vrai : une option `--exclude-group` remplace l'exclusion de `phpunit.xml` (`--exclude-group=slow` → 140) → réécrire en « toute option `--exclude-group` remplace cette exclusion (`--exclude-group=slow` lance `pgsql`) » — 🟢 minor, rot
- `aidd_docs/tasks/2026_10/2026_10_19_pages-lecture/evidence.md:56-71` : le tableau des gates reste celui de `ba70034` (`pest` 132, `--group=pgsql` 12, gate avant commit à deux `--exclude-group`) ; les résultats de `d15c2cc` n'y sont pas → y reporter ceux de la tête : `pest` 123, `--group=pgsql` 17, `--exclude-group=slow` 140, pint 108 files — 🟢 minor, rot
- `web/tests/Pgsql/ArticleSearchHttpTest.php:14-23` : `searchableArticle` est la copie exacte de `summarizedArticle` (`ArticleSearchTest.php:11-20`), renommée pour éviter la redéclaration ; `orderedArticle` (`ArticleOrderTest.php:14-22`) refait `readableArticle` → un état `summarized()` sur `ArticleFactory`, ou un helper unique dans `tests/Pest.php` — 🟢 minor, rot
- `web/tests/Feature/ArticlePagesTest.php:69-79` : cas couvert par `ArticleOrderTest.php:24-37` (« Sans date ancien » après « Ancien ») ; idem `ArticleSearchHttpTest.php:51-55` refait `ArticlePagesTest.php:134-139` (201 caractères) → supprimer les doublons, garder les tests d'ordre dans un seul fichier — 🟢 minor, rot
- `web/app/Http/Controllers/ArticleController.php:43` : sur `?categorie=inconnue`, l'écran montre « Toutes les catégories », « 0 article » et « Aucun article ne correspond » : il laisse croire que le site est vide alors que le filtre est actif. Critère 3 tenu (liste vide sans erreur) → soit rediriger un slug inconnu vers la liste sans filtre, soit afficher « Catégorie inconnue » au-dessus de la liste vide — 🟢 minor, fit

## Challenge · round 2 (contre `contract.md`)

My confidence level of correctness now: 85%

# Correctness (100%)
- Objectif tenu de bout en bout : liste `summarized` paginée par 20, filtre `categorie` et recherche `q` combinables et conservés en page 2 (`ArticleSearchHttpTest.php:62`), détail sans `content`, 404 hors `summarized`, accès `auth`+`verified`, `/` comme accueil.
- Recherche conforme aux décisions : `unaccent` + `fr_unaccent`, colonne générée pondérée A/B/C + GIN, `websearch_to_tsquery` + `ts_rank`, puis date et `id` pour un ordre stable ; `securite` et `sécurité` donnent les mêmes résultats (`pgsql` 17 passed).
- Tri « repli sur la date de collecte » désormais aligné sur la date affichée par la carte (`COALESCE`), l'ambiguïté contrat/plan du round 1 est tranchée en faveur du contrat.
- Sécurité de la base `veille` : trois barrières indépendantes (forçage `phpunit.xml`, refus d'une config en cache ou d'une connexion autre que SQLite mémoire, nom `_test` + `current_database()` pour `pgsql`), chacune prouvée par leurre ; le gate `pest` ne touche plus `veille_test`.
- Écart assumé : « Titre d'origine » masqué quand il égale le titre affiché ; le contrat le liste au détail, mais l'afficher deux fois n'apporte rien.

# Deal breakers
-

# Suggestions (enhancements only)
- Critère 6 : la migration n'a jamais tourné via `artisan migrate` sur une table `articles` peuplée (appliquée par le `migrate:fresh` de l'incident) ; le SQL rejoué ici sur `veille_test` peuplée passe, mais un `migrate:rollback --step=1 && migrate` sur une copie de `veille` (`pg_dump` → base `*_test`) fermerait le doute avant la mise en prod.
- Critère 7 vérifié sur 97 articles, non 160 (base reconstruite après l'incident) et captures antérieures à la tête : refaire 02, 05 et 08 sur `d15c2cc` suffirait.
- Simplifier la remise à zéro de `RefreshDatabaseState::$migrated` en un mécanisme symétrique dans `Tests\TestCase` (finding 1 du round 2) et corriger l'affirmation fausse de `coding-assertions.md:25`.
- Factoriser les helpers d'articles de test en un état de factory ; retirer les tests en double.
