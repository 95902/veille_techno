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
| `infra/postgres/init/01-roles.sh` (repo) | `veille_worker` reçoit SELECT/INSERT/UPDATE par défaut sur les tables créées par `veille_app`, ni DDL ni DELETE |
| `worker/src/veille_worker/llm.py` (repo) | point d'appel unique vLLM, thinking désactivé, erreurs converties en `LLMUnavailableError` |
| `.env.example` (repo) | `VLLM_MAX_MODEL_LEN=8192` : budget texte d'entrée à borner |

## Decisions

| Decision | Why |
| -------- | --- |
| Résumé en tableau JSON de exactement 3 phrases (`minItems = maxItems = 3`), catégorie en `enum` des slugs en base | le décodage contraint garantit structurellement les 3 phrases et une catégorie valide |
| Plafond d'articles par source et par passage (colonne `max_items_per_run`, défaut 20) | arXiv cs.AI/cs.CL publient des centaines d'articles par jour : sans plafond, le volume et le temps GPU explosent |
| Le worker lit `sources`/`categories` et écrit `articles` en SQL brut (psycopg) ; aucune migration côté Python | Laravel reste seul propriétaire du schéma |
| `worker-cron` réutilise l'image du worker et tourne en continu (hors profil `tools`) | la planification doit survivre aux redémarrages sans dépendre du cron de l'hôte |
