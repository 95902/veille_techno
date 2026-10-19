<?php

namespace App\Console\Commands;

use App\Models\User;
use Illuminate\Console\Attributes\Description;
use Illuminate\Console\Attributes\Signature;
use Illuminate\Console\Command;
use Illuminate\Validation\Rules\Password;

use function Laravel\Prompts\password;
use function Laravel\Prompts\text;

#[Signature('veille:make-admin')]
#[Description('Crée un compte administrateur, ou promeut un compte existant')]
class MakeAdmin extends Command
{
    /**
     * Execute the console command.
     */
    public function handle(): int
    {
        $email = text(
            label: 'Adresse e-mail',
            required: true,
            validate: ['email' => ['required', 'string', 'email', 'max:255']],
        );

        $existing = User::where('email', $email)->first();

        if ($existing !== null) {
            $existing->is_admin = true;
            $existing->save();

            $this->components->info("Le compte existant {$email} est maintenant administrateur (mot de passe inchangé).");

            return self::SUCCESS;
        }

        $name = text(
            label: 'Nom',
            required: true,
            validate: ['name' => ['required', 'string', 'max:255']],
        );

        $password = password(
            label: 'Mot de passe',
            required: true,
            validate: ['password' => ['required', 'string', Password::default()]],
        );

        $confirmation = password(
            label: 'Confirmez le mot de passe',
            required: true,
        );

        if (! hash_equals($password, $confirmation)) {
            $this->components->error('Les mots de passe ne correspondent pas. Aucun compte créé.');

            return self::FAILURE;
        }

        $user = new User([
            'name' => $name,
            'email' => $email,
            'password' => $password,
        ]);
        $user->email_verified_at = now();
        $user->is_admin = true;
        $user->save();

        $this->components->info("Administrateur {$email} créé.");

        return self::SUCCESS;
    }
}
