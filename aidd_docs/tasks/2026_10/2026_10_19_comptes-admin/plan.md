---
objective: "Seuls les admins accèdent à /admin ; le premier admin se crée par commande ; les admins gèrent les comptes collaborateurs dans Filament avec un lien de définition du mot de passe."
status: reviewed
---

# Plan: Comptes admin

## Overview

| Field      | Value                                                        |
| ---------- | ------------------------------------------------------------ |
| **Goal**   | Rôle admin, accès Filament restreint, commande premier admin, ressource Users |
| **Source** | `aidd_docs/tasks/2026_10/2026_10_19_comptes-admin/contract.md` |

## Phases

| #   | Phase                                        | File                         |
| --- | -------------------------------------------- | ---------------------------- |
| 1   | Rôle admin, accès au panneau, premier admin  | [`phase-1.md`](./phase-1.md) |
| 2   | Ressource Filament Users et garde-fous       | [`phase-2.md`](./phase-2.md) |

## Resources

| Source | Verified |
| ------ | -------- |
| `web/config/fortify.php` (repo) | `resetPasswords` actif : routes `password.reset` et page `ResetPassword.vue` disponibles pour le lien d'invitation |
| `web/config/auth.php` (repo) | jeton de réinitialisation valable 60 min (`passwords.users.expire`) |
| `web/app/Providers/Filament/AdminPanelProvider.php` (repo) | panneau `/admin` avec `->login()`, découverte des ressources dans `app/Filament/Resources` |
| `web/app/Models/User.php` (repo) | `MustVerifyEmail` : un compte non vérifié serait bloqué par le middleware `verified` |

## Decisions

| Decision | Why |
| -------- | --- |
| Action « Renvoyer le lien » sur chaque compte de la liste | le jeton expire en 60 min ; renvoyer le lien évite d'allonger la durée pour toutes les réinitialisations |
| Garde-fous dans une règle métier unique (policy `UserPolicy`) appliquée par Filament | une seule source de vérité, testable sans l'interface |

## Amendement 2026-10-19

Décidé à la pause sur le résultat :

- La suppression de compte de `/settings/profile` passe par `UserPolicy::deleteOwnAccount` : un collaborateur peut supprimer son compte, un admin non (403 avant déconnexion, section masquée).
- Locale par défaut `fr` dans `web/config/app.php` pour traduire les textes de Filament.
