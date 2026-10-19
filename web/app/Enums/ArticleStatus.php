<?php

namespace App\Enums;

/**
 * Lifecycle of an article, written by the Python worker: pending until the LLM
 * answers, summarized on success, failed (retried up to 3 attempts) otherwise.
 */
enum ArticleStatus: string
{
    case Pending = 'pending';
    case Summarized = 'summarized';
    case Failed = 'failed';

    public function label(): string
    {
        return match ($this) {
            self::Pending => 'En attente',
            self::Summarized => 'Résumé',
            self::Failed => 'Échec',
        };
    }
}
