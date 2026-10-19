<?php

namespace App\Filament\Resources\Users\Pages;

use App\Filament\Resources\Users\Schemas\UserForm;
use App\Filament\Resources\Users\UserResource;
use App\Models\User;
use Filament\Actions\DeleteAction;
use Filament\Resources\Pages\EditRecord;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Support\Facades\Gate;
use Illuminate\Validation\ValidationException;

class EditUser extends EditRecord
{
    protected static string $resource = UserResource::class;

    protected function getHeaderActions(): array
    {
        return [
            DeleteAction::make(),
        ];
    }

    /**
     * Apply the fields explicitly: is_admin is not mass assignable, and a
     * demotion must pass the UserPolicy guard.
     *
     * @param  User  $record
     * @param  array<string, mixed>  $data
     */
    protected function handleRecordUpdate(Model $record, array $data): Model
    {
        $record->name = $data['name'];
        $record->email = UserForm::normalizeEmail($data['email']);

        if (array_key_exists('is_admin', $data)) {
            $isAdmin = (bool) $data['is_admin'];

            if ($record->is_admin && ! $isAdmin) {
                $response = Gate::inspect('demote', $record);

                if ($response->denied()) {
                    throw ValidationException::withMessages([
                        'data.is_admin' => $response->message(),
                    ]);
                }
            }

            $record->is_admin = $isAdmin;
        }

        $record->save();

        return $record;
    }
}
