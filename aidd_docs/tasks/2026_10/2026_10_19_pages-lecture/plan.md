---
objective: "Un collaborateur connecté parcourt, filtre par catégorie, cherche sans accents et ouvre le détail des articles résumés."
status: pending
---

<!-- Fill or omit these sections; never add, rename, or reorder one. -->

# Plan: pages de lecture

## Overview

| Field      | Value                                                                 |
| ---------- | --------------------------------------------------------------------- |
| **Goal**   | Liste filtrable, recherche plein texte FR sans accents, page de détail |
| **Source** | `aidd_docs/tasks/2026_10/2026_10_19_pages-lecture/contract.md`         |

## Phases

| #   | Phase                                  | File                         |
| --- | -------------------------------------- | ---------------------------- |
| 1   | Recherche plein texte et base de test  | [`phase-1.md`](./phase-1.md) |
| 2   | Pages de lecture et navigation         | [`phase-2.md`](./phase-2.md) |

## Resources

| Source                                                             | Verified                                                                                   |
| ------------------------------------------------------------------ | ------------------------------------------------------------------------------------------ |
| https://www.postgresql.org/docs/16/unaccent.html                   | configuration `COPY = french` + `ALTER MAPPING … WITH unaccent, french_stem`                |
| https://www.postgresql.org/docs/16/ddl-generated-columns.html      | colonne `GENERATED ALWAYS AS (…) STORED` : expression immuable, non écrite par les INSERT/UPDATE |
| https://www.postgresql.org/docs/16/sql-createextension.html        | `unaccent` est « trusted » : créable par le propriétaire de la base (`veille_app`) sans superutilisateur |
| https://www.postgresql.org/docs/16/textsearch-controls.html        | `websearch_to_tsquery` (syntaxe tolérante aux saisies libres) et `ts_rank`                  |

## Decisions

| Decision                                                         | Why                                                                                         |
| ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| Colonne générée `search_vector` + GIN plutôt que trigger ou index d'expression | Toujours à jour quand le worker écrit `title_fr`/`summary`, sans code ni droit en plus côté worker |
| Base `veille_test` dédiée pour le groupe Pest `pgsql`            | `RefreshDatabase` vide la base visée : jamais la base `veille`                               |
