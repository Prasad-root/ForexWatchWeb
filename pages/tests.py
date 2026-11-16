import csv
import io

from django.core import mail
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from pages import sample_data

PUBLIC = ["home", "rates", "commodities", "fuel", "stocks", "analytics", "datasets",
          "about", "methodology", "contact", "privacy", "terms"]
ADMIN_PAGES = ["admin_dashboard", "admin_users"]


class PublicPageTests(TestCase):
    def test_every_public_page_renders_for_anonymous_visitors(self):
        for name in PUBLIC:
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 200, name)
            self.assertContains(response, "ForexWatch", msg_prefix=name)

    def test_home_has_login_and_signup_links(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, reverse("account_login"))
        self.assertContains(response, reverse("account_signup"))

    def test_rates_currency_filter_and_fallback(self):
        self.assertContains(self.client.get(reverse("rates"), {"currency": "EUR"}), "EUR / LKR by bank")
        self.assertContains(self.client.get(reverse("rates"), {"currency": "nope"}), "USD / LKR by bank")

    def test_unknown_url_gets_styled_404(self):
        with self.settings(DEBUG=False, ALLOWED_HOSTS=["testserver"]):
            response = self.client.get("/does-not-exist/")
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "Page not found", status_code=404)


class DatasetDownloadTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("normal", "normal@example.com", "x")

    def test_anonymous_download_redirects_to_login(self):
        response = self.client.get(reverse("dataset_download", args=["fx-daily"]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse("account_login")))

    def test_logged_in_user_gets_csv(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("dataset_download", args=["fx-daily"]))
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])
        rows = list(csv.reader(io.StringIO(response.content.decode())))
        self.assertEqual(rows[0], ["date", "usd_lkr", "eur_lkr", "gbp_lkr"])
        self.assertEqual(len(rows), sample_data.HISTORY_DAYS + 1)

    def test_unknown_dataset_is_404(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("dataset_download", args=["nope"])).status_code, 404)


class RoleAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("normal", "normal@example.com", "x")
        cls.admin = User.objects.create_user("boss", "boss@example.com", "x", role=User.Role.ADMIN)

    def test_anonymous_is_sent_to_login_for_protected_pages(self):
        for name in ["dashboard", "user_dashboard"] + ADMIN_PAGES:
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 302, name)
            self.assertTrue(response.url.startswith(reverse("account_login")), name)

    def test_normal_user_cannot_open_admin_pages(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("user_dashboard")).status_code, 200)
        for name in ADMIN_PAGES:
            self.assertEqual(self.client.get(reverse(name)).status_code, 403, name)

    def test_admin_can_open_everything(self):
        self.client.force_login(self.admin)
        for name in ["user_dashboard"] + ADMIN_PAGES:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)

    def test_dashboard_redirects_by_role(self):
        self.client.force_login(self.user)
        self.assertRedirects(self.client.get(reverse("dashboard")), reverse("user_dashboard"))
        self.client.force_login(self.admin)
        self.assertRedirects(self.client.get(reverse("dashboard")), reverse("admin_dashboard"))

    def test_admin_can_promote_but_not_demote_self(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("admin_users"), {"user_id": self.user.pk, "role": "admin"})
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, User.Role.ADMIN)
        self.client.post(reverse("admin_users"), {"user_id": self.admin.pk, "role": "user"})
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.role, User.Role.ADMIN)

    def test_normal_user_cannot_change_roles(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("admin_users"), {"user_id": self.user.pk, "role": "admin"})
        self.assertEqual(response.status_code, 403)


class ContactFormTests(TestCase):
    def test_valid_message_is_emailed(self):
        response = self.client.post(reverse("contact"), {
            "name": "Nimal", "email": "nimal@example.com", "topic": "data", "message": "Rate looks off.",
        })
        self.assertRedirects(response, reverse("contact"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Rate looks off.", mail.outbox[0].body)

    def test_honeypot_blocks_bots(self):
        self.client.post(reverse("contact"), {
            "name": "Bot", "email": "bot@example.com", "topic": "general",
            "message": "buy now", "website": "http://spam.example",
        })
        self.assertEqual(len(mail.outbox), 0)


class SampleDataTests(TestCase):
    def test_history_ends_at_current_value_and_has_expected_length(self):
        for key, cfg in sample_data.SERIES.items():
            dates, values = sample_data.history(key)
            self.assertEqual(len(dates), sample_data.HISTORY_DAYS, key)
            self.assertAlmostEqual(values[-1], round(cfg["current"], cfg["decimals"]), places=2, msg=key)

    def test_each_currency_has_best_rates_flagged(self):
        for code in sample_data.CURRENCY_CODES:
            rows = sample_data.bank_rates(code)
            self.assertTrue(any(r["best_buy"] for r in rows), code)
            self.assertTrue(any(r["best_sell"] for r in rows), code)
            self.assertTrue(all(r["sell"] > r["buy"] for r in rows), code)
