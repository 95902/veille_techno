<?php

use App\Enums\ArticleStatus;
use App\Models\Article;
use App\Models\Category;
use App\Models\Source;
use App\Models\User;
use Inertia\Testing\AssertableInertia as Assert;

// SQLite: no full-text search here (tests/Pgsql covers ?q=).

beforeEach(function () {
    $this->source = Source::factory()->create(['name' => 'Le Blog IA']);
    $this->securite = Category::factory()->create(['name' => 'Sécurité', 'slug' => 'securite']);
    $this->modeles = Category::factory()->create(['name' => 'Modèles', 'slug' => 'modeles']);
});

/**
 * @param  array<string, mixed>  $attributes
 */
function readableArticle(array $attributes = []): Article
{
    return Article::factory()->create([
        'source_id' => test()->source->id,
        'status' => ArticleStatus::Summarized,
        'title' => 'Original title',
        'title_fr' => 'Titre français',
        'summary' => "Phrase un.\nPhrase deux.\nPhrase trois.",
        'content' => 'Texte extrait complet.',
        'category_id' => test()->modeles->id,
        ...$attributes,
    ]);
}

test('a guest is sent to the login page', function () {
    $article = readableArticle();

    $this->get(route('articles.index'))->assertRedirect(route('login'));
    $this->get(route('articles.show', $article))->assertRedirect(route('login'));
});

test('an unverified user is sent to the verification notice', function () {
    $this->actingAs(User::factory()->unverified()->create())
        ->get(route('articles.index'))
        ->assertRedirect(route('verification.notice'));
});

test('the list shows 20 summarized articles per page, most recent first', function () {
    foreach (range(1, 25) as $day) {
        readableArticle(['published_at' => now()->subDays($day), 'title_fr' => "Article {$day}"]);
    }
    readableArticle(['status' => ArticleStatus::Pending, 'published_at' => now()]);
    readableArticle(['status' => ArticleStatus::Failed, 'published_at' => now()]);

    $this->actingAs(User::factory()->create())
        ->get(route('articles.index'))
        ->assertOk()
        ->assertInertia(fn (Assert $page) => $page
            ->component('articles/Index')
            ->where('articles.total', 25)
            ->where('articles.last_page', 2)
            ->has('articles.data', 20)
            ->where('articles.data.0.title_fr', 'Article 1')
            ->where('articles.data.19.title_fr', 'Article 20')
            ->has('categories', 2)
            ->where('filters', ['q' => '', 'categorie' => '']));
});

test('an undated article falls back after the dated ones', function () {
    readableArticle(['published_at' => null, 'title_fr' => 'Sans date']);
    readableArticle(['published_at' => now()->subDays(10), 'title_fr' => 'Daté']);

    $this->actingAs(User::factory()->create())
        ->get(route('articles.index'))
        ->assertInertia(fn (Assert $page) => $page
            ->where('articles.data.0.title_fr', 'Daté')
            ->where('articles.data.1.title_fr', 'Sans date')
            ->whereNot('articles.data.1.published_at', null));
});

test('a card carries the displayed fields only', function () {
    readableArticle(['last_error' => 'boom', 'published_at' => now()->subDay()]);
    readableArticle(['title_fr' => null, 'title' => 'Only the original title', 'published_at' => now()->subDays(2)]);

    $this->actingAs(User::factory()->create())
        ->get(route('articles.index'))
        ->assertInertia(fn (Assert $page) => $page
            ->has('articles.data.0', fn (Assert $card) => $card
                ->hasAll(['id', 'title_fr', 'summary', 'published_at'])
                ->where('source', 'Le Blog IA')
                ->where('category', ['name' => 'Modèles', 'slug' => 'modeles'])
                ->missing('content')
                ->missing('last_error')
                ->missing('search_vector'))
            ->where('articles.data.1.title_fr', 'Only the original title'));
});

test('the category filter keeps that category and survives pagination', function () {
    foreach (range(1, 22) as $day) {
        readableArticle(['category_id' => $this->securite->id, 'published_at' => now()->subDays($day)]);
    }
    readableArticle(['category_id' => $this->modeles->id]);

    $user = User::factory()->create();

    $this->actingAs($user)
        ->get(route('articles.index', ['categorie' => 'securite']))
        ->assertInertia(fn (Assert $page) => $page
            ->where('articles.total', 22)
            ->where('filters.categorie', 'securite')
            ->where('articles.next_page_url', fn (string $url) => str_contains($url, 'categorie=securite')
                && str_contains($url, 'page=2')));

    $this->actingAs($user)
        ->get(route('articles.index', ['categorie' => 'securite', 'page' => 2]))
        ->assertInertia(fn (Assert $page) => $page
            ->has('articles.data', 2)
            ->where('articles.data.0.category.slug', 'securite')
            ->where('articles.data.1.category.slug', 'securite'));
});

test('an unknown category gives an empty list without error', function () {
    readableArticle();

    $this->actingAs(User::factory()->create())
        ->get(route('articles.index', ['categorie' => 'inconnue']))
        ->assertOk()
        ->assertInertia(fn (Assert $page) => $page
            ->where('articles.total', 0)
            ->has('articles.data', 0));
});

test('an overlong query is rejected by validation', function () {
    $this->actingAs(User::factory()->create())
        ->from(route('articles.index'))
        ->get(route('articles.index', ['q' => str_repeat('a', 201)]))
        ->assertSessionHasErrors('q');
});

test('the detail page shows a summarized article', function () {
    $article = readableArticle([
        'url' => 'https://example.com/article',
        'category_id' => $this->securite->id,
    ]);

    $this->actingAs(User::factory()->create())
        ->get(route('articles.show', $article))
        ->assertOk()
        ->assertInertia(fn (Assert $page) => $page
            ->component('articles/Show')
            ->has('article', fn (Assert $detail) => $detail
                ->where('id', $article->id)
                ->where('title_fr', 'Titre français')
                ->where('title', 'Original title')
                ->where('summary', "Phrase un.\nPhrase deux.\nPhrase trois.")
                ->where('source', 'Le Blog IA')
                ->where('category', ['name' => 'Sécurité', 'slug' => 'securite'])
                ->where('url', 'https://example.com/article')
                ->has('published_at')
                ->missing('content')
                ->missing('last_error')));
});

test('the detail of an article not summarized is not found', function (ArticleStatus $status) {
    $article = readableArticle(['status' => $status]);

    $this->actingAs(User::factory()->create())
        ->get(route('articles.show', $article))
        ->assertNotFound();
})->with([ArticleStatus::Pending, ArticleStatus::Failed]);
