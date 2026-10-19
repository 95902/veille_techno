<?php

use App\Enums\ArticleStatus;
use App\Models\Article;
use App\Models\Category;
use App\Models\User;
use Inertia\Testing\AssertableInertia as Assert;

// ?q= through ArticleController on PostgreSQL: validation, trimming, query string kept.

/**
 * @param  array<string, mixed>  $attributes
 */
function searchableArticle(array $attributes): Article
{
    return Article::factory()->create([
        'status' => ArticleStatus::Summarized,
        'title' => 'Original title',
        'title_fr' => 'Titre sans rapport',
        'summary' => "Première phrase.\nDeuxième phrase.\nTroisième phrase.",
        ...$attributes,
    ]);
}

test('a search without accents finds an accented article through the page', function () {
    $hit = searchableArticle(['title_fr' => 'La sécurité des agents']);
    searchableArticle(['title_fr' => 'Un nouveau modèle de vision']);

    $this->actingAs(User::factory()->create())
        ->get(route('articles.index', ['q' => 'securite']))
        ->assertOk()
        ->assertInertia(fn (Assert $page) => $page
            ->component('articles/Index')
            ->where('articles.total', 1)
            ->where('articles.data.0.id', $hit->id)
            ->where('filters.q', 'securite'));
});

test('the query is trimmed', function () {
    $hit = searchableArticle(['title_fr' => 'Sécurité des modèles']);

    $this->actingAs(User::factory()->create())
        ->get(route('articles.index', ['q' => '   sécurité  ']))
        ->assertOk()
        ->assertInertia(fn (Assert $page) => $page
            ->where('articles.total', 1)
            ->where('articles.data.0.id', $hit->id)
            ->where('filters.q', 'sécurité'));
});

test('a query longer than 200 characters is rejected', function () {
    $this->actingAs(User::factory()->create())
        ->from(route('articles.index'))
        ->get(route('articles.index', ['q' => str_repeat('a', 201)]))
        ->assertSessionHasErrors('q');

    $this->actingAs(User::factory()->create())
        ->get(route('articles.index', ['q' => str_repeat('a', 200)]))
        ->assertOk();
});

test('the query and the category survive pagination', function () {
    $securite = Category::factory()->create(['slug' => 'securite']);
    $modeles = Category::factory()->create(['slug' => 'modeles']);

    foreach (range(1, 22) as $day) {
        searchableArticle([
            'title_fr' => "Sécurité des agents {$day}",
            'category_id' => $securite->id,
            'published_at' => now()->subDays($day),
        ]);
    }
    searchableArticle(['title_fr' => 'Sécurité des modèles', 'category_id' => $modeles->id]);

    $user = User::factory()->create();

    $this->actingAs($user)
        ->get(route('articles.index', ['q' => 'sécurité', 'categorie' => 'securite']))
        ->assertOk()
        ->assertInertia(fn (Assert $page) => $page
            ->where('articles.total', 22)
            ->has('articles.data', 20)
            ->where('filters', ['q' => 'sécurité', 'categorie' => 'securite'])
            ->where('articles.next_page_url', function (string $url) {
                parse_str((string) parse_url($url, PHP_URL_QUERY), $query);

                return $query === ['q' => 'sécurité', 'categorie' => 'securite', 'page' => '2'];
            }));

    $this->actingAs($user)
        ->get(route('articles.index', ['q' => 'sécurité', 'categorie' => 'securite', 'page' => 2]))
        ->assertInertia(fn (Assert $page) => $page
            ->has('articles.data', 2)
            ->where('articles.data.0.category.slug', 'securite')
            ->where('articles.next_page_url', null));
});
