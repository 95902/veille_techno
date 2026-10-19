# Contrat — collecte et résumé

## Objectif

Chaque jour, collecter les articles des sources RSS actives, extraire leur texte, et stocker pour chacun un titre français, un résumé de 3 phrases et une catégorie produits par vLLM ; les admins gèrent sources et catégories dans Filament.

## Périmètre

- **Schéma (migrations Laravel)** : `sources` (nom, URL du flux, type `rss`/`arxiv`, active), `categories` (nom, slug, description pour guider le LLM), `articles` (source, URL d'origine, URL normalisée unique, titre d'origine, titre FR, texte extrait, résumé, catégorie, date de publication, statut `pending`/`summarized`/`failed`, nombre d'essais, dernière erreur).
- **Filament** : ressources Sources et Catégories (CRUD, activation d'une source), réservées aux admins.
- **Seeders** : catégories *Modèles*, *Outils dev*, *Recherche*, *Réglementation*, *Sécurité*, *Business*, *Autre* ; ~10 sources de départ (labos IA, arXiv cs.AI et cs.CL, Hacker News, presse tech), URLs de flux vérifiées.
- **Worker** (`python -m veille_worker.collect`) :
  1. lit les sources actives ; premier passage limité aux 7 derniers jours ;
  2. normalise l'URL (sans `utm_*` ni fragment) et ignore les articles connus ;
  3. extrait le texte avec trafilatura ; repli sur le contenu du flux si l'extraction échoue ou est trop courte ; arXiv : résumé du flux ; texte tronqué pour tenir dans le contexte ;
  4. appelle vLLM avec une sortie JSON imposée (titre FR, résumé, slug de catégorie parmi la liste en base), résumé de 3 phrases, `max_tokens` borné ;
  5. écrit avec le rôle `veille_worker` (sans DDL, sans DELETE) ; statut `summarized`, ou `failed` avec erreur, retenté jusqu'à 3 essais aux collectes suivantes ;
  6. une source en erreur (flux injoignable, invalide) n'arrête pas les autres ; un résumé de fin (sources, nouveaux, résumés, échecs) est affiché.
- **Planification** : service Compose `worker-cron` (supercronic), collecte quotidienne à 6 h ; lancement manuel possible.

## Hors périmètre

Pages de lecture, recherche plein texte côté front, digest hebdomadaire, purge des articles, droit DELETE du worker.

## Critères d'acceptation

1. `php artisan migrate --force` crée les trois tables ; les seeders chargent catégories et sources ; le rôle worker peut lire `sources`/`categories` et écrire `articles`, mais ni DDL ni DELETE.
2. Un admin crée, modifie, désactive et supprime une source et une catégorie dans Filament ; un non-admin n'y a pas accès.
3. Une collecte sur des flux figés (tests) crée les articles attendus, ignore les doublons à la seconde passe, et n'importe que les 7 derniers jours au premier passage.
4. Chaque article résumé a un titre FR, un résumé de 3 phrases (vérifié par test sur la sortie structurée) et une catégorie existante ; une sortie invalide du LLM passe l'article en `failed`, retenté au plus 3 fois.
5. Une source injoignable est signalée sans bloquer les autres.
6. Collecte réelle contre les sources de départ et vLLM : des articles `summarized` en base, en français, catégorisés (preuve : extrait SQL et résumé de fin).
7. `worker-cron` démarre avec la planification quotidienne ; `docker compose run --rm worker-py python -m veille_worker.collect` fonctionne à la demande.
8. Tests Pest et pytest couvrant 1 à 5 ; gates de `aidd_docs/memory/coding-assertions.md` verts.

## Décisions

- Une catégorie par article, choisie dans la liste gérée par l'admin (slug) ; *Autre* en repli.
- Sortie JSON imposée par vLLM : élimine le parsing fragile et borne la longueur du résumé.
- URL normalisée comme clé de dédoublonnage.
- Pas de purge ni de DELETE : ~15k articles à 6 mois ne le justifient pas.
