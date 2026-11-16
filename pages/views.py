from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.http import Http404, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import admin_required, user_required
from accounts.models import User

from . import sample_data as data
from .forms import ContactForm


# --- Public pages --------------------------------------------------------------

def home(request):
    dates, values = data.history("usd_lkr")
    context = {
        "snapshot": data.snapshot(),
        "top_rates": data.bank_rates("USD")[:5],
        "hero_chart": {"labels": dates[-30:], "values": values[-30:]},
        "datasets": data.DATASETS[:3],
    }
    return render(request, "pages/home.html", context)


def rates(request):
    code = request.GET.get("currency", "USD").upper()
    if code not in data.CURRENCY_CODES:
        code = "USD"
    rows = data.bank_rates(code)
    context = {
        "currencies": data.currency_overview(),
        "selected": next(c for c in data.currency_overview() if c["code"] == code),
        "rows": rows,
        "best_buy": max(rows, key=lambda r: r["buy"]),
        "best_sell": min(rows, key=lambda r: r["sell"]),
    }
    return render(request, "pages/rates.html", context)


def commodities(request):
    rows = data.commodities()
    categories = []
    for row in rows:
        if row["category"] not in categories:
            categories.append(row["category"])
    grouped = [(c, [r for r in rows if r["category"] == c]) for c in categories]
    return render(request, "pages/commodities.html", {"grouped": grouped})


def fuel(request):
    dates, p92 = data.history("petrol_92")
    _, diesel = data.history("auto_diesel")
    context = {
        "prices": data.fuel_prices(),
        "revision_date": data.fuel_revision_date(),
        "chart": {"labels": dates, "petrol": p92, "diesel": diesel},
    }
    return render(request, "pages/fuel.html", context)


def stocks(request):
    rows = data.stocks()
    ranked = sorted(rows, key=lambda r: r["change"], reverse=True)
    context = {
        "indices": data.indices(),
        "stocks": rows,
        "gainers": ranked[:3],
        "losers": list(reversed(ranked[-3:])),
    }
    return render(request, "pages/stocks.html", context)


def analytics(request):
    groups = {}
    for key, cfg in data.SERIES.items():
        groups.setdefault(cfg["group"], []).append((key, cfg["label"]))
    context = {"series": data.all_series(), "groups": groups}
    return render(request, "pages/analytics.html", context)


def datasets(request):
    return render(request, "pages/datasets.html", {"datasets": data.DATASETS})


@user_required
def dataset_download(request, slug):
    """Dataset downloads are free but need an account (login or Google)."""
    dataset = data.get_dataset(slug)
    if dataset is None:
        raise Http404
    response = HttpResponse(data.dataset_csv(dataset), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="forexwatch-{slug}.csv"'
    return response


def about(request):
    return render(request, "pages/about.html")


def methodology(request):
    return render(request, "pages/methodology.html")


def privacy(request):
    return render(request, "pages/privacy.html")


def terms(request):
    return render(request, "pages/terms.html")


def contact(request):
    initial = {}
    if request.user.is_authenticated:
        initial = {"name": request.user.get_full_name(), "email": request.user.email}
    form = ContactForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        cd = form.cleaned_data
        send_mail(
            subject=f"[{settings.SITE_NAME}] {cd['topic']} from {cd['name']}",
            message=f"From: {cd['name']} <{cd['email']}>\n\n{cd['message']}",
            from_email=None,
            recipient_list=[settings.CONTACT_EMAIL],
        )
        messages.success(request, "Thanks, your message has been sent. We'll reply by email.")
        return redirect("contact")
    return render(request, "pages/contact.html", {"form": form})


def not_found(request, exception=None):
    return render(request, "404.html", status=404)


# --- Signed-in users -----------------------------------------------------------

@user_required
def dashboard(request):
    """Send each role to its own dashboard after login."""
    if request.user.is_app_admin:
        return redirect("admin_dashboard")
    return redirect("user_dashboard")


@user_required
def user_dashboard(request):
    return render(request, "pages/user_dashboard.html", {"datasets": data.DATASETS})


# --- Admins only -----------------------------------------------------------------

@admin_required
def admin_dashboard(request):
    context = {
        "total_users": User.objects.count(),
        "admin_count": User.objects.filter(role=User.Role.ADMIN).count(),
    }
    return render(request, "pages/admin_dashboard.html", context)


@admin_required
def admin_users(request):
    if request.method == "POST":
        target = get_object_or_404(User, pk=request.POST.get("user_id"))
        new_role = request.POST.get("role")
        if new_role not in User.Role.values:
            return HttpResponseBadRequest("Unknown role")
        if target == request.user:
            messages.error(request, "You can't change your own role.")
        elif target.is_superuser:
            messages.error(request, "Superusers are always admins.")
        else:
            target.role = new_role
            target.save(update_fields=["role"])
            messages.success(request, f"{target.email or target.username} is now {target.get_role_display()}.")
        return redirect("admin_users")

    return render(request, "pages/admin_users.html", {"users": User.objects.order_by("-date_joined")})
