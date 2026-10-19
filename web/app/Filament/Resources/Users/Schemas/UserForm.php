<?php

namespace App\Filament\Resources\Users\Schemas;

use App\Models\User;
use Filament\Forms\Components\TextInput;
use Filament\Forms\Components\Toggle;
use Filament\Schemas\Schema;
use Illuminate\Support\Facades\Auth;

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
                    ->unique(ignoreRecord: true),
                Toggle::make('is_admin')
                    ->label('Administrateur')
                    ->helperText(fn (?User $record): ?string => $record?->is(Auth::user())
                        ? 'Vous ne pouvez pas retirer votre propre rôle administrateur.'
                        : null)
                    ->disabled(fn (?User $record): bool => (bool) $record?->is(Auth::user())),
            ]);
    }
}
