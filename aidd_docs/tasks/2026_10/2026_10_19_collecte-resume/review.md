# Review: collecte et résumé

- Rounds: 3
- Started: 2026-10-19

## Round 1 · r-69a1

- Date: 2026-10-19
- By: 95902
- Diff: `main...feat/collecte-resume`
- Axes: code, functional, relevancy
- Verdict: changes-requested
- Score: 12/12 met, 0 unmet, 0 unverified at runtime, 0 out of the diff

### Criteria

- [x] P1.1 Migrations Postgres et SQLite ; URL normalisée en double rejetée par la base — `web/tests/Feature/Schema/CollectSchemaTest.php:13,29` (Pest 112 passed, SQLite) ; base réelle migrée (evidence.md §1)
- [x] P1.2 Après seed : 7 catégories, ~10 sources actives ; re-seed sans doublon — `web/tests/Feature/Schema/CollectSchemaTest.php:36,48`
- [x] P1.3 Admin gère sources et catégories ; non-admin 403 ; catégorie utilisée non supprimable — `web/tests/Feature/Admin/SourceResourceTest.php:19`, `web/tests/Feature/Admin/CategoryResourceTest.php:19,82,93,104`
- [x] P1.4 `veille_worker` lit/écrit comme prévu, DELETE et CREATE refusés — `web/database/migrations/2026_10_19_150003_grant_worker_privileges.php:30-32` ; evidence.md §1 ; `information_schema.role_table_grants` relu en revue : articles INSERT,SELECT,UPDATE / sources SELECT / categories SELECT, `pg_default_acl` vide
- [x] P2.1 Aucun DDL ni DELETE ; doublon d'URL sans erreur — `worker/src/veille_worker/db.py:118`, `worker/tests/test_db.py`
- [x] P2.2 Dédoublonnage utm_*/fragment ; fenêtre 7 jours ; plafond — `worker/tests/test_urls.py`, `worker/tests/test_feeds.py:25,35`, `worker/tests/test_collect.py:208`
- [x] P2.3 Page vide → contenu du flux ; budget respecté — `worker/tests/test_extract.py:24,62,75`
- [x] P2.4 Schéma imposé ; sortie hors schéma → `failed` — `worker/src/veille_worker/llm.py:136-143`, `worker/tests/test_collect.py:131`
- [x] P2.5 Source injoignable au bilan sans bloquer les autres ; 3 échecs → plus retenté — `worker/tests/test_collect.py:131,181` (pytest 61 passed hors slow, relancé en revue)
- [x] P3.1 `worker-cron` démarré, planification annoncée, rien au démarrage — evidence.md §4
- [x] P3.2 Collecte réelle : articles `summarized`, en français, catégorisés, bilan et extrait SQL — evidence.md §2 ; base relue : 99 summarized, 11 failed (attempts=3), 20 pending
- [x] P3.3 Mémoire décrit pipeline et service planifié — `aidd_docs/memory/architecture.md`, `aidd_docs/memory/codebase-map.md`

### Findings

