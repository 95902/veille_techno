# Review: collecte et résumé

- Rounds: 1
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
