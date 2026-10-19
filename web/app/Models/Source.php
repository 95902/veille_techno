<?php

namespace App\Models;

use App\Enums\SourceType;
use Database\Factories\SourceFactory;
use Illuminate\Database\Eloquent\Attributes\Fillable;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Support\Carbon;

/**
 * @property int $id
 * @property string $name
 * @property string $feed_url
 * @property SourceType $type
 * @property bool $active
 * @property int $max_items_per_run
 * @property Carbon|null $created_at
 * @property Carbon|null $updated_at
 */
#[Fillable(['name', 'feed_url', 'type', 'active', 'max_items_per_run'])]
class Source extends Model
{
    /** @use HasFactory<SourceFactory> */
    use HasFactory;

    /**
     * Default attribute values, mirroring the database defaults.
     *
     * @var array<string, mixed>
     */
    protected $attributes = [
        'type' => 'rss',
        'active' => true,
        'max_items_per_run' => 20,
    ];

    /**
     * @return array<string, string>
     */
    protected function casts(): array
    {
        return [
            'type' => SourceType::class,
            'active' => 'boolean',
            'max_items_per_run' => 'integer',
        ];
    }

    /**
     * @return HasMany<Article, $this>
     */
    public function articles(): HasMany
    {
        return $this->hasMany(Article::class);
    }
}
