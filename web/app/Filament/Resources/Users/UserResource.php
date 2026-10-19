<?php

namespace App\Filament\Resources\Users;

use App\Filament\Resources\Users\Pages\CreateUser;
use App\Filament\Resources\Users\Pages\EditUser;
use App\Filament\Resources\Users\Pages\ListUsers;
use App\Filament\Resources\Users\Schemas\UserForm;
use App\Filament\Resources\Users\Tables\UsersTable;
use App\Models\User;
use App\Notifications\AccountInvitation;
use BackedEnum;
use Filament\Notifications\Notification;
use Filament\Resources\Resource;
use Filament\Schemas\Schema;
use Filament\Support\Icons\Heroicon;
use Filament\Tables\Table;
use Illuminate\Support\Facades\Password;

class UserResource extends Resource
{
    protected static ?string $model = User::class;

    protected static string|BackedEnum|null $navigationIcon = Heroicon::OutlinedUsers;

    protected static ?string $recordTitleAttribute = 'name';

    protected static ?string $modelLabel = 'utilisateur';

    protected static ?string $pluralModelLabel = 'utilisateurs';

    protected static ?string $navigationLabel = 'Utilisateurs';

    public static function form(Schema $schema): Schema
    {
        return UserForm::configure($schema);
    }

    public static function table(Table $table): Table
    {
        return UsersTable::configure($table);
    }

    public static function getPages(): array
    {
        return [
            'index' => ListUsers::route('/'),
            'create' => CreateUser::route('/create'),
            'edit' => EditUser::route('/{record}/edit'),
        ];
    }

    /**
     * Send the dedicated invitation e-mail carrying a password-broker token so
     * the user sets their own password. The broker still creates the token and
     * applies its throttle; only the notification differs from "forgot password".
     */
    public static function sendPasswordSetupLink(User $user): void
    {
        $status = Password::broker()->sendResetLink(
            ['email' => $user->email],
            function (User $user, string $token): void {
                $user->notify(new AccountInvitation($token));
            },
        );

        if ($status === Password::RESET_LINK_SENT) {
            Notification::make()
                ->success()
                ->title("Lien de définition du mot de passe envoyé à {$user->email}.")
                ->send();

            return;
        }

        Notification::make()
            ->danger()
            ->title('Le lien n\'a pas pu être envoyé.')
            ->body(__($status))
            ->send();
    }
}
