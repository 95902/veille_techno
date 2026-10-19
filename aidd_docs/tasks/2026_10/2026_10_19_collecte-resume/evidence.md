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

Relancés le 2026-10-19 après les corrections de la revue r-69a1.

| Commande | Résultat |
| -------- | -------- |
| `pint --test` | PASS (103 fichiers) |
| `npm run lint` | 0 avertissement, 0 erreur |
| `uv run ruff check .` | All checks passed |
| `pest` | 112 tests, 509 assertions, PASS |
| `uv run pytest -m "not slow"` (sans base) | 106 passed, 9 skipped (`db`) |
| `uv run pytest -m db` (Postgres de Compose, `veille_worker`) | 9 passed, aucune ligne laissée en base |
| `uv run pytest` (vLLM démarré) | non relancé (vLLM arrêté) ; dernier passage : 63 passed dont 2 `slow` |
| `npm run build` | OK |
