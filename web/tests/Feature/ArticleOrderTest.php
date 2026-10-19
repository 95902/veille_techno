<?php

use App\Enums\ArticleStatus;
use App\Models\Article;
use App\Models\User;
use Inertia\Testing\AssertableInertia as Assert;

// Contract: publication date first, falling back to the collection date for undated articles.

/**
 * @param  array<string, mixed>  $attributes
 */
function orderedArticle(string $title, array $attributes): Article
{
    return Article::factory()->create([
        'status' => ArticleStatus::Summarized,
        'title' => $title,
        'title_fr' => $title,
        'summary' => "Phrase un.\nPhrase deux.\nPhrase trois.",
        ...$attributes,
    ]);
}

test('an undated article sorts by its collection date among the dated ones', function () {
    orderedArticle('Ancien', ['published_at' => now()->subDays(10), 'created_at' => now()->subDays(10)]);
    orderedArticle('Sans date récent', ['published_at' => null, 'created_at' => now()->subHour()]);
    orderedArticle('Récent', ['published_at' => now()->subDays(2), 'created_at' => now()->subDays(2)]);
    orderedArticle('Sans date ancien', ['published_at' => null, 'created_at' => now()->subDays(30)]);

    $this->actingAs(User::factory()->create())
        ->get(route('articles.index'))
        ->assertInertia(fn (Assert $page) => $page
            ->where('articles.data.0.title_fr', 'Sans date récent')
            ->where('articles.data.1.title_fr', 'Récent')
            ->where('articles.data.2.title_fr', 'Ancien')
            ->where('articles.data.3.title_fr', 'Sans date ancien'));
});

test('the publication date wins over a later collection date', function () {
    orderedArticle('Publié il y a longtemps', ['published_at' => now()->subDays(20), 'created_at' => now()]);
    orderedArticle('Publié hier', ['published_at' => now()->subDay(), 'created_at' => now()->subDays(3)]);

    $this->actingAs(User::factory()->create())
        ->get(route('articles.index'))
        ->assertInertia(fn (Assert $page) => $page
            ->where('articles.data.0.title_fr', 'Publié hier')
            ->where('articles.data.1.title_fr', 'Publié il y a longtemps'));
});

test('equal dates are ordered by id, newest first', function () {
    $date = now()->subDay();
    $first = orderedArticle('Premier', ['published_at' => $date]);
    $second = orderedArticle('Second', ['published_at' => $date]);

    $this->actingAs(User::factory()->create())
        ->get(route('articles.index'))
        ->assertInertia(fn (Assert $page) => $page
            ->where('articles.data.0.id', $second->id)
            ->where('articles.data.1.id', $first->id));
});
