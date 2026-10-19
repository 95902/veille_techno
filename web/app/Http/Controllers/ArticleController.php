<?php

namespace App\Http\Controllers;

use App\Enums\ArticleStatus;
use App\Models\Article;
use App\Models\Category;
use Illuminate\Http\Request;
use Inertia\Inertia;
use Inertia\Response;

/**
 * Reader pages: the summarized articles, filtered by category and searched in French.
 * Only displayed fields are sent to the page (never content, last_error, search_vector).
 */
class ArticleController extends Controller
{
    public function index(Request $request): Response
    {
        $filters = $request->validate([
            'q' => ['nullable', 'string', 'max:200'],
            'categorie' => ['nullable', 'string', 'max:64'],
        ]);
        $q = trim((string) ($filters['q'] ?? ''));
        $categorie = (string) ($filters['categorie'] ?? '');

        $articles = Article::summarized()
            ->inCategory($categorie)
            ->search($q)
            ->with(['source:id,name', 'category:id,name,slug'])
            ->paginate(20)
            ->withQueryString()
            ->through(fn (Article $article) => $this->card($article));

        $categories = Category::query()->orderBy('name')->get(['name', 'slug']);

        return Inertia::render('articles/Index', [
            'articles' => $articles,
            'categories' => $categories,
            // An unknown slug still filters to an empty list, but the select falls back to "all".
            'filters' => [
                'q' => $q,
                'categorie' => $categories->contains('slug', $categorie) ? $categorie : '',
            ],
        ]);
    }

    public function show(Article $article): Response
    {
        abort_unless($article->status === ArticleStatus::Summarized, 404);

        $article->load(['source:id,name', 'category:id,name,slug']);

        return Inertia::render('articles/Show', [
            'article' => [
                ...$this->card($article),
                'title' => $article->title,
                'url' => $article->url,
            ],
        ]);
    }

    /**
     * @return array<string, mixed>
     */
    private function card(Article $article): array
    {
        return [
            'id' => $article->id,
            'title_fr' => $article->title_fr ?: $article->title,
            'summary' => $article->summary,
            'published_at' => ($article->published_at ?? $article->created_at)?->toIso8601String(),
            'source' => $article->source?->name,
            'category' => $article->category?->only(['name', 'slug']),
        ];
    }
}
