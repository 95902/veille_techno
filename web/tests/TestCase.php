<?php

namespace Tests;

use Illuminate\Foundation\Application;
use Illuminate\Foundation\Testing\TestCase as BaseTestCase;
use Laravel\Fortify\Features;
use RuntimeException;

abstract class TestCase extends BaseTestCase
{
    /**
     * RefreshDatabase wipes the default connection. A cached config (config:cache, optimize)
     * ignores the phpunit.xml overrides and would point it at the application database:
     * refuse anything but in-memory SQLite before any trait runs. PgsqlTestCase switches to
     * its own guarded connection after this check.
     */
    public function createApplication(): Application
    {
        $app = parent::createApplication();

        if ($app->configurationIsCached()) {
            throw new RuntimeException(
                'Refusing to run the tests with a cached configuration ('.$app->getCachedConfigPath().'): run "php artisan config:clear".'
            );
        }

        $default = (string) $app['config']->get('database.default');
        $database = (string) $app['config']->get("database.connections.{$default}.database");

        if ($app['config']->get("database.connections.{$default}.driver") !== 'sqlite' || $database !== ':memory:') {
            throw new RuntimeException(
                "Refusing to run the tests on connection \"{$default}\" (database \"{$database}\"): in-memory SQLite expected."
            );
        }

        return $app;
    }

    protected function skipUnlessFortifyHas(string $feature, ?string $message = null): void
    {
        if (! Features::enabled($feature)) {
            $this->markTestSkipped($message ?? "Fortify feature [{$feature}] is not enabled.");
        }
    }
}
