<?php

use Laravel\Fortify\Features;

// Les comptes sont créés par l'administrateur : aucune inscription publique.

test('registration feature is disabled', function () {
    expect(Features::enabled(Features::registration()))->toBeFalse();
});

test('registration screen is not available', function () {
    $this->get('/register')->assertNotFound();
});

test('users cannot register', function () {
    $response = $this->post('/register', [
        'name' => 'Test User',
        'email' => 'test@example.com',
        'password' => 'password',
        'password_confirmation' => 'password',
    ]);

    $response->assertNotFound();
    $this->assertGuest();
    $this->assertDatabaseMissing('users', ['email' => 'test@example.com']);
});
