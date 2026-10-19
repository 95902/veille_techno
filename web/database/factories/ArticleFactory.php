<?php

namespace Database\Factories;

use App\Enums\ArticleStatus;
use App\Models\Article;
use App\Models\Source;
use Illuminate\Database\Eloquent\Factories\Factory;

/**
 * @extends Factory<Article>
 */
class ArticleFactory extends Factory
{
    /**
     * @return array<string, mixed>
     */
    public function definition(): array
    {
        $url = fake()->unique()->url();

        return [
            'source_id' => Source::factory(),
            'url' => $url,
            'normalized_url' => $url,
            'title' => fake()->sentence(),
            'published_at' => now()->subDay(),
            'status' => ArticleStatus::Pending,
            'attempts' => 0,
        ];
    }
}
