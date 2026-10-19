# Preuves — collecte et résumé (2026-10-19)

Environnement : stack Compose locale, vLLM v0.28.0 (`Qwen/Qwen3-8B-AWQ`, max-model-len 8192, gpu-memory-utilization 0.80, `--reasoning-parser qwen3`), Postgres 16. Base réelle `veille` migrée (`php artisan migrate --force`) et seedée (`php artisan db:seed --force`, lancé deux fois : aucun doublon, 7 catégories, 11 sources). Aucun plafond abaissé : `max_items_per_run` des seeders (20, 10 pour arXiv).

## 1. Droits du rôle `veille_worker` (psql, rôle `veille_worker`)

| Requête | Résultat |
| ------- | -------- |
| `SELECT count(*) FROM sources` / `categories` | 11 / 7 |
| `INSERT INTO articles …` puis `UPDATE articles …` (transaction annulée) | OK |
| `DELETE FROM articles …` | `ERROR: permission denied for table articles` |
| `CREATE TABLE intrus …` | `ERROR: permission denied for schema public` |
| `ALTER TABLE articles …` / `DROP TABLE articles` | `ERROR: must be owner of table articles` |
| `CREATE TEMP TABLE …` | `ERROR: permission denied to create temporary tables` |
| `TRUNCATE articles` | `ERROR: permission denied for table articles` |

## 2. Collecte réelle complète

Commande : `docker compose run --rm worker-py python -m veille_worker.collect` — de 15:12:48 à 15:16:32 (3 min 44 s au total, conteneur compris), code de sortie 0.

```text
[source] OpenAI News : 12 entrées (premier passage, 7 j), 12 nouvelles
[source] Google DeepMind : 5 entrées (premier passage, 7 j), 5 nouvelles
[source] Hugging Face Blog : 8 entrées (premier passage, 7 j), 8 nouvelles
[source] arXiv cs.AI : 344 entrées (premier passage, 7 j), 10 nouvelles
[source] arXiv cs.CL : 226 entrées (premier passage, 7 j), 10 nouvelles
[source] Hacker News (IA, 100 points) : 20 entrées (premier passage, 7 j), 20 nouvelles
[source] The Verge – IA : 10 entrées (premier passage, 7 j), 9 nouvelles
[source] MIT Technology Review – IA : 4 entrées (premier passage, 7 j), 4 nouvelles
[source] Simon Willison : 18 entrées (premier passage, 7 j), 18 nouvelles
[source] ActuIA : 9 entrées (premier passage, 7 j), 9 nouvelles
[source] Le Monde Informatique – IA : 5 entrées (premier passage, 7 j), 5 nouvelles
[llm] 110 article(s) à résumer
[llm] 1/110 #107 [securite] G7 opte pour le cloud SecNumCloud de S3NS pour ses traitements d'IA
…
[llm] 51/110 #3 ÉCHEC : aucun texte exploitable (133 caractères, minimum 150)
[llm] 52/110 #4 ÉCHEC : aucun texte exploitable (146 caractères, minimum 150)
… (11 échecs au total, tous OpenAI News)
=== Bilan de la collecte ===
Sources : 11 OK, 0 en erreur
Nouveaux articles : 110
Résumés : 99
Échecs : 11
Durée : 222 s
```

Les 11 échecs sont tous des articles OpenAI News : openai.com répond 403 au téléchargement de la page (quel que soit le User-Agent) et le flux ne porte qu'un chapeau de 120 à 149 caractères, sous le minimum de 150. Ils seront retentés jusqu'à 3 essais.

### Répartition par statut, par catégorie, par source ; contrôle des 3 phrases

```text
   status   | count 
------------+-------
 failed     |    11
 summarized |    99
(2 rows)

   categorie    | count 
----------------+-------
 Autre          |    31
 Modèles        |    19
 Recherche      |    13
 (aucune)       |    11
 Outils dev     |    11
 Sécurité       |    11
 Réglementation |     8
 Business       |     6
(8 rows)

            source            | resumes | echecs 
------------------------------+---------+--------
 ActuIA                       |       9 |      0
 arXiv cs.AI                  |      10 |      0
 arXiv cs.CL                  |      10 |      0
 Google DeepMind              |       5 |      0
 Hacker News (IA, 100 points) |      20 |      0
 Hugging Face Blog            |       8 |      0
 Le Monde Informatique – IA   |       5 |      0
 MIT Technology Review – IA   |       4 |      0
 OpenAI News                  |       1 |     11
 Simon Willison               |      18 |      0
 The Verge – IA               |       9 |      0
(11 rows)

 resumes_3_lignes | total 
------------------+-------
               99 |    99
(1 row)
```

