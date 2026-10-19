<?php

use App\Filament\Resources\Users\Pages\EditUser;
use App\Filament\Resources\Users\Pages\ListUsers;
use App\Models\User;
use Filament\Actions\DeleteAction;
use Filament\Actions\Testing\TestAction;
use Illuminate\Support\Facades\Gate;
use Illuminate\Validation\ValidationException;
use Livewire\Livewire;

// Policy level: the rules hold outside the Filament UI.

test('the policy refuses self-deletion', function () {
    $admin = User::factory()->admin()->create();
    User::factory()->admin()->create();

    expect(Gate::forUser($admin)->inspect('delete', $admin)->denied())->toBeTrue();
});

test('the policy refuses self-demotion', function () {
    $admin = User::factory()->admin()->create();
    User::factory()->admin()->create();

    expect(Gate::forUser($admin)->inspect('demote', $admin)->denied())->toBeTrue();
});

test('the policy refuses deleting or demoting the last admin', function () {
    $actor = User::factory()->admin()->create();
    $last = User::factory()->admin()->create();

    // Another context demoted the actor meanwhile: $last is now the only admin.
    User::whereKey($actor->id)->update(['is_admin' => false]);

    expect($last->isLastAdmin())->toBeTrue()
        ->and(Gate::forUser($actor)->inspect('delete', $last)->denied())->toBeTrue()
        ->and(Gate::forUser($actor)->inspect('demote', $last)->denied())->toBeTrue();
});

test('the policy allows an admin to delete and demote another admin', function () {
    $admin = User::factory()->admin()->create();
    $other = User::factory()->admin()->create();

    expect(Gate::forUser($admin)->allows('delete', $other))->toBeTrue()
        ->and(Gate::forUser($admin)->allows('demote', $other))->toBeTrue();
});

test('the policy refuses account management to non-admins', function () {
    $user = User::factory()->create();
    $other = User::factory()->create();

    expect(Gate::forUser($user)->allows('viewAny', User::class))->toBeFalse()
        ->and(Gate::forUser($user)->allows('create', User::class))->toBeFalse()
        ->and(Gate::forUser($user)->allows('update', $other))->toBeFalse()
        ->and(Gate::forUser($user)->allows('delete', $other))->toBeFalse();
});

// Model level: the last admin survives any write path.

test('the last admin cannot be deleted at the model level', function () {
    $admin = User::factory()->admin()->create();

    expect(fn () => $admin->delete())->toThrow(ValidationException::class);

    $this->assertModelExists($admin);
});

test('the last admin cannot be demoted at the model level', function () {
    $admin = User::factory()->admin()->create();
    $admin->is_admin = false;

    expect(fn () => $admin->save())->toThrow(ValidationException::class);

    expect($admin->fresh()->is_admin)->toBeTrue();
});

// Filament level.

test('an admin cannot delete their own account from Filament', function () {
    $admin = User::factory()->admin()->create();
    User::factory()->admin()->create();
    $this->actingAs($admin);

    Livewire::test(ListUsers::class)
        ->assertActionHidden(TestAction::make('delete')->table($admin));

    Livewire::test(EditUser::class, ['record' => $admin->getRouteKey()])
        ->assertActionHidden(DeleteAction::class);

    $this->assertModelExists($admin);
});

test('an admin cannot demote themselves from Filament', function () {
    $admin = User::factory()->admin()->create();
    User::factory()->admin()->create();
    $this->actingAs($admin);

    Livewire::test(EditUser::class, ['record' => $admin->getRouteKey()])
        ->assertFormFieldDisabled('is_admin')
        ->set('data.is_admin', false)
        ->call('save');

    expect($admin->fresh()->is_admin)->toBeTrue();
});

test('Filament refuses to delete or demote the last admin', function () {
    $actor = User::factory()->admin()->create();
    $last = User::factory()->admin()->create();
    $this->actingAs($actor);

    $page = Livewire::test(EditUser::class, ['record' => $last->getRouteKey()]);

    // Another context demoted the actor meanwhile: $last is now the only admin.
    User::whereKey($actor->id)->update(['is_admin' => false]);

    $page->fillForm(['is_admin' => false])
        ->call('save')
        ->assertHasFormErrors(['is_admin']);

    expect($last->fresh()->is_admin)->toBeTrue();

    Livewire::test(ListUsers::class)
        ->assertActionHidden(TestAction::make('delete')->table($last));

    $this->assertModelExists($last);
});
