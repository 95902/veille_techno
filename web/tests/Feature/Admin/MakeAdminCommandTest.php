<?php

use App\Models\User;
use Filament\Auth\Pages\Login;
use Illuminate\Support\Facades\Hash;
use Livewire\Livewire;

test('it creates a verified admin who can access the panel', function () {
    $this->artisan('veille:make-admin')
        ->expectsQuestion('Adresse e-mail', 'admin@example.com')
        ->expectsQuestion('Nom', 'Admin')
        ->expectsQuestion('Mot de passe', 'secret-password')
        ->expectsQuestion('Confirmez le mot de passe', 'secret-password')
        ->assertSuccessful();

    $admin = User::where('email', 'admin@example.com')->sole();

    expect($admin->name)->toBe('Admin')
        ->and($admin->is_admin)->toBeTrue()
        ->and($admin->email_verified_at)->not->toBeNull()
        ->and(Hash::check('secret-password', $admin->password))->toBeTrue();

    $this->actingAs($admin)->get('/admin')->assertOk();
});

test('the created admin can log in to the panel with the chosen password', function () {
    $this->artisan('veille:make-admin')
        ->expectsQuestion('Adresse e-mail', 'admin@example.com')
        ->expectsQuestion('Nom', 'Admin')
        ->expectsQuestion('Mot de passe', 'secret-password')
        ->expectsQuestion('Confirmez le mot de passe', 'secret-password')
        ->assertSuccessful();

    Livewire::test(Login::class)
        ->fillForm([
            'email' => 'admin@example.com',
            'password' => 'secret-password',
        ])
        ->call('authenticate')
        ->assertHasNoFormErrors()
        ->assertRedirect('/admin');

    $this->assertAuthenticatedAs(User::where('email', 'admin@example.com')->sole());
    $this->get('/admin')->assertOk();
});

test('it promotes an existing account without duplicating it', function () {
    $user = User::factory()->create(['email' => 'collab@example.com']);
    $hash = $user->password;

    $this->artisan('veille:make-admin')
        ->expectsQuestion('Adresse e-mail', 'collab@example.com')
        ->assertSuccessful();

    expect(User::where('email', 'collab@example.com')->count())->toBe(1);

    $user->refresh();

    expect($user->is_admin)->toBeTrue()
        ->and($user->password)->toBe($hash);
});

test('it refuses a mismatched password confirmation and writes nothing', function () {
    $this->artisan('veille:make-admin')
        ->expectsQuestion('Adresse e-mail', 'admin@example.com')
        ->expectsQuestion('Nom', 'Admin')
        ->expectsQuestion('Mot de passe', 'secret-password')
        ->expectsQuestion('Confirmez le mot de passe', 'other-password')
        ->assertFailed();

    expect(User::count())->toBe(0);
});
