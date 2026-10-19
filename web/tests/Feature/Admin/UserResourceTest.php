<?php

use App\Filament\Resources\Users\Pages\CreateUser;
use App\Filament\Resources\Users\Pages\EditUser;
use App\Filament\Resources\Users\Pages\ListUsers;
use App\Filament\Resources\Users\UserResource;
use App\Models\User;
use Filament\Actions\DeleteAction;
use Filament\Actions\Testing\TestAction;
use Filament\Notifications\Notification as FilamentNotification;
use Illuminate\Auth\Notifications\ResetPassword;
use Illuminate\Support\Facades\Notification;
use Livewire\Livewire;

beforeEach(function () {
    $this->admin = User::factory()->admin()->create();
    $this->actingAs($this->admin);
});

test('a non-admin cannot reach the users resource', function () {
    $this->actingAs(User::factory()->create());

    $this->get(UserResource::getUrl('index'))->assertForbidden();
    $this->get(UserResource::getUrl('create'))->assertForbidden();
});

test('an admin lists the users', function () {
    $users = User::factory()->count(3)->create();

    $this->get(UserResource::getUrl('index'))->assertOk();

    Livewire::test(ListUsers::class)
        ->assertCanSeeTableRecords($users->push($this->admin));
});

test('the create form has no password field', function () {
    $this->get(UserResource::getUrl('create'))->assertOk();

    Livewire::test(CreateUser::class)
        ->assertFormFieldExists('name')
        ->assertFormFieldExists('email')
        ->assertFormFieldExists('is_admin')
        ->assertFormFieldDoesNotExist('password');
});

test('an admin creates a verified collaborator and a password setup link is sent', function () {
    Notification::fake();

    Livewire::test(CreateUser::class)
        ->fillForm([
            'name' => 'Camille Collab',
            'email' => 'camille@example.com',
        ])
        ->call('create')
        ->assertHasNoFormErrors();

    $user = User::where('email', 'camille@example.com')->sole();

    expect($user->name)->toBe('Camille Collab')
        ->and($user->is_admin)->toBeFalse()
        ->and($user->email_verified_at)->not->toBeNull()
        ->and(strlen($user->getRawOriginal('password')))->toBeGreaterThan(20);

    Notification::assertSentTo($user, ResetPassword::class);
});

test('the invited collaborator sets a password with the link and logs in without email verification', function () {
    Notification::fake();

    Livewire::test(CreateUser::class)
        ->fillForm([
            'name' => 'Camille Collab',
            'email' => 'camille@example.com',
        ])
        ->call('create')
        ->assertHasNoFormErrors();

    $user = User::where('email', 'camille@example.com')->sole();

    $token = null;
    Notification::assertSentTo($user, ResetPassword::class, function (ResetPassword $notification) use (&$token) {
        $token = $notification->token;

        return true;
    });

    auth()->logout();

    $this->get(route('password.reset', $token))->assertOk();

    $this->post(route('password.update'), [
        'token' => $token,
        'email' => 'camille@example.com',
        'password' => 'nouveau-mot-de-passe',
        'password_confirmation' => 'nouveau-mot-de-passe',
    ])->assertSessionHasNoErrors()->assertRedirect(route('login'));

    $this->post(route('login.store'), [
        'email' => 'camille@example.com',
        'password' => 'nouveau-mot-de-passe',
    ])->assertRedirect(route('dashboard', absolute: false));

    $this->assertAuthenticatedAs($user);

    // The dashboard sits behind the `verified` middleware: no verification step.
    $this->get(route('dashboard'))->assertOk();
});

test('a mixed-case email is stored lowercase and the invited user resets and logs in with it', function () {
    Notification::fake();

    Livewire::test(CreateUser::class)
        ->fillForm([
            'name' => 'Prenom Nom',
            'email' => 'Prenom.Nom@Innosys.FR',
        ])
        ->call('create')
        ->assertHasNoFormErrors();

    $user = User::whereKeyNot($this->admin->getKey())->sole();

    expect($user->email)->toBe('prenom.nom@innosys.fr');

    $token = null;
    Notification::assertSentTo($user, ResetPassword::class, function (ResetPassword $notification) use (&$token) {
        $token = $notification->token;

        return true;
    });

    auth()->logout();

    $this->post(route('password.update'), [
        'token' => $token,
        'email' => 'Prenom.Nom@Innosys.FR',
        'password' => 'nouveau-mot-de-passe',
        'password_confirmation' => 'nouveau-mot-de-passe',
    ])->assertSessionHasNoErrors()->assertRedirect(route('login'));

    $this->post(route('login.store'), [
        'email' => 'Prenom.Nom@Innosys.FR',
        'password' => 'nouveau-mot-de-passe',
    ])->assertRedirect(route('dashboard', absolute: false));

    $this->assertAuthenticatedAs($user);
    $this->get(route('dashboard'))->assertOk();
});