### 5 articles résumés (un par source : ActuIA, arXiv cs.CL, Google DeepMind, Hacker News, The Verge)

```text
-[ RECORD 1 ]------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
source    | ActuIA
title     | Anthropic propose de ne bloquer un modèle qu'en cas de risque imminent de plus de 50 morts ou blessés graves, ou 1 Md$
title_fr  | Anthropic propose un seuil de risque strict pour bloquer ses modèles
summary   | Anthropic a publié un brouillon de cadre réglementaire qui définit des seuils de risque pour bloquer ses modèles, notamment un seuil de 50 victimes ou 1 Md$ de dommages.                              +
          | Le cadre propose un ordre de blocage émis par un juge fédéral après une évaluation par des experts indépendants, avec une procédure de 72 heures de préavis.                                           +
          | Le texte reprend des seuils inspirés de la loi californienne et du FRONTIER Act, mais il prévoit une préemption des lois d'États, ce qui a suscité des critiques.
categorie | reglementation
-[ RECORD 2 ]------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
source    | arXiv cs.CL
title     | AuditKIT: A Unified Evaluation Spine for Benchmarking, Judging, and Comparing Large Language Models and Agentic Systems
title_fr  | AuditKIT : Un outil unifié pour l'évaluation des grands modèles linguistiques et systèmes agents
summary   | AuditKIT est une bibliothèque d'évaluation open source conçue pour comparer et évaluer les grands modèles linguistiques et systèmes agents de manière unifiée.                                         +
          | Elle combine des métriques de précision, des évaluations basées sur des jugements, des performances en temps réel, des comportements d'utilisation d'outils et la qualité de la récupération.          +
          | AuditKIT permet d'identifier les échecs dans les workflows agents en marquant les preuves manquantes ou non observables comme non notées plutôt que comme des échecs.
categorie | modeles
-[ RECORD 3 ]------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
source    | Google DeepMind
title     | Accelerating the search for antimicrobial peptides with Google Antigravity
title_fr  | Accélérer la recherche de peptides antimicrobiens avec Google Antigravity
summary   | Google a développé Antigravity, une plateforme d'innovation agente, pour accélérer la découverte de nouveaux antibiotiques en identifiant des peptides antimicrobiens (AMPs) prometteurs.              +
          | Le modèle ProtNLM, entraîné pour prédire la fonction biologique à partir de séquences d'acides aminés, permet d'annoter des millions d'entrées dans UniProt avec des étiquettes fonctionnelles fiables.+
          | La plateforme intègre une visualisation 3D pour aider les chercheurs à explorer les structures moléculaires et à interagir avec l'IA pour des analyses avancées.
categorie | outils-dev
-[ RECORD 4 ]------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
source    | Hacker News (IA, 100 points)
title     | Websites are closing their doors to AI agents
title_fr  | Les sites web ferment leurs portes aux agents d'intelligence artificielle
summary   | Plusieurs services web comme Yelp, Delta Air Lines, JPMorgan Chase et Charles Schwab bloquent l'accès aux agents d'IA en raison de préoccupations de sécurité.                                         +
          | Amazon a déjà interdit l'utilisation d'agents d'IA pour le shopping et a engagé une lutte juridique contre Perplexity, soulignant des questions légales et pratiques.                                  +
          | Les agents d'IA, bien que développés par des entreprises comme OpenAI, Meta et Google, rencontrent des obstacles avec les systèmes anti-bot et les politiques des sites web.
categorie | securite
-[ RECORD 5 ]------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
source    | The Verge – IA
title     | Democrats think cracking down on AI could give them an edge
title_fr  | Les démocrates pensent que des mesures strictes contre l'IA pourraient leur donner un avantage
summary   | Les démocrates pourraient récupérer le contrôle du Congrès en novembre et envisagent d'appliquer des mesures strictes contre l'IA pour se positionner politiquement.                                   +
          | Des sondages prévoient que les démocrates prendront le contrôle d'au moins une chambre du Congrès, ce qui pourrait entraîner une surveillance accrue des entreprises d'IA.                             +
          | Des groupes comme Tomorrow Together lancent des campagnes pour attaquer les candidats républicains sur l'IA et préparent leur stratégie pour les élections de 2028.
categorie | business

```

