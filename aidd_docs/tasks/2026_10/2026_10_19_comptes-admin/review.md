# Review: comptes admin

- Rounds: 2
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

## Round 2 · r-cf82

- Date: 2026-10-19
- By: 95902
- Diff: `main...7ef786b`
- Axes: code, functional, relevancy
- Verdict: approve
- Score: 8/8 met, 0 unmet, 0 unverified at runtime, 0 out of the diff

### Criteria

- [x] P1.1 Un nouveau compte n'est pas admin ; `is_admin` non affectable en masse — `web/app/Models/User.php:35` (`#[Fillable]` sans `is_admin`), `:46-49` défaut `false`, `PanelAccessTest.php`
- [x] P1.2 Non-admin 403 sur `/admin`, admin 200 — `web/app/Models/User.php:103-106`, `PanelAccessTest.php`
- [x] P1.3 La commande crée un admin vérifié qui se connecte, promeut sans dupliquer (y compris en casse mixte, et pose `email_verified_at` si absent), confirmation différente n'écrit rien — `web/app/Console/Commands/MakeAdmin.php:25-37`, `MakeAdminCommandTest.php` (8 tests)
- [x] P1.4 Tests dans le gate Pest — run du relecteur dans le conteneur `app` : Pest 90 passed (412 assertions)
- [x] P2.1 Les quatre cas interdits refusés, y compris hors interface — `web/app/Policies/UserPolicy.php` (messages en constantes `:14-16`), filet modèle `User.php:72-89`, `UserGuardsTest.php`
- [x] P2.2 Liste, création, édition, suppression ; aucun champ mot de passe — `UserResourceTest.php` ; libellés Filament par défaut (`EditUser.php:21`, `UsersTable.php:39,47`)
- [x] P2.3 Lien émis à la création (e-mail d'invitation français dédié, contrat amendé), définition du mot de passe puis connexion sans vérification, y compris pour une adresse saisie en casse mixte ; « Renvoyer le lien » émet un nouveau lien et le throttle du broker s'applique — `UserResource.php:58-81`, `web/app/Notifications/AccountInvitation.php`, `UserResourceTest.php` (flux casse mixte via le lien de l'e-mail, throttle en français, forgot-password inchangé)
- [x] P2.4 pint, lint front, Pest, build verts — run du relecteur dans le conteneur `app` : pint PASS 72 fichiers, `npm run lint` 0 erreur, Pest 90 passed, `npm run build` exit 0

### Findings

- `web/app/Providers/Filament/AdminPanelProvider.php:30` : `->login()` utilise la page Login de Filament, qui passe l'e-mail tel que saisi à `attemptWhen` (`vendor/filament/filament/src/Auth/Pages/Login.php:440-446`, aucune mise en minuscules) ; les e-mails étant désormais stockés en minuscules, un admin qui tape `Prenom.Nom@innosys.fr` sur `/admin/login` est refusé sur PostgreSQL alors que `/login` (Fortify) l'accepte → page `App\Filament\Pages\Auth\Login` étendant celle de Filament avec `getCredentialsFromFormData` en `Str::lower`, branchée par `->login(Login::class)`, plus un test en casse mixte — 🟢 minor, fit
- `web/app/Filament/Resources/Users/Schemas/UserForm.php:44-47` : la normalisation `Str::lower(trim())` vit à trois endroits (`UserForm::normalizeEmail`, `MakeAdmin.php:25`, `ProfileUpdateRequest.php:21`) et est appliquée deux fois côté Filament (`dehydrateStateUsing` `UserForm.php:30` puis `CreateUser.php:26` / `EditUser.php:35`) ; une classe de schéma Filament est un foyer étrange pour une règle de domaine → un mutateur `email` sur `User` (couvre toute écriture), en gardant seulement la mutation pour la validation `unique` côté formulaires — 🟢 minor, rot
- `web/lang/fr.json:2-3` : avec la locale `fr`, l'e-mail standard « mot de passe oublié » mêle désormais le corps anglais de `ResetPassword` (« Hello! », « Reset Password », « Regards, ») et les deux lignes de gabarit traduites → traduire aussi les lignes de `ResetPassword` dans `fr.json`, ou accepter (accepté par l'orchestrateur) — 🟢 minor, fit
