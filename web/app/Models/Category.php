<?php

namespace App\Models;

use Database\Factories\CategoryFactory;
use Illuminate\Database\Eloquent\Attributes\Fillable;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Support\Carbon;
use Illuminate\Validation\ValidationException;

/**
 * @property int $id
 * @property string $name
 * @property string $slug
 * @property string|null $description
 * @property Carbon|null $created_at
 * @property Carbon|null $updated_at
 */
#[Fillable(['name', 'slug', 'description'])]
class Category extends Model
{
    /** @use HasFactory<CategoryFactory> */
    use HasFactory;

    public const IN_USE_MESSAGE = 'Cette catégorie est attribuée à des articles : elle ne peut pas être supprimée.';

    /**
     * Safety net on every write path: the foreign key already restricts the
     * delete, this turns it into a readable validation error.
     */
    protected static function booted(): void
    {
        static::deleting(function (Category $category): void {
            if ($category->isInUse()) {
                throw ValidationException::withMessages(['category' => self::IN_USE_MESSAGE]);
            }
        });
    }

    /**
     * @return HasMany<Article, $this>
     */
    public function articles(): HasMany
    {
        return $this->hasMany(Article::class);
    }

    public function isInUse(): bool
    {
        return $this->articles()->exists();
    }
}
