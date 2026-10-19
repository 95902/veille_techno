<?php

namespace Database\Seeders;

use App\Enums\SourceType;
use App\Models\Source;
use Illuminate\Database\Seeder;

class SourceSeeder extends Seeder
{
    /**
     * Starting feeds, each checked live on 2026-10-19 (HTTP 200, parsed by feedparser
     * with entries). arXiv uses export.arxiv.org: rss.arxiv.org served an empty cs.AI feed.
     * An entry with 'active' => false is seeded inactive (forced on every seeding).
     */
    public const SOURCES = [
        // Inactive: article pages return 403 and the feed only gives a lede under 150 characters.
        ['name' => 'OpenAI News', 'feed_url' => 'https://openai.com/news/rss.xml', 'active' => false],
        ['name' => 'Google DeepMind', 'feed_url' => 'https://deepmind.google/blog/rss.xml'],
        ['name' => 'Hugging Face Blog', 'feed_url' => 'https://huggingface.co/blog/feed.xml'],
        ['name' => 'arXiv cs.AI', 'feed_url' => 'https://export.arxiv.org/rss/cs.AI', 'type' => SourceType::Arxiv, 'max_items_per_run' => 10],
        ['name' => 'arXiv cs.CL', 'feed_url' => 'https://export.arxiv.org/rss/cs.CL', 'type' => SourceType::Arxiv, 'max_items_per_run' => 10],
        ['name' => 'Hacker News (IA, 100 points)', 'feed_url' => 'https://hnrss.org/newest?q=AI&points=100'],
        ['name' => 'The Verge – IA', 'feed_url' => 'https://www.theverge.com/rss/ai-artificial-intelligence/index.xml'],
        ['name' => 'MIT Technology Review – IA', 'feed_url' => 'https://www.technologyreview.com/topic/artificial-intelligence/feed'],
        ['name' => 'Simon Willison', 'feed_url' => 'https://simonwillison.net/atom/everything/'],
        ['name' => 'ActuIA', 'feed_url' => 'https://www.actuia.com/feed/'],
        ['name' => 'Le Monde Informatique – IA', 'feed_url' => 'https://www.lemondeinformatique.fr/flux-rss/thematique/intelligence-artificielle/rss.xml'],
    ];

    public function run(): void
    {
        foreach (self::SOURCES as $source) {
            Source::updateOrCreate(
                ['feed_url' => $source['feed_url']],
                [
                    'name' => $source['name'],
                    'type' => $source['type'] ?? SourceType::Rss,
                    'max_items_per_run' => $source['max_items_per_run'] ?? 20,
                    // Only a forced deactivation is written: an admin deactivation of another source survives.
                    ...(isset($source['active']) ? ['active' => $source['active']] : []),
                ],
            );
        }
    }
}
