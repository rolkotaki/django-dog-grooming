from django.contrib.auth.tokens import PasswordResetTokenGenerator
import six


class AccountActivationTokenGenerator(PasswordResetTokenGenerator):
    """
    Token generator class to generate the activation token for the user registration.
    """

    def _make_hash_value(self, user, timestamp):
        """Overrides the super method to generate the token based on the pk, timestamp and is_active values."""
        return (
            six.text_type(user.pk) + six.text_type(timestamp) + six.text_type(user.is_active)
        )


account_activation_token = AccountActivationTokenGenerator()