- `worker/src/veille_worker/extract.py:62` : les URL d'articles viennent de flux tiers (Hacker News pointe vers n'importe quel site) et sont téléchargées sans plafond de taille (corps entier en mémoire avant le contrôle du content-type), redirections suivies sans limite d'hôte, aucun filtre d'adresse privée/loopback/link-local ni des services Compose (`vllm:8000`, `postgres`, `app`) ; le timeout httpx de 20 s est par opération, pas une durée totale → lecture en streaming avec plafond (2 à 5 Mo) et content-type vérifié avant le corps, durée totale bornée, résolution de l'hôte et refus des IP non publiques à chaque saut de redirection (redirections gérées à la main, 5 au plus), http/https seulement ; tests associés — 🟡 major, security
- `worker/src/veille_worker/collect.py:103` : `normalize_url` lève `ValueError` sur un lien d'entrée au port invalide (`http://host:abc/`, reproduit) et n'est pas protégé : une seule entrée malformée d'un flux tiers interrompt toute la collecte (trace Python, pas de bilan, code 1) tant qu'elle reste dans le flux, ce qui contredit « une source en erreur n'arrête pas les autres » → isoler le traitement des entrées de chaque source (entrée ignorée ou source notée en erreur au bilan), test avec une entrée malformée — 🟡 major, error-handling
- `worker/src/veille_worker/collect.py:149` : seules `NoUsableTextError`/`LLMInvalidOutputError` sont capturées ; `httpx.InvalidURL` (pas une sous-classe de `httpx.HTTPError`, reproduit sur un hôte IDNA invalide) ou toute exception imprévue de trafilatura fait sortir le run sans incrémenter `attempts` : l'article reste `pending` et refait planter chaque collecte, les articles plus anciens ne sont plus jamais traités → capturer `httpx.InvalidURL` dans `extract_page_text` et ajouter un `except Exception` par article qui appelle `mark_failed` (en laissant remonter `LLMUnavailableError` et `psycopg.Error`) ; test « article empoisonné » — 🟡 major, error-handling
- `worker/src/veille_worker/llm.py:171-185` : la revalidation Python n'applique pas les `maxLength` du schéma (300 pour le titre, 500 par phrase), alors que la docstring promet de ne pas se fier au seul décodage contraint → vérifier les longueurs, ou partager les bornes entre `enrichment_schema` et `parse_enrichment` — 🟢 minor, backend
- `worker/src/veille_worker/collect.py:204` : rien n'empêche une collecte manuelle de tourner en même temps que celle de `worker-cron` ; les deux traitent les mêmes `pending` (double appel vLLM, `attempts` compté deux fois) → `pg_try_advisory_lock` au démarrage (aucun privilège requis), sortie propre si le verrou est pris — 🟢 minor, backend
- `web/database/migrations/2026_10_19_150003_grant_worker_privileges.php:59-62` : sur Postgres, un rôle worker absent ne produit qu'un avertissement de log et la migration est enregistrée comme jouée : elle ne repassera pas, et le worker échouera ensuite en `permission denied` → échouer franchement sur pgsql quand le rôle manque (ou le documenter dans le README d'exploitation) — 🟢 minor, error-handling
- `worker/tests/test_db.py:32` : le SQL de `Repository` (`ANY(%s)`, `articles_to_process`, `mark_*`) n'est couvert que par des contrôles texte/AST ; `test_collect.py` passe par un faux dépôt, donc une régression SQL ne se voit qu'en collecte réelle → un test pytest marqué `db` contre le Postgres de Compose — 🟢 minor, code-health
- `worker/src/veille_worker/feeds.py:63` : après le premier passage, les entrées non datées sont toujours admises ; un flux sans dates et avec une longue archive serait importé par tranches de `max_items_per_run` chaque jour, le défaut corrigé au §5 pour les entrées datées → limiter les entrées non datées (par exemple aux N premières du flux) ou le documenter comme limite connue — 🟢 minor, fit
- `aidd_docs/tasks/2026_10/2026_10_19_collecte-resume/plan.md:27` : la ligne Resources parle encore de privilèges par défaut accordés à `veille_worker`, ce que la migration de droits table par table remplace → aligner la ligne sur la décision — 🟢 minor, rot
- `aidd_docs/tasks/2026_10/2026_10_19_collecte-resume/evidence.md:193` : affirme que les 99 articles hors fenêtre sont restés en base, mais la base relue n'a que 130 lignes (99 summarized, 11 failed, 20 pending arXiv) : ils ont été supprimés depuis ; la ligne 202 donne aussi 111 tests Pest contre 112 aujourd'hui → noter la suppression (qui l'a faite, comment) et rafraîchir les gates — 🟢 minor, rot

## Round 2 · r-b7ba

- Date: 2026-10-19
- By: 95902
- Diff: `6d57ecc...d253cce`
- Axes: code, functional, relevancy
- Verdict: changes-requested
- Score: 10/12 met, 0 unmet, 2 unverified at runtime, 0 out of the diff

### Criteria

- [x] P1.1 Migrations Postgres et SQLite ; URL normalisée en double rejetée — Pest 112 passed (509 assertions), relancé en revue sur d253cce
- [x] P1.2 Seed : 7 catégories, ~10 sources, re-seed sans doublon — `web/tests/Feature/Schema/CollectSchemaTest.php` (Pest relancé)
- [x] P1.3 Admin gère sources et catégories ; non-admin 403 — `web/tests/Feature/Admin/*ResourceTest.php` (Pest relancé)
- [x] P1.4 `veille_worker` lit/écrit comme prévu, DELETE et CREATE refusés ; rôle absent → migration en échec — `web/database/migrations/2026_10_19_150003_grant_worker_privileges.php:21,63-67` ; `worker/tests/test_repository_db.py:160` (pytest -m db 10 passed, relancé en revue)
- [x] P2.1 Aucun DDL ni DELETE ; doublon d'URL sans erreur — `worker/tests/test_repository_db.py:85,160`
- [x] P2.2 Dédoublonnage, fenêtre 7 jours, plafond, non datées ≤ 3 — `worker/tests/test_feeds.py:25,87`, `worker/tests/test_collect.py:211` (pytest -m "not slow" 108 passed, 10 skipped, relancé)
- [x] P2.3 Page vide → contenu du flux ; budget respecté ; page refusée → repli — `worker/tests/test_extract.py:37,75,267` ; appel réel `fetch_html` en revue : python.org, github.blog, http://github.com → https (redirection) OK ; certificats invalides badssl (hostname, auto-signé, expiré) refusés ; localhost, ::1, 169.254.169.254 refusés
- [x] P2.4 Schéma imposé, bornes revalidées ; hors schéma → `failed` — `worker/src/veille_worker/llm.py:177-194`, `worker/tests/test_llm.py:156`
- [x] P2.5 Source injoignable au bilan sans bloquer ; 3 échecs → plus retenté ; article empoisonné → `failed` — `worker/tests/test_collect.py:184,258,273,286,310`
- Unverified at runtime: P3.1 `worker-cron` démarré, planification annoncée — evidence.md §4 relevé sur un head antérieur, non rejoué sur d253cce
- Unverified at runtime: P3.2 Collecte réelle (`summarized`, français, catégorisés, bilan) — evidence.md §2 relevé avant les corrections ; vLLM non démarré (consigne), base relue : 130 articles inchangés
- [x] P3.3 Mémoire décrit pipeline, garde-fous de fetch et verrou — `aidd_docs/memory/architecture.md:40-48`, `aidd_docs/memory/testing.md`, `aidd_docs/memory/coding-assertions.md`

### Findings

- `worker/src/veille_worker/collect.py:102` : une entrée de flux dont le lien dépasse 2048 caractères (colonnes `url`/`normalized_url` en `varchar(2048)`) lève `psycopg.errors.StringDataRightTruncation` (reproduit en revue avec `Repository.insert_article` en `veille_worker`, transaction annulée) ; `collect_sources` relance tout `psycopg.Error`, donc la collecte entière s'arrête (« base indisponible », code 1, aucun résumé) à chaque passage tant que l'entrée reste dans le flux : même classe de défaut que l'entrée malformée de r-69a1, sur le chemin d'insertion → dans `collect_source`, ignorer et compter (`skipped_entries`) les entrées dont `url` ou l'URL normalisée dépasse 2048 caractères (constante partagée avec le schéma), test avec un lien trop long — 🟡 major, error-handling
- `worker/src/veille_worker/collect.py:155` : si une erreur imprévue survient après des insertions (autocommit), la source est notée KO et `new_articles` ne compte pas les lignes déjà insérées : le bilan sous-estime → incrémenter `report.new_articles` à chaque insertion — 🟢 minor, error-handling
- `aidd_docs/tasks/2026_10/2026_10_19_collecte-resume/evidence.md:205-206` : les gates annoncent 106 passed / 9 skipped et 9 tests `db`, la suite en compte 108 / 10 et 10 (relancé en revue) → rafraîchir les chiffres — 🟢 minor, rot

## Round 3 · r-3e1d

- Date: 2026-10-19
- By: 95902
- Diff: `d253cce...d3c3d5d`
- Axes: code, functional, relevancy
- Verdict: changes-requested
- Score: 7/12 met, 0 unmet, 0 unverified at runtime, 5 out of the diff

### Criteria

- Out of the diff: phase 1 — schéma, seed, back-office, droits du rôle (4 criteria) ; Pest relancé en revue sur d3c3d5d : 112 passed (509 assertions)
- [x] P2.1 Aucun DDL ni DELETE ; doublon d'URL sans erreur — `worker/tests/test_repository_db.py:94,211` (pytest -m db 12 passed, relancé en revue sur d3c3d5d)
- [x] P2.2 Dédoublonnage, fenêtre 7 jours, plafond — `worker/src/veille_worker/collect.py:139-163`, `worker/tests/test_collect.py:274,292` (pytest -m "not slow" 111 passed, 12 skipped, relancé ; ruff OK)
- [x] P2.3 Page vide → contenu du flux ; budget respecté — `worker/tests/test_extract.py` (inchangé, suite relancée)
- [x] P2.4 Schéma imposé ; hors schéma → `failed` — `worker/tests/test_llm.py`, `worker/tests/test_collect.py` (inchangés, suite relancée)
- [x] P2.5 Source injoignable au bilan sans bloquer les autres ; 3 échecs → plus retenté — `worker/tests/test_collect.py:321` ; nouveaux articles comptés avant une erreur imprévue : `worker/tests/test_collect.py:303` ; URL > 2048 caractères ignorée et comptée : `worker/tests/test_collect.py:274`, `worker/tests/test_repository_db.py:176`
- [x] P3.1 `worker-cron` démarré, planification annoncée, rien au démarrage — evidence.md §7 « worker-cron » ; image `veille_techno-worker` (créée 15:57:59) extraite en revue : `src/veille_worker` identique octet pour octet à `worker/src/veille_worker` de d3c3d5d (`diff -r` vide)
- [x] P3.2 Collecte réelle : `summarized`, en français, catégorisés, bilan et extrait SQL — evidence.md §7 (41 puis 20 résumés, 0 échec, même image) ; base relue en revue (SELECT, `veille_worker`) : 160 summarized, 11 failed, 0 pending, 171 lignes / 171 `normalized_url` distinctes, 0 summarized sans catégorie/titre/résumé, 0 couple (source, titre) en double
- Out of the diff: phase 3 — P3.3 mémoire (1 criterion)

### Findings

- `worker/src/veille_worker/db.py:26-28` : `url_fits` compte des caractères, mais l'index unique `articles_normalized_url_unique` (btree) plafonne la ligne à 2704 octets ; feedparser garde les IRI non ASCII telles quelles (vérifié : `https://ex.org/文章/漢字`) et `normalize_url` ne les encode pas. Reproduit en revue en `veille_worker`, transaction annulée : URL de 1955 caractères CJK (5755 octets), `url_fits` → True, INSERT → `psycopg.errors.ProgramLimitExceeded: index row size 5768 exceeds btree version 4 maximum 2704`. C'est un `psycopg.Error`, relancé par `collect_sources` : toute la collecte s'arrête à chaque passage tant que l'entrée reste dans le flux — le défaut du round 2 subsiste pour les URL non ASCII → mesurer en octets UTF-8 (`len(clean_text(url).encode()) <= URL_MAX_CHARS` : 2048 octets tiennent sous 2704 et impliquent ≤ 2048 caractères), ajuster le commentaire « longueur en caractères », le faux dépôt (`worker/tests/helpers.py:100`) et ajouter une URL CJK au test `db` `test_url_limit_matches_the_articles_columns` — 🟡 major, error-handling
- `worker/src/veille_worker/collect.py:79` : le bilan affiche « Entrées ignorées (malformées) » alors que le compteur inclut désormais les URL trop longues (docstring `collect.py:98` à jour, libellé non) → « Entrées ignorées (malformées ou URL trop longue) » ou « Entrées ignorées » — 🟢 minor, rot
