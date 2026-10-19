<?php

namespace App\Models;

use App\Enums\ArticleStatus;
use Database\Factories\ArticleFactory;
use Illuminate\Database\Eloquent\Builder;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Support\Carbon;

/**
 * Written by the Python worker (raw SQL, role veille_worker); Laravel only reads it.
 *
 * @property int $id
 * @property int $source_id
 * @property string $url
 * @property string $normalized_url
 * @property string $title
 * @property string|null $title_fr
 * @property string|null $content
 * @property string|null $summary
 * @property int|null $category_id
 * @property Carbon|null $published_at
 * @property ArticleStatus $status
 * @property int $attempts
 * @property string|null $last_error
 * @property Carbon|null $created_at
 * @property Carbon|null $updated_at
 */
class Article extends Model
{
    /** @use HasFactory<ArticleFactory> */
    use HasFactory;

    /**
     * Default attribute values, mirroring the database defaults.
     *
     * @var array<string, mixed>
     */
    protected $attributes = [
        'status' => 'pending',
        'attempts' => 0,
    ];

    /**
     * @return array<string, string>
     */
    protected function casts(): array
    {
        return [
            'status' => ArticleStatus::class,
            'published_at' => 'datetime',
            'attempts' => 'integer',
        ];
    }

    /**
     * @return BelongsTo<Source, $this>
     */
    public function source(): BelongsTo
    {
        return $this->belongsTo(Source::class);
    }

    /**
     * @return BelongsTo<Category, $this>
     */
    public function category(): BelongsTo
    {
        return $this->belongsTo(Category::class);
    }

    /**
     * Articles ready to read: the worker has written their summary and category.
     *
     * @param  Builder<Article>  $query
     */
    public function scopeSummarized(Builder $query): void
    {
        $query->where('status', ArticleStatus::Summarized);
    }

    /**
     * Articles of the category with this slug; no filter when the slug is empty.
     *
     * @param  Builder<Article>  $query
     */
    public function scopeInCategory(Builder $query, ?string $slug): void
    {
        if ($slug === null || $slug === '') {
            return;
        }

        $query->whereHas('category', fn (Builder $category) => $category->where('slug', $slug));
    }

    /**
     * Full-text search (PostgreSQL only, search_vector), most relevant first; then, and
     * alone without a query, most recent first: publication date, or collection date for
     * an undated article (the date shown on its card).
     *
     * @param  Builder<Article>  $query
     */
    public function scopeSearch(Builder $query, ?string $terms): void
    {
        $terms = trim((string) $terms);

        if ($terms !== '') {
            $query->whereRaw("search_vector @@ websearch_to_tsquery('fr_unaccent', ?)", [$terms])
                ->orderByRaw("ts_rank(search_vector, websearch_to_tsquery('fr_unaccent', ?)) DESC", [$terms]);
        }

        $query->orderByRaw('COALESCE(published_at, created_at) DESC')
            ->orderByDesc('id');
    }
}
