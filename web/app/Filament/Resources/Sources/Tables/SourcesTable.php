<?php

namespace App\Filament\Resources\Sources\Tables;

use App\Enums\SourceType;
use Filament\Actions\DeleteAction;
use Filament\Actions\EditAction;
use Filament\Tables\Columns\TextColumn;
use Filament\Tables\Columns\ToggleColumn;
use Filament\Tables\Table;

class SourcesTable
{
    public static function configure(Table $table): Table
    {
        return $table
            ->columns([
                TextColumn::make('name')
                    ->label('Nom')
                    ->searchable()
                    ->sortable(),
                TextColumn::make('feed_url')
                    ->label('URL du flux')
                    ->limit(60)
                    ->searchable(),
                TextColumn::make('type')
                    ->label('Type')
                    ->formatStateUsing(fn (SourceType $state): string => $state->label()),
                TextColumn::make('max_items_per_run')
                    ->label('Max. / collecte')
                    ->numeric(),
                TextColumn::make('articles_count')
                    ->label('Articles')
                    ->counts('articles')
                    ->sortable(),
                ToggleColumn::make('active')
                    ->label('Active'),
            ])
            ->defaultSort('name')
            ->recordActions([
                EditAction::make(),
                DeleteAction::make()
                    ->modalDescription('Les articles collectés depuis cette source seront supprimés avec elle.'),
            ]);
    }
}