## 3. vLLM arrêté

`docker compose stop vllm`, puis `docker compose run --rm --no-deps worker-py python -m veille_worker.collect` (image d'avant la correction de la fenêtre, voir § 5) :

```text
[source] OpenAI News : 1299 entrées (suivi), 20 nouvelles
[source] Google DeepMind : 100 entrées (suivi), 20 nouvelles
[source] Hugging Face Blog : 881 entrées (suivi), 20 nouvelles
[source] arXiv cs.AI : 344 entrées (suivi), 10 nouvelles
[source] arXiv cs.CL : 226 entrées (suivi), 10 nouvelles
[source] Hacker News (IA, 100 points) : 20 entrées (suivi), 0 nouvelles
[source] The Verge – IA : 10 entrées (suivi), 0 nouvelles
[source] MIT Technology Review – IA : 10 entrées (suivi), 6 nouvelles
[source] Simon Willison : 30 entrées (suivi), 12 nouvelles
[source] ActuIA : 15 entrées (suivi), 6 nouvelles
[source] Le Monde Informatique – IA : 20 entrées (suivi), 15 nouvelles
[llm] 130 article(s) à résumer
=== Bilan de la collecte ===
Sources : 11 OK, 0 en erreur
Nouveaux articles : 119
Résumés : 0
Échecs : 0
Durée : 3 s
Interrompue : vLLM injoignable à http://vllm:8000/v1 : Connection error.
Erreur : vLLM injoignable à http://vllm:8000/v1 : Connection error.
exit=1
```

Aucun article perdu ni pénalisé : les nouveaux articles restent `pending`, `attempts = 0`.

## 4. `worker-cron`

`docker compose up -d --wait` puis `docker compose logs worker-cron` (statut : `Up`, 0 redémarrage) :

```text
worker-cron-1  | level=info msg="read crontab: /tmp/crontab"
worker-cron-1  | level=info msg="crontab is valid"
worker-cron-1  | Collecte planifiée : '0 6 * * *' (fuseau Europe/Paris)
worker-cron-1  | level=info msg="reaping dead processes"
worker-cron-1  | level=info msg="read crontab: /tmp/crontab"
```

Crontab rendue dans le conteneur : `0 6 * * * python -m veille_worker.collect` ; `date` dans le conteneur : `CEST`. Aucune collecte lancée au démarrage.

## 5. Constat et correction : archive des flux

Le passage « vLLM arrêté » (2e passage, donc hors premier passage) a importé 119 articles dont 99 publiés avant la fenêtre de 7 jours (jusqu'au 2026-07-30) : sans filtre de date après le premier passage, chaque collecte aurait importé l'archive des flux (1 299 entrées chez OpenAI) par tranches de `max_items_per_run`. Correction : la fenêtre de 7 jours s'applique à tous les passages (les entrées non datées sont admises après le premier). Contrôle en lecture seule après correction, sur la base réelle :

```text
OpenAI News: 12 entrées dans la fenêtre, 0 inconnues (plafond 20)
Google DeepMind: 5 entrées dans la fenêtre, 0 inconnues (plafond 20)
Hugging Face Blog: 8 entrées dans la fenêtre, 0 inconnues (plafond 20)
arXiv cs.AI: 344 entrées dans la fenêtre, 321 inconnues (plafond 10)
arXiv cs.CL: 226 entrées dans la fenêtre, 202 inconnues (plafond 10)
```

Les 99 articles hors fenêtre déjà insérés (`id > 111`, `status = 'pending'`, `published_at < now() - interval '7 days'`) n'ont pas pu être supprimés par le worker (pas de droit DELETE). Ils ont été supprimés le 2026-10-19 par l'orchestrateur, avec l'accord explicite de l'utilisateur : `DELETE` exécuté en `veille_app` avec les critères `id > 111 AND status = 'pending' AND published_at < now() - interval '7 days'`, 99 lignes. Base relue ensuite : 130 articles (99 `summarized`, 11 `failed`, 20 `pending`).

## 6. Gates

Relancés le 2026-10-19 après les corrections de la revue, round 2 (URL plus longue que la colonne, comptage incrémental des nouveaux articles).

| Commande | Résultat |
| -------- | -------- |
| `pint --test` | PASS (103 fichiers) |
| `npm run lint` | 0 avertissement, 0 erreur |
| `uv run ruff check .` | All checks passed |
| `pest` | 112 tests, 509 assertions, PASS |
| `uv run pytest -m "not slow"` (sans base) | 111 passed, 12 skipped (`db`) |
| `uv run pytest -m db` (Postgres de Compose, `veille_worker`) | 12 passed, aucune ligne laissée en base |
| `uv run pytest` (vLLM démarré) | non relancé ; dernier passage : 63 passed dont 2 `slow` |
| `npm run build` | OK |

Contrôle des nouveaux tests sur le code d'avant la correction : les 2 tests unitaires (URL de 2 049 caractères ignorée et comptée ; nouveaux articles comptés avant une erreur imprévue de la source) et le test `db` de collecte échouent (`StringDataRightTruncation: value too long for type character varying(2048)`), puis passent après.

## 7. Re-preuve sur head corrigé (2026-10-19)

Code : `d253cce` plus les corrections round 2 non commitées (`collect.py`, `db.py`, tests). Image `veille_techno-worker` reconstruite (`docker compose build worker-cron`, même image que `worker-py`), puis `docker compose up -d --wait` : les 5 services `Up`, Postgres et vLLM `healthy`. Base réelle avant passage : 130 articles (99 `summarized`, 11 `failed`, 20 `pending`). OpenAI News est inactive en base (10 sources actives) ; ses 11 articles `failed` sont au plafond de 3 essais et ne sont plus retentés.

### Première collecte manuelle

`docker compose run --rm worker-py python -m veille_worker.collect` — 85 s au total (conteneur compris), code de sortie 0.

```text
[source] Google DeepMind : 5 entrées (suivi, 7 derniers jours), 0 nouvelles
[source] Hugging Face Blog : 8 entrées (suivi, 7 derniers jours), 0 nouvelles
[source] arXiv cs.AI : 344 entrées (suivi, 7 derniers jours), 10 nouvelles
[source] arXiv cs.CL : 226 entrées (suivi, 7 derniers jours), 10 nouvelles
[source] Hacker News (IA, 100 points) : 20 entrées (suivi, 7 derniers jours), 0 nouvelles
[source] The Verge – IA : 10 entrées (suivi, 7 derniers jours), 1 nouvelles
[source] MIT Technology Review – IA : 4 entrées (suivi, 7 derniers jours), 0 nouvelles
[source] Simon Willison : 18 entrées (suivi, 7 derniers jours), 0 nouvelles
[source] ActuIA : 9 entrées (suivi, 7 derniers jours), 0 nouvelles
[source] Le Monde Informatique – IA : 4 entrées (suivi, 7 derniers jours), 0 nouvelles
[llm] 41 article(s) à résumer
[llm] 1/41 #284 [securite] Un hackeur a pénétré John Deere et SharkNinja grâce à une armée d'agents d'IA
…
=== Bilan de la collecte ===
Sources : 10 OK, 0 en erreur
Nouveaux articles : 21
Entrées ignorées (malformées) : 0
Résumés : 41
Échecs : 0
Durée : 84 s
```

Les 41 résumés = les 20 articles arXiv `pending` + les 21 nouveaux. Base après passage : 151 articles (140 `summarized`, 11 `failed`, 0 `pending`), 151 `normalized_url` distinctes. Les identifiants sautent de 191 à 265 : la séquence avance avec les tests `db` (transactions annulées) et les `ON CONFLICT DO NOTHING`.

### 3 nouveaux résumés

```text
#284 | The Verge – IA | securite
title_fr : Un hackeur a pénétré John Deere et SharkNinja grâce à une armée d'agents d'IA
summary  : Un hackeur a compromis plus de 100 sites web en utilisant une armée d'agents d'IA, selon une enquête de la firme de sécurité Norforge.
           Les attaques ont visé des entreprises comme John Deere, SharkNinja et Cummins, avec des intrusions réussies en moins de 24 heures.
           Norforge a découvert ces attaques via l'exploitation d'une plateforme open-source appelée Cairn, utilisée pour orchestrer les cyberattaques via des agents d'IA.

#283 | arXiv cs.CL | modeles
title_fr : Attention par passage initial : une nouvelle approche pour améliorer l'attention dans les modèles de langage
summary  : Le texte présente First Passage Attention (FPA), une méthode qui améliore l'attention softmax en utilisant des portes d'oubli, en se basant sur les extrêmes du chemin plutôt que sur la somme des contributions.
           FPA inclut le Forgetting Transformer (FoX) comme cas particulier et permet la formation naturelle d'une pile de clés actives lorsqu'un champ scalaire et des niveaux suivent un même parcours appris.
           Des expérimentations synthétiques montrent que FPA converge vers les ensembles cibles, alors que les bases softmax et FoX échouent, et FPA atteint une récupération parfaite des clés à 8 fois la longueur d'entraînement avec une compression du cache clé-valeur à 25 %.

#282 | arXiv cs.CL | outils-dev
title_fr : Explorer séparément, adopter sélectivement : utilisation guidée par l'exécution d'outils sur de grandes bibliothèques d'outils
summary  : Une nouvelle approche nommée BRIA est présentée pour aider les agents basés sur des modèles de langage à sélectionner efficacement les outils pertinents parmi des bibliothèques composées de milliers d'outils.
           BRIA isole les investigations des candidats dans des branches séparées, permettant à chaque branche d'explorer et d'exécuter des outils indépendamment avant de choisir les résultats utiles pour la trajectoire principale.
           Les tests montrent que BRIA égale ou dépasse les meilleures bases de recherche existantes, avec une amélioration significative sur le benchmark MCP-Atlas.
```

### Deuxième collecte, lancée juste après

Même commande, enchaînée sans attente — 46 s au total, code de sortie 0. Le verrou consultatif, libéré à la fin de la première, ne bloque pas la seconde (pas de « collecte déjà en cours »).

```text
[source] Google DeepMind : 5 entrées (suivi, 7 derniers jours), 0 nouvelles
[source] Hugging Face Blog : 8 entrées (suivi, 7 derniers jours), 0 nouvelles
[source] arXiv cs.AI : 344 entrées (suivi, 7 derniers jours), 10 nouvelles
[source] arXiv cs.CL : 226 entrées (suivi, 7 derniers jours), 10 nouvelles
[source] Hacker News (IA, 100 points) : 20 entrées (suivi, 7 derniers jours), 0 nouvelles
[source] The Verge – IA : 10 entrées (suivi, 7 derniers jours), 0 nouvelles
[source] MIT Technology Review – IA : 4 entrées (suivi, 7 derniers jours), 0 nouvelles
[source] Simon Willison : 18 entrées (suivi, 7 derniers jours), 0 nouvelles
[source] ActuIA : 9 entrées (suivi, 7 derniers jours), 0 nouvelles
[source] Le Monde Informatique – IA : 4 entrées (suivi, 7 derniers jours), 0 nouvelles
[llm] 20 article(s) à résumer
…
=== Bilan de la collecte ===
Sources : 10 OK, 0 en erreur
Nouveaux articles : 20
Entrées ignorées (malformées) : 0
Résumés : 20
Échecs : 0
Durée : 44 s
```

Aucun doublon : hors arXiv, 0 nouvelle entrée (l'article The Verge de la première collecte n'est pas réinséré). Les 20 nouveaux articles arXiv sont des entrées encore inconnues de la fenêtre de 7 jours (344 et 226 entrées, plafond 10 par passage), pas des doublons. Base après passage : 171 articles (160 `summarized`, 11 `failed`), 171 `normalized_url` distinctes, 0 couple (source, titre) en double.

### `worker-cron`

`docker compose logs worker-cron | tail` (conteneur `running`, 0 redémarrage) :

```text
level=warning msg="process reaping disabled, not pid 1"
level=info msg="read crontab: /tmp/crontab"
level=info msg="crontab is valid"
Collecte planifiée : '0 6 * * *' (fuseau Europe/Paris)
level=info msg="reaping dead processes"
level=info msg="read crontab: /tmp/crontab"
```

Arrêt : `docker compose down` (volumes conservés).
