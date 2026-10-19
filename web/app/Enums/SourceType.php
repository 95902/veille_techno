<?php

namespace App\Enums;

/**
 * How the worker reads a source: rss extracts each article page, arxiv uses
 * the abstract carried by the feed.
 */
enum SourceType: string
{
    case Rss = 'rss';
    case Arxiv = 'arxiv';

    public function label(): string
    {
        return match ($this) {
            self::Rss => 'RSS / Atom',
            self::Arxiv => 'arXiv',
        };
    }

    /**
     * @return array<string, string>
     */
    public static function options(): array
    {
        $options = [];

        foreach (self::cases() as $case) {
            $options[$case->value] = $case->label();
        }

        return $options;
    }
}
