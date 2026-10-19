# Review: pages de lecture

- Rounds: 1
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
