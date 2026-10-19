<?php

test('the home page sends a guest to the login page', function () {
    $this->get('/')->assertRedirect(route('login'));
});

test('filament admin login page is served', function () {
    $this->get('/admin/login')->assertOk();
});
