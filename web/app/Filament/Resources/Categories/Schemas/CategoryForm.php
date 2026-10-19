<?php

namespace App\Filament\Resources\Categories\Schemas;

use Filament\Forms\Components\Textarea;
use Filament\Forms\Components\TextInput;
use Filament\Schemas\Schema;

class CategoryForm
{
    public static function configure(Schema $schema): Schema
    {
        return $schema
            ->components([
                TextInput::make('name')
                    ->label('Nom')
                    ->required()
                    ->maxLength(255),
                TextInput::make('slug')
                    ->label('Identifiant')
                    ->helperText('Valeur choisie par le LLM : minuscules, chiffres et tirets.')
                    ->required()
                    ->maxLength(64)
                    ->regex('/^[a-z0-9]+(?:-[a-z0-9]+)*$/')
                    ->unique(ignoreRecord: true),
                Textarea::make('description')
                    ->label('Description pour le LLM')
                    ->helperText('Décrit ce que couvre la catégorie ; transmise au LLM pour guider le classement.')
                    ->rows(3)
                    ->maxLength(1000)
                    ->columnSpanFull(),
            ]);
    }
}
