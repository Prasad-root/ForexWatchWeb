import json
import logging

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from . import rates_service
from .forex_config import BASIS_LABELS, QUICK_CURRENCIES, WINDOWS

log = logging.getLogger(__name__)


def rates(request):
    """Page shell with the default view embedded. Later filtering goes through rates_data."""
    try:
        meta = rates_service.get_meta()
        if not meta["dates"]:
            return render(request, "pages/bankrates/rates.html", {"empty": True})
        initial = rates_service.build_payload()  # latest date, USD, TT, 30 days
    except Exception:
        log.exception("Could not load exchange rates")
        return render(request, "pages/bankrates/rates.html", {"empty": True}, status=503)

    codes = {c["code"] for c in meta["currencies"]}
    return render(request, "pages/bankrates/rates.html", {
        "meta": meta,
        "initial": initial,
        "windows": WINDOWS,
        "basis_labels": BASIS_LABELS,
        "quick": [c for c in QUICK_CURRENCIES if c in codes],
    })


@require_POST
def rates_data(request):
    """Filters arrive as a JSON body, so the page URL never changes."""
    try:
        body = json.loads(request.body or b"{}")
        if not isinstance(body, dict):
            raise ValueError
    except ValueError:
        return JsonResponse({"error": "invalid JSON"}, status=400)

    try:
        payload = rates_service.build_payload(
            body.get("date"), body.get("currency"), body.get("basis"), body.get("days"))
    except Exception:
        log.exception("Could not build rates payload")
        return JsonResponse({"error": "data unavailable"}, status=503)
    return JsonResponse(payload)