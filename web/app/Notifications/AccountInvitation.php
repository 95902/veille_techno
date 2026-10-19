<?php

namespace App\Notifications;

use Illuminate\Bus\Queueable;
use Illuminate\Notifications\Messages\MailMessage;
use Illuminate\Notifications\Notification;

/**
 * Invitation sent when an administrator creates an account: it carries a
 * password-broker token so the new user sets their own password.
 */
class AccountInvitation extends Notification
{
    use Queueable;

    public function __construct(public string $token) {}

    /**
     * @return array<int, string>
     */
    public function via(object $notifiable): array
    {
        return ['mail'];
    }

    public function toMail(object $notifiable): MailMessage
    {
        $email = $notifiable->getEmailForPasswordReset();
        $expire = config('auth.passwords.'.config('auth.defaults.passwords').'.expire');

        return (new MailMessage)
            ->subject('Votre compte Veille techno a été créé')
            ->greeting("Bonjour {$notifiable->name},")
            ->line('Un administrateur vient de créer votre compte sur Veille techno.')
            ->line('Pour y accéder, définissez votre mot de passe à l\'aide du bouton ci-dessous.')
            ->action('Définir mon mot de passe', $this->url($email))
            ->line("Ce lien est valable {$expire} minutes.")
            ->line('Si vous ne vous attendiez pas à cette invitation, vous pouvez ignorer cet e-mail.')
            ->salutation('L\'équipe Veille techno');
    }

    public function url(string $email): string
    {
        return route('password.reset', ['token' => $this->token, 'email' => $email]);
    }
}
