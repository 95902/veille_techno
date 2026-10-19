# Project Brief

## What it is

- Site interne de veille IA pour les collaborateurs INNOSYS (~10 personnes : dev, chefs de projet, commerciaux, direction).
- Collecte l'actualité IA, la résume en français et la classe par thème.

## Why it exists

- Permettre à chacun de rester à jour sur l'IA en 5 minutes par semaine, sans parcourir des dizaines de sources.
- Tout tourne en interne, LLM compris : 0 € de coût externe, aucune donnée envoyée à un tiers.

## Domain language

| Term | Meaning |
| ---- | ------- |
| Source | Flux RSS/Atom configuré par l'admin (blog de labo IA, arXiv, Hacker News, presse tech) |
| Article | Entrée collectée depuis une source, avec son texte extrait |
| Résumé | Synthèse en français d'un article, produite une seule fois par le LLM puis stockée |
| Catégorie | Thème attribué par le LLM (modèles, outils dev, réglementation, sécurité…), géré dans le back-office |
| Collecte | Passage quotidien du worker : lecture des sources, extraction, résumé, catégorisation |
| Digest | Sélection hebdomadaire envoyée par e-mail et sur Slack |

## Key features

- Collecte quotidienne de 30 à 50 sources RSS configurables.
- Résumé en français et catégorisation automatiques par LLM local.
- Liste filtrable par catégorie, recherche plein texte, page de détail.
- Digest hebdomadaire par e-mail et webhook Slack.
- Back-office d'administration des sources, catégories et comptes.
