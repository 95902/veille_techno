<?php

use App\Enums\ArticleStatus;
use App\Models\Article;
use App\Models\Category;
use Illuminate\Support\Facades\DB;

/**
 * @param  array<string, mixed>  $attributes
 */
function summarizedArticle(array $attributes): Article
{
    return Article::factory()->create([
        'status' => ArticleStatus::Summarized,
        'title' => 'Original title',
        'title_fr' => 'Titre sans rapport',
        'summary' => "Première phrase.\nDeuxième phrase.\nTroisième phrase.",
        ...$attributes,
    ]);
}

/**
 * @return list<int>
 */
function searchIds(?string $terms, ?string $category = null): array
{
    return Article::summarized()->inCategory($category)->search($terms)->pluck('id')->all();
}

test('the database computes the search vector from the worker columns', function () {
    $article = summarizedArticle(['title_fr' => 'Sécurité des agents']);

    $vector = DB::selectOne('SELECT search_vector::text AS v FROM articles WHERE id = ?', [$article->id])->v;

    expect($vector)->toContain("'securit':1A")
        ->and($vector)->toContain(':4B')
        ->and($vector)->toContain("'original'");
});

test('a search without accents finds an accented article', function () {
    $accented = summarizedArticle(['title_fr' => 'La sécurité des modèles de langage']);
    summarizedArticle(['title_fr' => 'Un nouveau modèle de vision']);

    expect(searchIds('securite'))->toBe([$accented->id]);
});

test('an accented search finds an article written without accents', function () {
    $plain = summarizedArticle(['summary' => "Une faille de securite.\nPhrase deux.\nPhrase trois."]);
    summarizedArticle(['summary' => "Rien à voir.\nPhrase deux.\nPhrase trois."]);

    expect(searchIds('sécurité'))->toBe([$plain->id]);
});

test('the original title is searched too', function () {
    $article = summarizedArticle(['title' => 'Security of LLM agents']);

    expect(searchIds('security'))->toBe([$article->id]);
});

test('a match in the French title ranks before a match in the summary', function () {
    $inTitle = summarizedArticle(['title_fr' => 'Sécurité des agents', 'published_at' => now()->subDays(5)]);
    $inSummary = summarizedArticle([
        'summary' => "Les agents progressent.\nLa sécurité reste un sujet.\nFin.",
        'published_at' => now()->subDay(),
    ]);

    expect(searchIds('sécurité'))->toBe([$inTitle->id, $inSummary->id]);
});

test('the search combines with the category filter and keeps summarized articles only', function () {
    $securite = Category::factory()->create(['slug' => 'securite']);
    $modeles = Category::factory()->create(['slug' => 'modeles']);
    $kept = summarizedArticle(['title_fr' => 'Sécurité des agents', 'category_id' => $securite->id]);
    summarizedArticle(['title_fr' => 'Sécurité des modèles', 'category_id' => $modeles->id]);
    Article::factory()->create([
        'status' => ArticleStatus::Pending,
        'title' => 'Sécurité en attente',
        'category_id' => $securite->id,
    ]);

    expect(searchIds('securite', 'securite'))->toBe([$kept->id]);
});

test('free-form input never raises an SQL error', function (string $terms) {
    summarizedArticle(['title_fr' => 'Sécurité des agents']);

    expect(searchIds($terms))->toBeArray();
})->with([
    'unbalanced quote' => '"sécurité',
    'dangling operator' => 'sécurité OR',
    'lone minus' => '-',
    'punctuation' => '!!! & | :*',
    'stop words only' => 'le la les',
]);

test('without a query the most recent articles come first, undated ones by collection date', function () {
    $old = summarizedArticle(['published_at' => now()->subDays(3)]);
    $undatedRecent = summarizedArticle(['published_at' => null, 'created_at' => now()->subMinutes(30)]);
    $undatedOld = summarizedArticle(['published_at' => null, 'created_at' => now()->subDays(10)]);
    $recent = summarizedArticle(['published_at' => now()->subHour()]);

    expect(searchIds(null))->toBe([$undatedRecent->id, $recent->id, $old->id, $undatedOld->id]);
});

test('equally relevant results fall back to the date order', function () {
    $older = summarizedArticle(['title_fr' => 'Sécurité des agents', 'published_at' => now()->subDays(4)]);
    $undated = summarizedArticle([
        'title_fr' => 'Sécurité des agents',
        'published_at' => null,
        'created_at' => now()->subHour(),
    ]);

    expect(searchIds('sécurité'))->toBe([$undated->id, $older->id]);
});
