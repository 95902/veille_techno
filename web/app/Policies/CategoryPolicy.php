<?php

namespace App\Policies;

use App\Models\Category;
use App\Models\User;

/**
 * Only administrators manage categories in the back-office. Deleting a category
 * still used by articles is refused by the delete action and the model.
 */
class CategoryPolicy
{
    public function viewAny(User $user): bool
    {
        return $user->is_admin;
    }

    public function view(User $user, Category $category): bool
    {
        return $user->is_admin;
    }

    public function create(User $user): bool
    {
        return $user->is_admin;
    }

    public function update(User $user, Category $category): bool
    {
        return $user->is_admin;
    }

    public function delete(User $user, Category $category): bool
    {
        return $user->is_admin;
    }
}
