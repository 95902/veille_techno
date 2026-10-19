# Contrat — comptes admin

## Objectif

Réserver le back-office Filament aux admins, permettre de créer le premier admin en ligne de commande, et laisser les admins gérer les comptes des collaborateurs depuis Filament.

## Périmètre

- Colonne booléenne `is_admin` sur `users` (défaut `false`), via une migration Laravel.
- `User` implémente `FilamentUser` : `canAccessPanel` renvoie `true` seulement pour un admin.
- Commande `php artisan veille:make-admin` : demande nom, e-mail et mot de passe au clavier (mot de passe masqué et confirmé), crée l'admin avec e-mail vérifié, ou promeut un compte existant de même e-mail.
- Ressource Filament `Users` : liste, création, édition (nom, e-mail, `is_admin`), suppression.
  - À la création : pas de champ mot de passe ; mot de passe aléatoire inutilisable, e-mail marqué vérifié, envoi du lien Laravel de définition du mot de passe (notification de réinitialisation). Avec `MAIL_MAILER=log`, le lien est écrit dans le log.
  - Garde-fous : un admin ne peut pas se supprimer ni se retirer le rôle admin ; le dernier admin ne peut être ni supprimé ni rétrogradé.

## Hors périmètre

Pages de lecture, configuration SMTP réelle, statut « désactivé », rôles supplémentaires.

## Critères d'acceptation

1. Un utilisateur non admin connecté reçoit 403 sur `/admin` ; un admin y accède.
2. `veille:make-admin` crée un admin capable de se connecter à `/admin` ; relancée avec un e-mail existant, elle le promeut sans dupliquer le compte.
3. Un admin crée un collaborateur depuis Filament sans saisir de mot de passe ; un lien de définition du mot de passe est émis (visible dans le log) ; après l'avoir suivi, le collaborateur se connecte sans étape de vérification d'e-mail.
4. Les garde-fous refusent : auto-suppression, auto-rétrogradation, suppression ou rétrogradation du dernier admin.
5. L'édition et la suppression d'un collaborateur fonctionnent.
6. Tests Pest couvrant les critères 1 à 5 ; gates de `aidd_docs/memory/coding-assertions.md` verts.

## Décisions

- `is_admin` booléen : deux profils pour ~10 utilisateurs, pas de paquet de permissions.
- Premier admin par commande interactive : aucun mot de passe dans un fichier ni dans l'historique du shell.
- Lien de définition du mot de passe plutôt qu'un mot de passe transmis par l'admin ; e-mail vérifié d'office car l'admin se porte garant de l'adresse.