test('creating a user with a mixed-case variant of a taken email fails validation', function () {
    Notification::fake();
    User::factory()->create(['email' => 'taken@example.com']);

    Livewire::test(CreateUser::class)
        ->fillForm([
            'name' => 'Doublon',
            'email' => 'Taken@Example.com',
        ])
        ->call('create')
        ->assertHasFormErrors(['email' => 'unique']);

    expect(User::where('email', 'taken@example.com')->count())->toBe(1);
    Notification::assertNothingSent();
});

test('an admin edit stores the email lowercase', function () {
    $user = User::factory()->create();

    Livewire::test(EditUser::class, ['record' => $user->getRouteKey()])
        ->fillForm(['email' => 'Nouveau.Nom@Example.COM'])
        ->call('save')
        ->assertHasNoFormErrors();

    expect($user->refresh()->email)->toBe('nouveau.nom@example.com');
});

test('the invitation link is written to the log with the log mailer', function () {
    config(['mail.default' => 'log', 'mail.mailers.log.channel' => 'mail-test']);
    config(['logging.channels.mail-test' => [
        'driver' => 'single',
        'path' => storage_path('logs/mail-test.log'),
    ]]);
    @unlink(storage_path('logs/mail-test.log'));

    Livewire::test(CreateUser::class)
        ->fillForm([
            'name' => 'Camille Collab',
            'email' => 'camille@example.com',
        ])
        ->call('create')
        ->assertHasNoFormErrors();

    $log = file_get_contents(storage_path('logs/mail-test.log'));
    @unlink(storage_path('logs/mail-test.log'));

    expect($log)->toContain('camille@example.com')
        ->and($log)->toContain('/reset-password/');
});

test('an admin can create another admin', function () {
    Notification::fake();

    Livewire::test(CreateUser::class)
        ->fillForm([
            'name' => 'Second Admin',
            'email' => 'second@example.com',
            'is_admin' => true,
        ])
        ->call('create')
        ->assertHasNoFormErrors();

    expect(User::where('email', 'second@example.com')->sole()->is_admin)->toBeTrue();
});

test('creating a user with an email already taken fails validation', function () {
    Notification::fake();
    User::factory()->create(['email' => 'taken@example.com']);

    Livewire::test(CreateUser::class)
        ->fillForm([
            'name' => 'Doublon',
            'email' => 'taken@example.com',
        ])
        ->call('create')
        ->assertHasFormErrors(['email' => 'unique']);

    expect(User::where('email', 'taken@example.com')->count())->toBe(1);
    Notification::assertNothingSent();
});

test('an admin edits a collaborator', function () {
    $user = User::factory()->create();

    $this->get(UserResource::getUrl('edit', ['record' => $user]))->assertOk();

    Livewire::test(EditUser::class, ['record' => $user->getRouteKey()])
        ->fillForm([
            'name' => 'Nouveau Nom',
            'email' => 'nouveau@example.com',
            'is_admin' => true,
        ])
        ->call('save')
        ->assertHasNoFormErrors();

    $user->refresh();

    expect($user->name)->toBe('Nouveau Nom')
        ->and($user->email)->toBe('nouveau@example.com')
        ->and($user->is_admin)->toBeTrue();
});

test('an admin demotes another admin', function () {
    $other = User::factory()->admin()->create();

    Livewire::test(EditUser::class, ['record' => $other->getRouteKey()])
        ->fillForm(['is_admin' => false])
        ->call('save')
        ->assertHasNoFormErrors();

    expect($other->refresh()->is_admin)->toBeFalse();
});

test('an admin deletes a collaborator from the table', function () {
    $user = User::factory()->create();

    Livewire::test(ListUsers::class)
        ->callAction(TestAction::make('delete')->table($user));

    $this->assertModelMissing($user);
});

test('an admin deletes a collaborator from the edit page', function () {
    $user = User::factory()->create();

    Livewire::test(EditUser::class, ['record' => $user->getRouteKey()])
        ->callAction(DeleteAction::class);

    $this->assertModelMissing($user);
});

test('the resend link action sends a new password setup link', function () {
    Notification::fake();
    $user = User::factory()->create();

    Livewire::test(ListUsers::class)
        ->assertActionHasLabel(TestAction::make('sendPasswordLink')->table($user), 'Renvoyer le lien')
        ->callAction(TestAction::make('sendPasswordLink')->table($user))
        ->assertHasNoActionErrors()
        ->assertNotified();

    Notification::assertSentTo($user, ResetPassword::class);
});

test('resending the link twice in a row shows the throttled error in french', function () {
    Notification::fake();
    $user = User::factory()->create();

    Livewire::test(ListUsers::class)
        ->callAction(TestAction::make('sendPasswordLink')->table($user))
        ->assertNotified("Lien de définition du mot de passe envoyé à {$user->email}.")
        ->callAction(TestAction::make('sendPasswordLink')->table($user))
        ->assertNotified(
            FilamentNotification::make()
                ->danger()
                ->title('Le lien n\'a pas pu être envoyé.')
                ->body('Veuillez patienter avant de réessayer.'),
        );

    Notification::assertSentToTimes($user, ResetPassword::class, 1);
});
