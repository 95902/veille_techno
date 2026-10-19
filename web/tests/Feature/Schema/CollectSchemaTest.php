<?php

use App\Enums\ArticleStatus;
use App\Models\Article;
use App\Models\Category;
use App\Models\Source;
use Database\Seeders\CategorySeeder;
use Database\Seeders\DatabaseSeeder;
use Database\Seeders\SourceSeeder;
use Illuminate\Database\UniqueConstraintViolationException;
use Illuminate\Support\Facades\Schema;

test('the migrations create the sources, categories and articles tables', function () {
    expect(Schema::hasColumns('sources', ['name', 'feed_url', 'type', 'active', 'max_items_per_run']))->toBeTrue()
        ->and(Schema::hasColumns('categories', ['name', 'slug', 'description']))->toBeTrue()
        ->and(Schema::hasColumns('articles', [
            'source_id', 'url', 'normalized_url', 'title', 'title_fr', 'content', 'summary',
            'category_id', 'published_at', 'status', 'attempts', 'last_error',
        ]))->toBeTrue();
});

test('a new article defaults to pending with no attempt', function () {
    $article = Article::factory()->create()->fresh();

    expect($article->status)->toBe(ArticleStatus::Pending)
        ->and($article->attempts)->toBe(0);
});

test('the database rejects a duplicate normalized url', function () {
    Article::factory()->create(['normalized_url' => 'https://example.com/a']);

    expect(fn () => Article::factory()->create(['normalized_url' => 'https://example.com/a']))
        ->toThrow(UniqueConstraintViolationException::class);
});

test('seeding loads the categories and the active sources', function () {
    $this->seed(DatabaseSeeder::class);

    expect(Category::pluck('slug')->sort()->values()->all())
        ->toBe(['autre', 'business', 'modeles', 'outils-dev', 'recherche', 'reglementation', 'securite'])
        ->and(Category::whereNull('description')->count())->toBe(0)
        ->and(Source::where('active', true)->count())->toBe(count(SourceSeeder::SOURCES) - 1)
        ->and(Source::where('feed_url', 'https://openai.com/news/rss.xml')->value('active'))->toBeFalse()
        ->and(Source::count())->toBeGreaterThanOrEqual(10)
        ->and(Source::where('type', 'arxiv')->pluck('max_items_per_run')->all())->each->toBeLessThanOrEqual(10);
});

test('seeding twice creates no duplicate and keeps an admin deactivation', function () {
    $this->seed([CategorySeeder::class, SourceSeeder::class]);
    Source::where('name', 'Hugging Face Blog')->update(['active' => false]);

    $this->seed(DatabaseSeeder::class);
    $this->seed(DatabaseSeeder::class);

    expect(Category::count())->toBe(7)
        ->and(Source::count())->toBe(count(SourceSeeder::SOURCES))
        ->and(Source::where('active', false)->pluck('name')->sort()->values()->all())
        ->toBe(['Hugging Face Blog', 'OpenAI News']);
});

test('re-seeding rewrites the category descriptions', function () {
    Category::factory()->create(['slug' => 'autre', 'name' => 'Autre', 'description' => 'Ancienne description.']);

    $this->seed(CategorySeeder::class);

    expect(Category::where('slug', 'autre')->value('description'))
        ->toBe(CategorySeeder::CATEGORIES['autre']['description'])
        ->and(Category::where('slug', 'autre')->value('description'))->toContain('Dernier recours');
});
