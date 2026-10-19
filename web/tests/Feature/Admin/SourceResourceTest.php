<?php

use App\Enums\SourceType;
use App\Filament\Resources\Sources\Pages\CreateSource;
use App\Filament\Resources\Sources\Pages\EditSource;
use App\Filament\Resources\Sources\Pages\ListSources;
use App\Filament\Resources\Sources\SourceResource;
use App\Models\Article;
use App\Models\Source;
use App\Models\User;
use Filament\Actions\DeleteAction;
use Filament\Actions\Testing\TestAction;
use Livewire\Livewire;

beforeEach(function () {
    $this->actingAs(User::factory()->admin()->create());
});

test('a non-admin cannot reach the sources resource', function () {
    $source = Source::factory()->create();
    $this->actingAs(User::factory()->create());

    $this->get(SourceResource::getUrl('index'))->assertForbidden();
    $this->get(SourceResource::getUrl('create'))->assertForbidden();
    $this->get(SourceResource::getUrl('edit', ['record' => $source]))->assertForbidden();
});

test('an admin lists the sources', function () {
    $sources = Source::factory()->count(3)->create();

    $this->get(SourceResource::getUrl('index'))->assertOk();

    Livewire::test(ListSources::class)->assertCanSeeTableRecords($sources);
});

test('an admin creates an active source', function () {
    Livewire::test(CreateSource::class)
        ->fillForm([
            'name' => 'arXiv cs.LG',
            'feed_url' => 'https://export.arxiv.org/rss/cs.LG',
            'type' => 'arxiv',
            'max_items_per_run' => 5,
        ])
        ->call('create')
        ->assertHasNoFormErrors();

    $source = Source::where('feed_url', 'https://export.arxiv.org/rss/cs.LG')->sole();

    expect($source->name)->toBe('arXiv cs.LG')
        ->and($source->type)->toBe(SourceType::Arxiv)
        ->and($source->active)->toBeTrue()
        ->and($source->max_items_per_run)->toBe(5);

    Livewire::test(ListSources::class)->assertCanSeeTableRecords([$source]);
});

test('a duplicate feed url is rejected', function () {
    Source::factory()->create(['feed_url' => 'https://example.com/feed.xml']);

    Livewire::test(CreateSource::class)
        ->fillForm([
            'name' => 'Doublon',
            'feed_url' => 'https://example.com/feed.xml',
            'type' => 'rss',
            'max_items_per_run' => 20,
        ])
        ->call('create')
        ->assertHasFormErrors(['feed_url' => 'unique']);

    expect(Source::count())->toBe(1);
});

test('an admin edits a source', function () {
    $source = Source::factory()->create();

    Livewire::test(EditSource::class, ['record' => $source->getRouteKey()])
        ->fillForm(['name' => 'Nouveau nom', 'max_items_per_run' => 50])
        ->call('save')
        ->assertHasNoFormErrors();

    expect($source->refresh()->name)->toBe('Nouveau nom')
        ->and($source->max_items_per_run)->toBe(50);
});

test('an admin deactivates a source from the table toggle', function () {
    $source = Source::factory()->create();

    Livewire::test(ListSources::class)
        ->call('updateTableColumnState', 'active', (string) $source->getKey(), false);

    expect($source->refresh()->active)->toBeFalse();
});

test('an admin deletes a source without articles', function () {
    $source = Source::factory()->create();

    Livewire::test(ListSources::class)
        ->callAction(TestAction::make(DeleteAction::class)->table($source));

    $this->assertModelMissing($source);
});

test('deleting a source deletes its articles', function () {
    $article = Article::factory()->create();

    Livewire::test(EditSource::class, ['record' => $article->source->getRouteKey()])
        ->callAction(DeleteAction::class);

    $this->assertModelMissing($article->source);
    $this->assertModelMissing($article);
});
