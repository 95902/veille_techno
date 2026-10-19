# Contrat — pages de lecture

## Objectif

Un collaborateur connecté parcourt les articles résumés, les filtre par catégorie, les cherche en français (accents ignorés) et ouvre le détail d'un article.

## Périmètre

- **Accès** : pages réservées aux utilisateurs connectés et vérifiés ; un invité est renvoyé vers la connexion.
- **Accueil** : `/` affiche la liste pour un connecté ; la page Dashboard du kit et sa route sont supprimées, la redirection après connexion vise `/`.
- **Liste** (`/`) :
  - articles `summarized` seulement ;
  - tri par date de publication décroissante (repli sur la date de collecte) ; par pertinence quand une recherche est active ;
  - pagination de 20 ;
  - filtre par catégorie (`?categorie=<slug>`) et recherche (`?q=…`), combinables, conservés dans l'URL et la pagination ;
  - carte : titre FR (repli titre d'origine), source, date, catégorie, résumé de 3 lignes, lien vers le détail.
- **Détail** (`/articles/{id}`) : titre FR, titre d'origine, source, date, catégorie, résumé, lien vers l'article d'origine (nouvel onglet, `rel="noopener noreferrer"`) ; 404 pour un article non `summarized`. Le texte extrait n'est pas affiché.
- **Recherche plein texte (migration Laravel, Postgres)** :
  - extension `unaccent` et configuration `fr_unaccent` (dictionnaire `unaccent` puis `french_stem`) ;
  - colonne générée `search_vector` : titre FR (poids A), résumé (B), titre d'origine (C) ; index GIN ;
  - requête `websearch_to_tsquery('fr_unaccent', q)`, classement `ts_rank`.
- **Navigation** : entrée « Articles » dans la barre latérale ; libellés en français.
- **Tests** : Pest en SQLite pour accès, liste, filtre, pagination, détail ; groupe Pest `pgsql` contre une base `veille_test` du Postgres de Compose pour la recherche, ignoré si la base est absente.

## Hors périmètre

Digest, favoris ou statut lu/non lu, surlignage des termes, affichage du texte extrait, changements du back-office et du worker.

## Critères d'acceptation

1. Un invité qui ouvre `/` ou `/articles/{id}` est redirigé vers la connexion ; un connecté vérifié voit la liste.
2. La liste n'affiche que des articles `summarized`, du plus récent au plus ancien, 20 par page.
3. `?categorie=securite` ne montre que cette catégorie ; un slug inconnu donne une liste vide sans erreur.
4. Une recherche `securite` trouve un article dont le titre ou le résumé contient « sécurité », et inversement ; les résultats sont classés par pertinence et combinables avec le filtre de catégorie.
5. Le détail d'un article `summarized` affiche ses champs et le lien d'origine ; un article `pending` ou `failed` renvoie 404.
6. La migration passe sur la base réelle (`migrate --force`) sans casser l'écriture du worker (collecte manuelle ou test `-m db` vert).
7. Contrôle visuel sur la base réelle (160 articles) : liste, filtre, recherche accentuée, détail (preuve : captures).
8. Gates de `aidd_docs/memory/coding-assertions.md` verts, plus le groupe `pgsql`.

## Décisions

- `/` devient la liste : un seul point d'entrée pour les lecteurs.
- Recherche dans la base (colonne générée + GIN) : pas de moteur externe, ~15k articles à 6 mois.
- Le texte extrait n'est pas affiché : le lien d'origine suffit et évite de republier le contenu des sources.
- Base de test Postgres dédiée : le SQL de recherche est testé tel qu'il tourne en production ; le reste des tests garde SQLite.
