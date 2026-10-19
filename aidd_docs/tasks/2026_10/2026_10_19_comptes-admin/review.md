# Review: comptes admin

- Rounds: 1
- Started: 2026-10-19

## Round 1 · r-8c40

- Date: 2026-10-19
- By: 95902
- Diff: `main...feat/comptes-admin`
- Axes: code, functional, relevancy
- Verdict: changes-requested
- Score: 8/8 met, 0 unmet, 0 unverified at runtime, 0 out of the diff

### Criteria

- [x] P1.1 Un nouveau compte n'est pas admin ; `is_admin` non affectable en masse — `web/app/Models/User.php:34` (`#[Fillable]` sans `is_admin`), `web/tests/Feature/Admin/PanelAccessTest.php:5-24`
- [x] P1.2 Non-admin 403 sur `/admin`, admin 200 — `web/app/Models/User.php:100-103`, `PanelAccessTest.php:30-40`
- [x] P1.3 La commande crée un admin vérifié qui se connecte, promeut sans dupliquer, confirmation différente n'écrit rien — `web/app/Console/Commands/MakeAdmin.php`, `MakeAdminCommandTest.php` (4 tests)
- [x] P1.4 Tests dans le gate Pest — run du relecteur : Pest 79 passed (328 assertions)
- [x] P2.1 Les quatre cas interdits refusés, y compris hors interface — `web/app/Policies/UserPolicy.php:35-86`, invariant modèle `User.php:68-84`, `UserGuardsTest.php` (policy, modèle, Filament)
- [x] P2.2 Liste, création, édition, suppression ; aucun champ mot de passe — `UserResourceTest.php` (`assertFormFieldDoesNotExist('password')`, delete table + page)
- [x] P2.3 Lien émis à la création, définition du mot de passe puis connexion sans vérification, « Renvoyer le lien » — `UserResource.php:62-80`, `UserResourceTest.php` (flux reset + login + dashboard `verified`) ; limite : seulement pour une adresse saisie en minuscules, voir finding 1
- [x] P2.4 pint, lint front, Pest, build verts — run du relecteur : pint PASS 70 fichiers, `npm run lint` exit 0, `npm run build` OK

### Findings

- `web/app/Filament/Resources/Users/Schemas/UserForm.php:21` : l'e-mail est stocké tel que saisi (Filament create/edit, et `MakeAdmin.php:29,64`) alors que Fortify (`config/fortify.php:63` `lowercase_usernames => true`) met en minuscules l'e-mail au login (`CanonicalizeUsername`), à la demande de lien et à la soumission du nouveau mot de passe (`vendor/laravel/fortify/src/Http/Controllers/NewPasswordController.php:58`). Sur PostgreSQL (`=` sensible à la casse), un collaborateur créé avec `Prenom.Nom@innosys.fr` reçoit le lien mais ne peut ni définir son mot de passe (utilisateur introuvable) ni se connecter : le critère 3 échoue sur une saisie courante → normaliser en minuscules à l'écriture (`->dehydrateStateUsing(fn ($s) => Str::lower($s))` ou dans `handleRecordCreation`/`handleRecordUpdate`, et `Str::lower($email)` dans `MakeAdmin` avant recherche et création), plus un test avec une adresse en casse mixte — 🟡 major, backend
- `web/app/Filament/Resources/Users/UserResource.php:64` : l'invitation réutilise la notification `ResetPassword` standard (texte anglais « you are receiving this email because we received a password reset request », lien valable 60 min) ; un nouveau collaborateur reçoit un e-mail de réinitialisation qu'il n'a pas demandé → accepté par le contrat (« notification de réinitialisation ») ; à terme, une notification d'invitation dédiée ou au minimum le texte traduit — 🟢 minor, fit
- `web/app/Filament/Resources/Users/UserResource.php:78` : `__($status)` sans fichier `lang/fr` rend le message de throttle en anglais (« Please wait before retrying. ») dans une interface désormais française ; branche throttle non testée → ajouter `lang/fr/passwords.php` (ou message en dur) et un test « renvoyer le lien » deux fois de suite — 🟢 minor, error-handling
- `web/app/Models/User.php:73,81` : les messages « Le dernier administrateur ne peut pas être … » sont dupliqués avec `UserPolicy.php:45,82` ; le plan annonce la policy comme source unique → factoriser les messages (constantes ou méthode) ou documenter l'invariant modèle comme filet — 🟢 minor, rot
- `web/app/Console/Commands/MakeAdmin.php:32` : la promotion d'un compte existant non vérifié ne pose pas `email_verified_at` ; l'admin accède à `/admin` mais reste bloqué sur le front `verified` → poser `email_verified_at ??= now()` à la promotion, cohérent avec la création — 🟢 minor, backend
- `web/app/Filament/Resources/Users/UserResource.php:43-48` : `getRelations()` vide avec `//` issu du scaffold ; `UserPolicy::restore/forceDelete` (`:88-96`) sans soft delete → supprimer le scaffold inutile — 🟢 minor, code-health
- `web/app/Filament/Resources/Users/Pages/EditUser.php:21-22` et `Tables/UsersTable.php` : libellés « Supprimer », « Modifier » forcés en dur alors que la locale `fr` traduit déjà les actions Filament → retirer les libellés redondants — 🟢 minor, rot
- `aidd_docs/memory/testing.md:3` : « aucun test n'existe encore » est faux (79 tests) ; la mémoire n'est pas mise à jour par ce diff → corriger la ligne — 🟢 minor, conform
