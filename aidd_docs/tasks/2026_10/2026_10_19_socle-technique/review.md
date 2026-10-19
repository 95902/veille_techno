# Review: socle technique

- Rounds: 1
- Started: 2026-10-19

## Round 1 · r-2976

- Date: 2026-10-19
- By: 95902
- Diff: `main...feat/socle-technique`
- Axes: code, functional, relevancy
- Verdict: changes-requested
- Score: 2/11 met, 0 unmet, 9 unverified at runtime, 0 out of the diff

### Criteria

- [x] Phase 1 / T1 : `.env` non suivi ; chaque variable de `.env.example` commentée — `.gitignore:2`, `web/.gitignore:18`, `.env.example:3-40` ; `git log --all -- .env web/.env` vide
- Unverified at runtime: Phase 1 / T2 : postgres healthy, `unaccent` installée, `CREATE TABLE` refusé à `veille_worker` — logique statique correcte (`infra/postgres/init/01-roles.sh:19-33`) ; seule une exécution montre le refus (affirmé par l'implémenteur, sans sortie jointe)
- Unverified at runtime: Phase 1 / T3 : vllm healthy, `/v1/models` liste le modèle, port 8000 sur 127.0.0.1 seulement — le bind 127.0.0.1 est vérifié (`docker-compose.yml:77`, `docker compose config` → `host_ip: 127.0.0.1`) ; « sans téléchargement » est périmé depuis l'amendement du contrat (volume `hf_cache` en lecture-écriture, `HF_HUB_OFFLINE=0` au premier démarrage)
- Unverified at runtime: Phase 2 / T1 : `uv sync` installe, `uv run pytest` découvre les tests — affirmé (4 passed), non rejoué
- [x] Phase 2 / T2 : chaque requête envoie le modèle configuré avec le thinking désactivé — `worker/src/veille_worker/llm.py:29-37`, assertion `worker/tests/test_llm.py:28-30` ; absence de bloc de raisonnement : `--reasoning-parser qwen3` (`docker-compose.yml:64-65`) et `worker/tests/test_smoke_vllm.py:12`
- Unverified at runtime: Phase 2 / T3 : la commande affiche un résumé français, erreur explicite si vLLM arrêté — chemin d'erreur de connexion présent (`smoke.py:23-25`, `llm.py:38-39`) ; le résumé n'est montrable que par une exécution
- Unverified at runtime: Phase 2 / T4 : `docker compose run --rm worker-py python -m veille_worker.smoke` réussit — affirmé
- Unverified at runtime: Phase 3 / T1 : `php artisan migrate` crée les tables en `veille_app` — affirmé
- Unverified at runtime: Phase 3 / T2 : `/admin` affiche la connexion Filament, aucune ressource — aucune ressource vérifié (`web/app/Filament/` absent, `AdminPanelProvider.php:28-45`) ; écran de connexion : aucune preuve fournie, aucun test
- Unverified at runtime: Phase 3 / T3 : `http://localhost` via nginx ; FPM non publié — non-publication vérifiée (`docker-compose.yml:15-34`, aucun `ports`) ; page d'accueil : aucune preuve fournie
- Unverified at runtime: Phase 3 / T4 : pint, lint front, Pest, build front passent — affirmé (56 fichiers, 0 erreur, 41 passed, build OK), non rejoué

### Findings

- `web/.env.example:2-4` : `APP_ENV=local` et `APP_DEBUG=true` (recopiés tels quels dans `web/.env` en service) alors que `docker-compose.yml:8` publie nginx sur `0.0.0.0:80` pour les collaborateurs du LAN ; pages d'erreur détaillées servies au réseau, et Filament, sans `canAccessPanel`, ouvre `/admin` à tout utilisateur authentifié en environnement `local` → fixer `APP_ENV`/`APP_DEBUG` dans `environment:` du service `app` depuis le `.env` racine (défaut `production`/`false`), ou lier nginx à `127.0.0.1:80` jusqu'au ticket comptes — 🟡 major, security
- `docker-compose.yml:97` : `env_file: .env` injecte dans `worker-py` `POSTGRES_PASSWORD` (superutilisateur), `APP_DB_PASSWORD` (propriétaire du schéma) et `APP_KEY` ; le rôle worker sans DDL est contourné au niveau des identifiants → remplacer par une liste `environment:` explicite (`VLLM_MODEL`, `VLLM_BASE_URL`, `WORKER_DB_PASSWORD`, hôte/utilisateur `veille_worker`) — 🟡 major, security
- `aidd_docs/tasks/2026_10/2026_10_19_socle-technique/plan.md:38` : la décision « cache externe `agent-editorial_vllm_hf_cache` en lecture seule, `HF_HUB_OFFLINE=1` » contredit le contrat amendé (`contract.md:33`) et le code (`docker-compose.yml:69-72`) ; idem `phase-1.md:31,46,63,81` (Qwen3-14B-AWQ, volume externe) et `infra/vllm/README.md:13` (« cible du contrat : 14B ») → aligner plan et phase 1 sur l'amendement (ou ajouter une note d'amendement datée) et reformuler le README — 🟡 major, incoherence
- `docker-compose.yml:49` : `pg_isready` sans `-h` passe par le socket Unix et répond pendant le serveur temporaire d'init, avant la fin de `01-roles.sh` ; au premier démarrage, `app`/`worker-py` peuvent se connecter avant la création des rôles → `pg_isready -h 127.0.0.1 -U ... -d ...` — 🟢 minor, backend
- `infra/postgres/init/01-roles.sh:21-22` : `TEMPORARY` sur la base reste accordé à `PUBLIC`, `veille_worker` peut `CREATE TEMP TABLE` → `REVOKE TEMPORARY ON DATABASE :"db" FROM PUBLIC;` — 🟢 minor, security
- `worker/src/veille_worker/llm.py:38` : seule `APIConnectionError` est traduite ; un modèle non servi ou une erreur HTTP (`APIStatusError`) remonte en trace brute, contre « message d'erreur clair » de la phase 2 → capturer `openai.APIError` et lever `LLMUnavailableError` (ou une erreur dédiée) — 🟢 minor, error-handling
- `worker/Dockerfile:18` : le `CMD` lance le smoke test à chaque `docker compose up -d` (requête vLLM et attente de vllm healthy), alors que la phase 2 prévoit un service « sans commande longue, lancé à la demande » → `profiles: ["tools"]` sur `worker-py` ou `CMD` neutre — 🟢 minor, architecture
- `web/.github/workflows/tests.yml:1` : CI et dependabot du starter kit inertes dans un sous-dossier ; `web/pnpm-workspace.yaml` à côté de `package-lock.json` ; `CreateNewUser` toujours câblé (`FortifyServiceProvider.php:43`) alors que l'inscription est désactivée → supprimer `web/.github/` et `pnpm-workspace.yaml`, garder `CreateNewUser` seulement s'il sert au futur ticket comptes — 🟢 minor, rot
- `web/.env.example:23-29` : paramètres `DB_*` dupliqués avec `docker-compose.yml:23-28`, qui prime ; deux sources pour la même valeur → garder une seule source canonique (compose) et réduire `web/.env.example` à un renvoi — 🟢 minor, rot
- `web/tests/Feature/Auth/RegistrationTest.php:1` : aucun test ne couvre `/admin/login` ni `/` (critère 5 du contrat), et `phpunit.xml:26-27` force SQLite, donc aucun test ne touche PostgreSQL → ajouter `get('/admin/login')->assertOk()` et `get('/')->assertOk()`, et joindre la sortie `curl` des deux pages — 🟢 minor, standards
