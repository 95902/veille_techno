<?php

namespace Database\Seeders;

use App\Models\User;
use Illuminate\Database\Console\Seeds\WithoutModelEvents;
use Illuminate\Database\Seeder;

class DatabaseSeeder extends Seeder
{
    use WithoutModelEvents;

    /**
     * Seed the application's database. Safe to run again: every seeder is idempotent.
     */
    public function run(): void
    {
        $this->call([
            CategorySeeder::class,
            SourceSeeder::class,
        ]);

        // Known-password demo account: never in production, created once elsewhere.
        if (! app()->isProduction() && User::where('email', 'test@example.com')->doesntExist()) {
            User::factory()->create([
                'name' => 'Test User',
                'email' => 'test@example.com',
            ]);
        }
    }
}
