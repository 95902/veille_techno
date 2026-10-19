<?php

namespace App\Models;

use Database\Factories\UserFactory;
use Filament\Models\Contracts\FilamentUser;
use Filament\Panel;
use Illuminate\Contracts\Auth\MustVerifyEmail;
use Illuminate\Database\Eloquent\Attributes\Fillable;
use Illuminate\Database\Eloquent\Attributes\Hidden;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Foundation\Auth\User as Authenticatable;
use Illuminate\Notifications\Notifiable;
use Illuminate\Support\Carbon;
use Illuminate\Validation\ValidationException;
use Laravel\Fortify\Contracts\PasskeyUser;
use Laravel\Fortify\PasskeyAuthenticatable;
use Laravel\Fortify\TwoFactorAuthenticatable;

/**
 * @property int $id
 * @property string $name
 * @property string $email
 * @property Carbon|null $email_verified_at
 * @property bool $is_admin
 * @property string $password
 * @property string|null $two_factor_secret
 * @property string|null $two_factor_recovery_codes
 * @property Carbon|null $two_factor_confirmed_at
 * @property string|null $remember_token
 * @property Carbon|null $created_at
 * @property Carbon|null $updated_at
 */
#[Fillable(['name', 'email', 'password'])]
#[Hidden(['password', 'two_factor_secret', 'two_factor_recovery_codes', 'remember_token'])]
class User extends Authenticatable implements FilamentUser, MustVerifyEmail, PasskeyUser
{
    /** @use HasFactory<UserFactory> */
    use HasFactory, Notifiable, PasskeyAuthenticatable, TwoFactorAuthenticatable;

    /**
     * Default attribute values, mirroring the database defaults.
     *
     * @var array<string, mixed>
     */
    protected $attributes = [
        'is_admin' => false,
    ];

    /**
     * Get the attributes that should be cast.
     *
     * @return array<string, string>
     */
    protected function casts(): array
    {
        return [
            'email_verified_at' => 'datetime',
            'is_admin' => 'boolean',
            'password' => 'hashed',
            'two_factor_confirmed_at' => 'datetime',
        ];
    }

    /**
     * Enforce the last-admin invariant on every write path, UI or not.
     */
    protected static function booted(): void
    {
        static::updating(function (User $user): void {
            if ($user->isDirty('is_admin') && ! $user->is_admin && $user->isLastAdmin()) {
                throw ValidationException::withMessages([
                    'is_admin' => 'Le dernier administrateur ne peut pas être rétrogradé.',
                ]);
            }
        });

        static::deleting(function (User $user): void {
            if ($user->isLastAdmin()) {
                throw ValidationException::withMessages([
                    'is_admin' => 'Le dernier administrateur ne peut pas être supprimé.',
                ]);
            }
        });
    }

    /**
     * Whether this account is, as stored, the only remaining administrator.
     */
    public function isLastAdmin(): bool
    {
        return $this->exists
            && (bool) $this->getOriginal('is_admin')
            && static::query()->where('is_admin', true)->whereKeyNot($this->getKey())->doesntExist();
    }

    /**
     * Only administrators may open the Filament back-office.
     */
    public function canAccessPanel(Panel $panel): bool
    {
        return $this->is_admin;
    }
}
