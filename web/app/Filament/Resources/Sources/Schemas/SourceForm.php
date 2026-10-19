<?php

namespace App\Filament\Resources\Sources\Schemas;

use App\Enums\SourceType;
use Filament\Forms\Components\Select;
use Filament\Forms\Components\TextInput;
use Filament\Forms\Components\Toggle;
use Filament\Schemas\Schema;

class SourceForm
{
    public static function configure(Schema $schema): Schema
    {
        return $schema
            ->components([
                TextInput::make('name')
                    ->label('Nom')
                    ->required()
                    ->maxLength(255),
                TextInput::make('feed_url')
                    ->label('URL du flux')
                    ->url()
                    ->required()
                    ->maxLength(2048)
                    ->unique(ignoreRecord: true),
                Select::make('type')
                    ->label('Type')
                    ->options(SourceType::options())
                    ->default(SourceType::Rss->value)
                    ->helperText('arXiv : le résumé du flux est utilisé, sans extraction de la page.')
                    ->required(),
                TextInput::make('max_items_per_run')
                    ->label('Articles max. par collecte')
                    ->integer()
                    ->minValue(1)
                    ->maxValue(200)
                    ->default(20)
                    ->required(),
                Toggle::make('active')
                    ->label('Active')
                    ->default(true),
            ]);
    }
}
