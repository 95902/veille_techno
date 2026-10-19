<?php

namespace App\Policies;

use App\Models\Source;
use App\Models\User;

/**
 * Only administrators manage feed sources in the back-office.
 */
class SourcePolicy
{
    public function viewAny(User $user): bool
    {
        return $user->is_admin;
    }

    public function view(User $user, Source $source): bool
    {
        return $user->is_admin;
    }

    public function create(User $user): bool
    {
        return $user->is_admin;
    }

    public function update(User $user, Source $source): bool
    {
        return $user->is_admin;
    }

    public function delete(User $user, Source $source): bool
    {
        return $user->is_admin;
    }
}
