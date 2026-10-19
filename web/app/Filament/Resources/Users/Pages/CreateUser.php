<?php

namespace App\Filament\Resources\Users\Pages;

use App\Filament\Resources\Users\Schemas\UserForm;
use App\Filament\Resources\Users\UserResource;
use App\Models\User;
use Filament\Resources\Pages\CreateRecord;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Support\Str;

class CreateUser extends CreateRecord
{
    protected static string $resource = UserResource::class;

    /**
     * Create the account with an unusable random password and a verified
     * e-mail: the admin vouches for the address, the user sets the password.
     *
     * @param  array<string, mixed>  $data
     */
    protected function handleRecordCreation(array $data): Model
    {
        $user = new User([
            'name' => $data['name'],
            'email' => UserForm::normalizeEmail($data['email']),
            'password' => Str::password(64),
        ]);
        $user->email_verified_at = now();
        $user->is_admin = (bool) ($data['is_admin'] ?? false);
        $user->save();

        return $user;
    }

    protected function afterCreate(): void
    {
        /** @var User $user */
        $user = $this->record;

        UserResource::sendPasswordSetupLink($user);
    }
}
