<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Support\Facades\DB;

return new class extends Migration
{
    /**
     * French full-text search, accents ignored, on the articles.
     *
     * search_vector is a generated column: PostgreSQL recomputes it whenever the worker
     * writes title_fr or summary, with no trigger and no extra grant for the worker.
     * Weights: French title A, summary B, original title C. PostgreSQL only: the SQLite
     * test database has no full-text search.
     */
    public function up(): void
    {
        if (DB::getDriverName() !== 'pgsql') {
            return;
        }

        // Trusted extension: the database owner (veille_app) may create it.
        DB::statement('CREATE EXTENSION IF NOT EXISTS unaccent');
        // No IF NOT EXISTS for a configuration; migrate:fresh (pgsql test group) drops the
        // tables but keeps it.
        if (DB::selectOne("SELECT 1 FROM pg_ts_config WHERE cfgname = 'fr_unaccent'") === null) {
            DB::statement('CREATE TEXT SEARCH CONFIGURATION fr_unaccent (COPY = french)');
        }
        DB::statement('ALTER TEXT SEARCH CONFIGURATION fr_unaccent ALTER MAPPING FOR hword, hword_part, word WITH unaccent, french_stem');

        DB::statement(<<<'SQL'
            ALTER TABLE articles ADD COLUMN search_vector tsvector GENERATED ALWAYS AS (
                setweight(to_tsvector('fr_unaccent', coalesce(title_fr, '')), 'A')
                || setweight(to_tsvector('fr_unaccent', coalesce(summary, '')), 'B')
                || setweight(to_tsvector('fr_unaccent', coalesce(title, '')), 'C')
            ) STORED
            SQL);
        DB::statement('CREATE INDEX articles_search_vector_index ON articles USING gin (search_vector)');
    }

    /**
     * Reverse the migrations. The extension stays: the init script creates it too.
     */
    public function down(): void
    {
        if (DB::getDriverName() !== 'pgsql') {
            return;
        }

        DB::statement('DROP INDEX IF EXISTS articles_search_vector_index');
        DB::statement('ALTER TABLE articles DROP COLUMN IF EXISTS search_vector');
        DB::statement('DROP TEXT SEARCH CONFIGURATION IF EXISTS fr_unaccent');
    }
};
