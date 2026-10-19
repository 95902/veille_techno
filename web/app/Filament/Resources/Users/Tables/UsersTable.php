<?php

namespace App\Filament\Resources\Users\Tables;

use App\Filament\Resources\Users\UserResource;
use App\Models\User;
use Filament\Actions\Action;
use Filament\Actions\DeleteAction;
use Filament\Actions\EditAction;
use Filament\Support\Icons\Heroicon;
use Filament\Tables\Columns\IconColumn;
use Filament\Tables\Columns\TextColumn;
use Filament\Tables\Table;

class UsersTable
{
    public static function configure(Table $table): Table
    {
        return $table
            ->columns([
                TextColumn::make('name')
                    ->label('Nom')
                    ->searchable()
                    ->sortable(),
                TextColumn::make('email')
                    ->label('Adresse e-mail')
                    ->searchable()
                    ->sortable(),
                IconColumn::make('is_admin')
                    ->label('Administrateur')
                    ->boolean(),
                TextColumn::make('created_at')
                    ->label('Créé le')
                    ->dateTime('d/m/Y H:i')
                    ->sortable(),
            ])
            ->defaultSort('name')
            ->recordActions([
                EditAction::make()
                    ->label('Modifier'),
                Action::make('sendPasswordLink')
                    ->label('Renvoyer le lien')
                    ->icon(Heroicon::OutlinedEnvelope)
                    ->requiresConfirmation()
                    ->modalHeading('Renvoyer le lien de définition du mot de passe')
                    ->modalSubmitActionLabel('Envoyer')
                    ->action(fn (User $record) => UserResource::sendPasswordSetupLink($record)),
                DeleteAction::make()
                    ->label('Supprimer')
                    ->modalHeading('Supprimer l\'utilisateur'),
            ]);
    }
}
