---
objective: "Une collecte quotidienne remplit la table articles avec titre FR, résumé de 3 phrases et catégorie produits par vLLM, à partir de sources gérées dans Filament."
status: implemented
---

# Plan: Collecte et résumé

## Overview

| Field      | Value                                                        |
| ---------- | ------------------------------------------------------------ |
| **Goal**   | Schéma, back-office sources/catégories, pipeline worker RSS → extraction → vLLM, cron quotidien |
| **Source** | `aidd_docs/tasks/2026_10/2026_10_19_collecte-resume/contract.md` |

## Phases

| #   | Phase                                              | File                         |
| --- | -------------------------------------------------- | ---------------------------- |
| 1   | Schéma, seeders, ressources Filament               | [`phase-1.md`](./phase-1.md) |
| 2   | Pipeline worker (flux, extraction, vLLM, écriture) | [`phase-2.md`](./phase-2.md) |
| 3   | Planification et collecte réelle                   | [`phase-3.md`](./phase-3.md) |

## Resources

| Source | Verified |
| ------ | -------- |
| `web/database/migrations/2026_10_19_150003_grant_worker_privileges.php` (repo) | droits de `veille_worker` accordés table par table par migration (SELECT `sources`/`categories`, SELECT/INSERT/UPDATE `articles` et sa séquence), privilèges par défaut révoqués, ni DDL ni DELETE ; l'init Postgres ne donne que CONNECT et USAGE |
| `worker/src/veille_worker/llm.py` (repo) | point d'appel unique vLLM, thinking désactivé, erreurs converties en `LLMUnavailableError` |
| `.env.example` (repo) | `VLLM_MAX_MODEL_LEN=8192` : budget texte d'entrée à borner |

## Decisions

| Decision | Why |
| -------- | --- |
| Résumé en tableau JSON de exactement 3 phrases (`minItems = maxItems = 3`), catégorie en `enum` des slugs en base | le décodage contraint garantit structurellement les 3 phrases et une catégorie valide |
| Plafond d'articles par source et par passage (colonne `max_items_per_run`, défaut 20) | arXiv cs.AI/cs.CL publient des centaines d'articles par jour : sans plafond, le volume et le temps GPU explosent |
| Le worker lit `sources`/`categories` et écrit `articles` en SQL brut (psycopg) ; aucune migration côté Python | Laravel reste seul propriétaire du schéma |
| `worker-cron` réutilise l'image du worker et tourne en continu (hors profil `tools`) | la planification doit survivre aux redémarrages sans dépendre du cron de l'hôte |

## Amendments

| Date | Amendment | Why |
| ---- | --------- | --- |
| 2026-10-19 | Après le premier passage d'une source, entrées non datées plafonnées à 3 par source et par passage (les premières du flux), en plus de `max_items_per_run` et de la fenêtre de 7 jours des entrées datées (décision utilisateur, revue r-69a1) | un flux sans dates à longue archive serait sinon importé par tranches de `max_items_per_run` chaque jour |
