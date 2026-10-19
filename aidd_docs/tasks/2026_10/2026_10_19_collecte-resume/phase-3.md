---
status: done
---

# Instruction: Planification et collecte réelle

## Architecture projection

> Tree of the final files. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── docker-compose.yml               ✏️ service worker-cron (image du worker, hors profil tools)
├── .env.example                     ✏️ COLLECT_SCHEDULE (défaut « 0 6 * * * »), fuseau horaire
├── worker/
│   ├── Dockerfile                   ✏️ supercronic installé (binaire figé + somme de contrôle)
│   ├── crontab                      ✅ planification de veille_worker.collect
│   └── README.md                    ✏️ lancement manuel et planifié
└── aidd_docs/memory/
    ├── architecture.md              ✏️ pipeline de collecte, plafond, sortie structurée
    └── codebase-map.md              ✏️ worker-cron, modules du worker
```

## User Journey

```mermaid
flowchart TD
  A[docker compose up -d] --> B[worker-cron démarré]
  B -->|chaque jour à 6 h| C[veille_worker.collect]
  D[docker compose run --rm worker-py python -m veille_worker.collect] --> C
  C --> E[articles summarized en base]
```

## Test Scope

```mermaid
---
title: Test scope
---
journey
  section Setup
    stack démarrée avec vLLM healthy, base migrée et seedée => prêt: 5: cli
  section Happy path
    docker compose ps => worker-cron Up, planification 0 6 * * * dans ses logs: 5: cli
    docker compose run --rm worker-py python -m veille_worker.collect => bilan avec articles résumés: 5: cli
    requête SQL sur articles => titres FR, résumés en français de 3 phrases, catégories renseignées: 5: cli
  section Edge case - vLLM arrêté
    vllm stoppé => collect => code de sortie non nul, message clair, aucun article perdu: 1: cli
  section Teardown
    docker compose down => volumes conservés: 5: cli
```

## Tasks to do

### `1)` Service planifié

> La collecte tourne seule chaque jour.

1. supercronic dans l'image du worker (version figée, somme de contrôle vérifiée).
2. `worker/crontab` et service `worker-cron` : mêmes variables que `worker-py`, `depends_on` postgres et vllm healthy, `restart: unless-stopped`, fuseau `Europe/Paris`.

### `2)` Collecte réelle

> Prouver le pipeline sur les vraies sources.

1. Migrer et seeder la base réelle, lancer une collecte manuelle complète.
2. Capturer : bilan de fin, `SELECT` de 5 articles (source, titre FR, résumé, catégorie), répartition par statut et par catégorie, durée totale.

### `3)` Mémoire

> Garder le contexte à jour.

1. Mettre à jour `architecture.md` et `codebase-map.md` (pipeline, plafond, sortie structurée, worker-cron).

## Test acceptance criteria

| Task | Acceptance criteria |
| ---- | ------------------- |
| 1 | `worker-cron` reste démarré et annonce la planification quotidienne ; il ne lance rien au démarrage |
| 2 | la collecte réelle laisse des articles `summarized`, en français, catégorisés ; le bilan et l'extrait SQL sont fournis |
| 3 | la mémoire décrit le pipeline et le service planifié sans contredire le code |
