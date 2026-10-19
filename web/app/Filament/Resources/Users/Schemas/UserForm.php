<?php

namespace App\Filament\Resources\Users\Schemas;

use App\Models\User;
use Filament\Forms\Components\TextInput;
use Filament\Forms\Components\Toggle;
use Filament\Schemas\Schema;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Str;

class UserForm
{
    public static function configure(Schema $schema): Schema
    {
        return $schema
            ->components([
                TextInput::make('name')
                    ->label('Nom')
                    ->required()
                    ->maxLength(255),
                TextInput::make('email')
                    ->label('Adresse e-mail')
                    ->email()
                    ->required()
                    ->maxLength(255)
                    // Fortify lowercases e-mails at login and password reset:
                    // validate and store them lowercase so they always match.
                    ->mutateStateForValidationUsing(fn (?string $state): ?string => self::normalizeEmail($state))
                    ->dehydrateStateUsing(fn (?string $state): ?string => self::normalizeEmail($state))
                    ->unique(ignoreRecord: true),
                Toggle::make('is_admin')
                    ->label('Administrateur')
                    ->helperText(fn (?User $record): ?string => $record?->is(Auth::user())
                        ? 'Vous ne pouvez pas retirer votre propre rôle administrateur.'
                        : null)
                    ->disabled(fn (?User $record): bool => (bool) $record?->is(Auth::user())),
            ]);
    }

    /**
     * Lowercase and trim an e-mail address, as Fortify does at authentication time.
     */
    public static function normalizeEmail(?string $email): ?string
    {
        return $email === null ? null : Str::lower(trim($email));
    }
}
