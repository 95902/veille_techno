<?php

test('home page is served', function () {
    $this->get('/')->assertOk();
});

test('filament admin login page is served', function () {
    $this->get('/admin/login')->assertOk();
});
