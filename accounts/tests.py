from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount, SocialLogin
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from accounts.adapters import SocialAccountAdapter
from accounts.models import User


class AuthPageTests(TestCase):
    def test_login_and_signup_pages_have_google_button_and_form(self):
        for name in ("account_login", "account_signup"):
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 200, name)
            self.assertContains(response, "with Google")
            self.assertContains(response, "csrfmiddlewaretoken")

    def test_email_registration_creates_normal_user(self):
        response = self.client.post(reverse("account_signup"), {
            "email": "student@example.com",
            "password1": "S7rong-pass-phrase!",
            "password2": "S7rong-pass-phrase!",
        })
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(email="student@example.com")
        self.assertEqual(user.role, User.Role.USER)

    def test_email_login_works(self):
        User.objects.create_user("u1", "u1@example.com", "S7rong-pass-phrase!")
        EmailAddress.objects.create(user=User.objects.get(username="u1"), email="u1@example.com",
                                    primary=True, verified=True)
        response = self.client.post(reverse("account_login"), {
            "login": "u1@example.com", "password": "S7rong-pass-phrase!",
        })
        self.assertRedirects(response, reverse("dashboard"), fetch_redirect_response=False)

    def test_password_reset_page_uses_site_layout(self):
        response = self.client.get(reverse("account_reset_password"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ForexWatch")  # navbar from base.html

    @override_settings(
        SOCIALACCOUNT_PROVIDERS={
            "google": {
                "APP": {"client_id": "test-id", "secret": "test-secret", "key": ""},
                "SCOPE": ["profile", "email"],
            }
        }
    )
    def test_google_button_posts_to_google(self):
        response = self.client.post(reverse("google_login"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("https://accounts.google.com/"))


@override_settings(ADMIN_EMAILS=["owner@example.com"])
class AdminEmailPromotionTests(TestCase):
    def setUp(self):
        self.adapter = SocialAccountAdapter()
        self.request = RequestFactory().get("/")

    def _sociallogin(self, email, verified=True, user=None):
        return SocialLogin(
            user=user or User(),
            account=SocialAccount(provider="google", uid="123"),
            email_addresses=[EmailAddress(email=email, verified=verified, primary=True)],
        )

    def test_listed_verified_email_becomes_admin(self):
        sl = self._sociallogin("Owner@example.com")
        user = self.adapter.populate_user(self.request, sl, {"email": "Owner@example.com"})
        self.assertEqual(user.role, User.Role.ADMIN)

    def test_unlisted_email_is_normal_user(self):
        sl = self._sociallogin("someone@example.com")
        user = self.adapter.populate_user(self.request, sl, {"email": "someone@example.com"})
        self.assertEqual(user.role, User.Role.USER)

    def test_unverified_email_is_not_promoted(self):
        sl = self._sociallogin("owner@example.com", verified=False)
        user = self.adapter.populate_user(self.request, sl, {"email": "owner@example.com"})
        self.assertEqual(user.role, User.Role.USER)

    def test_existing_user_is_promoted_on_login(self):
        existing = User.objects.create_user("owner", "owner@example.com", "x")
        sl = self._sociallogin("owner@example.com", user=existing)
        self.adapter.pre_social_login(self.request, sl)
        existing.refresh_from_db()
        self.assertEqual(existing.role, User.Role.ADMIN)

    def test_superuser_is_always_admin(self):
        su = User.objects.create_superuser("root", "root@example.com", "x")
        self.assertEqual(su.role, User.Role.ADMIN)
