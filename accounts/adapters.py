from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings

from .models import User


def _has_verified_admin_email(sociallogin):
    """True if Google vouches for an email address listed in ADMIN_EMAILS."""
    return any(
        address.verified and address.email.lower() in settings.ADMIN_EMAILS
        for address in sociallogin.email_addresses
    )


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        if _has_verified_admin_email(sociallogin):
            user.role = User.Role.ADMIN
        return user

    def pre_social_login(self, request, sociallogin):
        # Existing user whose email was added to ADMIN_EMAILS later: promote on login.
        user = sociallogin.user
        if user.pk and user.role != User.Role.ADMIN and _has_verified_admin_email(sociallogin):
            user.role = User.Role.ADMIN
            user.save(update_fields=["role"])
