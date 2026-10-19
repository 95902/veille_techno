# Contrat — socle technique

## Objectif

Poser l'infrastructure et les squelettes décrits dans `aidd_docs/INSTALL.md`, sans aucune fonctionnalité métier, et prouver que vLLM résume en français sur la RTX 5070.

## Périmètre

- `docker-compose.yml` : services `nginx`, `app` (PHP-FPM 8.4), `postgres`, `vllm`, `worker-py`.
- `vllm` : image `vllm/vllm-openai` v0.28.0 figée par digest, modèle `Qwen/Qwen3-8B-AWQ`, `--max-model-len 8192`, `--gpu-memory-utilization 0.80`, volume nommé `hf_cache` propre au projet, port exposé uniquement sur `127.0.0.1:8000`.
- `web/` : Laravel 13, starter kit Vue (Inertia), panneau Filament installé sans ressource, connecté à PostgreSQL.
- `postgres` : script d'init créant le rôle propriétaire du schéma (Laravel), le rôle worker sans DDL, l'extension `unaccent`.
- `worker/` : projet Python (uv, `pyproject.toml`), module `veille_worker` avec une commande de test qui envoie un texte figé à vLLM et affiche le résumé en français ; `ruff` et `pytest` configurés.
- `.env.example` documentant chaque variable ; aucun secret commité.

## Hors périmètre

Collecte RSS, extraction, modèles métier, pages, digest, scheduler, sauvegarde `pg_dump`.

## Critères d'acceptation

1. `docker compose config` est valide.
2. `docker compose up -d` démarre `nginx`, `app`, `postgres` et `vllm` (`worker-py`, profil `tools`, se lance à la demande) ; `postgres` et `vllm` passent leur healthcheck.
3. `curl 127.0.0.1:8000/v1/models` liste `Qwen/Qwen3-8B-AWQ`.
4. La commande de test du worker, lancée dans `worker-py`, renvoie un résumé en français non vide.
5. `http://localhost` (via `nginx`) affiche la page d'accueil Laravel ; `/admin` affiche la connexion Filament.
6. `php artisan migrate --force` passe avec le rôle propriétaire ; le rôle worker ne peut pas créer de table (`CREATE TABLE` refusé).
7. Les gates de `aidd_docs/memory/coding-assertions.md` passent sur les squelettes (pint, lint front, ruff, pest, pytest, build front).

## Décisions

- Qwen3-8B-AWQ : Qwen3-14B-AWQ ne tient pas en VRAM (OOM à la conversion AWQ) et Qwen3-4B fait nettement plus de fautes ; repli 4B par simple changement de `.env`.
- Cache de modèles dans un volume propre au projet : aucune dépendance au volume d'agent-editorial.
- Inscription publique désactivée dès le socle : les comptes sont créés par l'admin.
- vLLM n'est pas exposé hors de la machine.
