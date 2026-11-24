import json
import logging
import time
from urllib.parse import urlencode

from django.core import signing
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from accounts.decorators import admin_required
from accounts.models import User

from . import bank_admin
from .dag_client import NotConnected, dag
from .models import AuditLog

log = logging.getLogger(__name__)

DELETE_WAIT_SECONDS = 15       # forced pause before the final delete button unlocks
TOKEN_MAX_AGE = 300            # the confirmation must happen within 5 minutes
MAX_PASSWORD_FAILS = 5         # per 15 minutes
TOKEN_SALT = "admincontrols.bankrates.delete"

NAV = [
    {"title": "Platform", "items": [
        {"key": "overview", "label": "Overview", "url": "cp_overview"},
        {"key": "users", "label": "User management", "url": "admin_users"},
        {"key": "api_keys", "label": "API keys", "url": "cp_api_keys", "soon": True},
    ]},
    {"title": "Extractions", "items": [
        {"key": "bankrates", "label": "Bank rates", "url": "cp_bankrates"},
        {"key": "commodities", "label": "Commodities", "url": "cp_commodities", "soon": True},
        {"key": "fuel", "label": "Fuel", "url": "cp_fuel", "soon": True},
        {"key": "stocks", "label": "Stocks", "url": "cp_stocks", "soon": True},
    ]},
]

PLACEHOLDERS = {
    "api_keys": {
        "title": "API keys",
        "blurb": "Issue, rotate and revoke API keys for the public data API.",
        "planned": ["Create keys per user with scopes and rate limits", "Revoke / rotate keys",
                    "Usage per key (requests per day)", "Last-used timestamps"],
    },
    "commodities": {
        "title": "Commodities extractions",
        "blurb": "Daily extraction rows for commodity prices, same workflow as Bank rates.",
        "planned": ["Daily extraction rows (multiple runs per day)", "Click a row to inspect the data",
                    "Delete a row with password confirmation", "Extraction DAG controls"],
    },
    "fuel": {
        "title": "Fuel extractions",
        "blurb": "Daily extraction rows for fuel prices, same workflow as Bank rates.",
        "planned": ["Daily extraction rows (multiple runs per day)", "Click a row to inspect the data",
                    "Delete a row with password confirmation", "Extraction DAG controls"],
    },
    "stocks": {
        "title": "Stocks extractions",
        "blurb": "Daily extraction rows for stock market data, same workflow as Bank rates.",
        "planned": ["Daily extraction rows (multiple runs per day)", "Click a row to inspect the data",
                    "Delete a row with password confirmation", "Extraction DAG controls"],
    },
}


def _ctx(active, **extra):
    return {"nav_groups": NAV, "active": active, **extra}


def _body(request):
    try:
        data = json.loads(request.body or b"{}")
        return data if isinstance(data, dict) else {}
    except ValueError:
        return {}


def _err(message, status=400, code=""):
    return JsonResponse({"error": message, "code": code}, status=status)


# --- Pages ---------------------------------------------------------------------

@admin_required
def overview(request):
    try:
        bank = bank_admin.summary()
    except Exception:
        log.exception("bank summary failed")
        bank = None
    return render(request, "admincontrols/overview.html", _ctx(
        "overview",
        total_users=User.objects.count(),
        admin_count=User.objects.filter(role=User.Role.ADMIN).count(),
        bank=bank,
        recent=AuditLog.objects.select_related("user")[:8],
    ))


@admin_required
def placeholder(request, key):
    return render(request, "admincontrols/placeholder.html", _ctx(key, **PLACEHOLDERS[key]))


@admin_required
def bankrates(request):
    def parse(name):
        try:
            return bank_admin.parse_day(request.GET.get(name))
        except (TypeError, ValueError):
            return None

    date_from, date_to = parse("from"), parse("to")
    try:
        page = int(request.GET.get("page", 1))
    except ValueError:
        page = 1
    error = None
    try:
        result = bank_admin.list_extractions(page, 20, date_from, date_to)
    except Exception:
        log.exception("list extractions failed")
        result = {"rows": [], "page": 1, "pages": 1, "total": 0, "run_col": None}
        error = "Could not read the rates database. Check the server log."
    qs = urlencode({k: v for k, v in (("from", date_from), ("to", date_to)) if v})
    return render(request, "admincontrols/bankrates.html", _ctx(
        "bankrates", **result, has_run=bool(result["run_col"]), error=error,
        date_from=date_from, date_to=date_to, qs=qs, delete_wait=DELETE_WAIT_SECONDS,
    ))


# --- Bank rates: JSON endpoints --------------------------------------------------

