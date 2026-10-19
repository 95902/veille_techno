<?php

namespace Tests\Pgsql;

use Illuminate\Foundation\Application;
use Illuminate\Support\Facades\DB;
use RuntimeException;
use Tests\TestCase;
use Throwable;

/**
 * Runs on the dedicated PostgreSQL test database (connection pgsql_testing), for SQL that
 * SQLite cannot run (full-text search). RefreshDatabase wipes the database it targets:
 * the connection is checked to be the test database before any trait runs, and the tests
 * are skipped when that database is unreachable.
 */
abstract class PgsqlTestCase extends TestCase
{
    public function createApplication(): Application
    {
        $app = parent::createApplication();

        $config = $app['config'];
        $config->set('database.default', 'pgsql_testing');

        // phpunit.xml overrides DB_DATABASE (":memory:"): the application database name is
        // not known here, so only a name ending in "_test" is accepted, before and after
        // connecting.
        $expected = (string) $config->get('database.connections.pgsql_testing.database');

        if (! self::isTestDatabase($expected)) {
            throw new RuntimeException(
                "Refusing to run the pgsql tests on database \"{$expected}\": its name must end with \"_test\"."
            );
        }

        try {
            $actual = DB::connection('pgsql_testing')->selectOne('SELECT current_database() AS name')->name;
        } catch (Throwable $e) {
            $this->markTestSkipped("Test database \"{$expected}\" unreachable: {$e->getMessage()}");
        }

        if ($actual !== $expected || ! self::isTestDatabase($actual)) {
            throw new RuntimeException("Connected to database \"{$actual}\", expected \"{$expected}\".");
        }

        return $app;
    }

    private static function isTestDatabase(string $name): bool
    {
        return preg_match('/^[a-z0-9_]+_test$/', $name) === 1;
    }
}
