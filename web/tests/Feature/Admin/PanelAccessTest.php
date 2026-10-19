<?php

use App\Models\User;

test('a new user is not an admin', function () {
    $user = User::factory()->create();

    expect($user->fresh()->is_admin)->toBeFalse();
});

test('is_admin cannot be mass assigned', function () {
    $user = User::create([
        'name' => 'Intrus',
        'email' => 'intrus@example.com',
        'password' => 'password',
        'is_admin' => true,
    ]);

    expect($user->fresh()->is_admin)->toBeFalse();

    $user->update(['is_admin' => true]);

    expect($user->fresh()->is_admin)->toBeFalse();
});

test('guests are redirected to the panel login', function () {
    $this->get('/admin')->assertRedirect('/admin/login');
});

test('a non-admin user gets 403 on the admin panel', function () {
    $this->actingAs(User::factory()->create());

    $this->get('/admin')->assertForbidden();
});

test('an admin user can access the admin panel', function () {
    $this->actingAs(User::factory()->admin()->create());

    $this->get('/admin')->assertOk();
});