def _target_from(data):
    """Validate day/run from a request. Returns (day, run) or a JsonResponse error."""
    try:
        day = bank_admin.parse_day(data.get("day"))
    except (TypeError, ValueError):
        return _err("Invalid date.")
    run = data.get("run")
    if bank_admin.run_column() and run is None:
        return _err("Missing extraction run.")
    return day, (str(run) if run is not None else None)


@admin_required
def bankrates_detail(request):
    target = _target_from({"day": request.GET.get("day"), "run": request.GET.get("run")})
    if isinstance(target, JsonResponse):
        return target
    try:
        return JsonResponse(bank_admin.detail(*target))
    except Exception:
        log.exception("detail failed")
        return _err("Could not load this extraction.", 503)


@admin_required
@require_POST
def bankrates_delete_request(request):
    """Step 1+2: check phrase and the admin's password, then issue a short-lived token."""
    body = _body(request)
    target = _target_from(body)
    if isinstance(target, JsonResponse):
        return target
    day, run = target
    user = request.user

    if not user.has_usable_password():
        return _err("Your account has no password (Google sign-in). Set a password first, "
                    "then try again.", 400, "no_password")
    key = f"cp:pwfail:{user.pk}"
    if cache.get(key, 0) >= MAX_PASSWORD_FAILS:
        return _err("Too many wrong passwords. Try again in 15 minutes.", 429, "locked")
    if str(body.get("phrase", "")).strip() != f"DELETE {day.isoformat()}":
        return _err("The confirmation phrase doesn't match.", 400, "phrase")
    if not user.check_password(str(body.get("password", ""))):
        cache.set(key, cache.get(key, 0) + 1, 900)
        return _err("Wrong password.", 403, "password")
    cache.delete(key)

    count = bank_admin.count_target(day, run)
    if count == 0:
        return _err("Nothing to delete: this extraction no longer exists.", 404)
    token = signing.dumps({"u": user.pk, "day": day.isoformat(), "run": run,
                           "n": count, "t": time.time()}, salt=TOKEN_SALT)
    return JsonResponse({"token": token, "count": count, "wait": DELETE_WAIT_SECONDS})


@admin_required
@require_POST
def bankrates_delete_confirm(request):
    """Step 3: only works after the forced wait, with a valid token for this admin."""
    try:
        data = signing.loads(str(_body(request).get("token", "")), salt=TOKEN_SALT, max_age=TOKEN_MAX_AGE)
    except signing.BadSignature:
        return _err("Confirmation expired. Start again.", 400, "expired")
    if data["u"] != request.user.pk:
        return _err("Not allowed.", 403)
    if time.time() - data["t"] < DELETE_WAIT_SECONDS:
        return _err("Please wait for the countdown to finish.", 400, "too_early")

    day, run = bank_admin.parse_day(data["day"]), data["run"]
    if bank_admin.count_target(day, run) != data["n"]:
        return _err("The data changed since you confirmed. Start again.", 409, "changed")
    try:
        deleted = bank_admin.delete_target(day, run)
    except Exception:
        log.exception("delete failed")
        return _err("Delete failed. Check the server log and the forex_admin database user.", 500)

    target = f"{day.isoformat()}" + (f" run={run}" if run else "")
    AuditLog.objects.create(user=request.user, section="bankrates", action="delete",
                            target=target, detail=f"{deleted} rows deleted")
    log.warning("ADMIN DELETE by %s: bankrates %s (%s rows)", request.user.pk, target, deleted)
    return JsonResponse({"deleted": deleted})


# --- Bank rates: DAG control (UI only for now) -------------------------------------

@admin_required
def bankrates_dag_status(request):
    return JsonResponse({"dag_id": dag.dag_id, "status": dag.status(), "runs": dag.recent_runs(10)})


@admin_required
@require_POST
def bankrates_dag_action(request):
    body = _body(request)
    action = body.get("action")
    try:
        if action == "trigger":
            dag.trigger()
        elif action == "pause":
            dag.pause()
        elif action == "resume":
            dag.resume()
        elif action == "schedule":
            cron = str(body.get("cron", "")).strip()
            if len(cron.split()) != 5:
                return _err("Enter a 5-field cron expression, e.g. 0 6 * * *")
            dag.set_schedule(cron)
        else:
            return _err("Unknown action.")
    except NotConnected:
        return _err("The extraction DAG isn't connected yet.", 501, "not_connected")
    AuditLog.objects.create(user=request.user, section="bankrates", action=f"dag.{action}",
                            target=dag.dag_id, detail=str(body.get("cron", "")))
    return JsonResponse({"ok": True})