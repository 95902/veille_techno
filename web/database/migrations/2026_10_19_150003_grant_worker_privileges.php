<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Support\Facades\DB;

return new class extends Migration
{
    /**
     * Grant the worker role exactly what it needs, table by table.
     *
     * Runs as veille_app (owner of the schema). The worker reads the sources and
     * categories, inserts and updates articles; nothing else, no DELETE, no DDL.
     * Older installs got blanket default privileges from the init script: they are
     * revoked first, so that no other table (users, sessions...) stays readable.
     *
     * On PostgreSQL a missing worker role fails the migration: recording it as run would
     * leave the worker with "permission denied" and the grants would never be replayed.
     */
    public function up(): void
    {
        $role = $this->workerRole(strict: true);
        if ($role === null) {
            return;
        }

        DB::statement("REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {$role}");
        DB::statement("REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM {$role}");
        // Without FOR ROLE: applies to the current role (veille_app), which creates every table.
        DB::statement("ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM {$role}");
        DB::statement("ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM {$role}");

        DB::statement("GRANT SELECT ON sources, categories TO {$role}");
        DB::statement("GRANT SELECT, INSERT, UPDATE ON articles TO {$role}");
        DB::statement("GRANT USAGE, SELECT ON SEQUENCE {$this->articlesSequence()} TO {$role}");
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        $role = $this->workerRole(strict: false);
        if ($role === null) {
            return;
        }

        DB::statement("REVOKE ALL ON sources, categories, articles FROM {$role}");
        DB::statement("REVOKE ALL ON SEQUENCE {$this->articlesSequence()} FROM {$role}");
    }

    /**
     * Quoted worker role name, or null when there is nothing to grant (SQLite, or role
     * missing on rollback). On PostgreSQL, a missing role throws when $strict.
     */
    private function workerRole(bool $strict): ?string
    {
        if (DB::getDriverName() !== 'pgsql') {
            return null;
        }

        $role = (string) config('database.connections.pgsql.worker_role');
        if (DB::selectOne('SELECT 1 FROM pg_roles WHERE rolname = ?', [$role]) === null) {
            if ($strict) {
                throw new RuntimeException(
                    "Worker role \"{$role}\" not found: create it (infra/postgres/init) before migrating."
                );
            }

            return null;
        }

        return '"'.str_replace('"', '""', $role).'"';
    }

    private function articlesSequence(): string
    {
        return DB::selectOne("SELECT pg_get_serial_sequence('articles', 'id') AS name")->name;
    }
};
