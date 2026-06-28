from django.contrib.auth.tokens import PasswordResetTokenGenerator


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        profile = getattr(user, "profile", None)
        email_verified = profile.email_verified if profile else False

        return (
            str(user.pk)
            + str(timestamp)
            + str(user.is_active)
            + str(email_verified)
            + str(user.email)
        )


email_verification_token = EmailVerificationTokenGenerator()