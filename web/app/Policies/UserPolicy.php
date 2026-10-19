<?php

namespace App\Policies;

use App\Models\User;
use Illuminate\Auth\Access\Response;

/**
 * Single source of truth for account management rules: only admins manage
 * accounts, nobody deletes or demotes themselves, and the last admin is kept.
 */
class UserPolicy
{
    public const LAST_ADMIN_DELETE_MESSAGE = 'Le dernier administrateur ne peut pas être supprimé.';

    public const LAST_ADMIN_DEMOTE_MESSAGE = 'Le dernier administrateur ne peut pas être rétrogradé.';

    public function viewAny(User $user): bool
    {
        return $user->is_admin;
    }

    public function view(User $user, User $model): bool
    {
        return $user->is_admin;
    }

    public function create(User $user): bool
    {
        return $user->is_admin;
    }

    public function update(User $user, User $model): bool
    {
        return $user->is_admin;
    }

    public function delete(User $user, User $model): Response
    {
        if (! $user->is_admin) {
            return Response::deny('Action réservée aux administrateurs.');
        }

        if ($user->is($model)) {
            return Response::deny('Vous ne pouvez pas supprimer votre propre compte.');
        }

        if ($model->isLastAdmin()) {
            return Response::deny(self::LAST_ADMIN_DELETE_MESSAGE);
        }

        return Response::allow();
    }

    /**
     * Determine whether the user can delete their own account from the profile settings.
     * Collaborators may; admins may not, whether or not they are the last one.
     */
    public function deleteOwnAccount(User $user, User $model): Response
    {
        if (! $user->is($model)) {
            return Response::deny('Action réservée au titulaire du compte.');
        }

        if ($user->is_admin) {
            return Response::deny('Vous ne pouvez pas supprimer votre propre compte.');
        }

        return Response::allow();
    }

    /**
     * Determine whether the user can remove the admin role from the model.
     */
    public function demote(User $user, User $model): Response
    {
        if (! $user->is_admin) {
            return Response::deny('Action réservée aux administrateurs.');
        }

        if ($user->is($model)) {
            return Response::deny('Vous ne pouvez pas retirer votre propre rôle administrateur.');
        }

        if ($model->isLastAdmin()) {
            return Response::deny(self::LAST_ADMIN_DEMOTE_MESSAGE);
        }

        return Response::allow();
    }
}
