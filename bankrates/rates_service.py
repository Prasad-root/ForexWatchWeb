"""Builds the JSON payload the rates page renders. Used by both the page and the POST endpoint."""
from datetime import date, datetime

from django.core.cache import cache

from . import forex_queries as q
from .forex_config import DEFAULTS, PALETTE, WINDOWS, bank_meta


def get_meta():
    """Available dates/currencies. Cached briefly because it's needed on every filter change."""
    return cache.get_or_set("forex:meta", q.meta, 300)


def _short(iso):
    return datetime.strptime(iso, "%Y-%m-%d").strftime("%d %b")


def _change(cur, prev):
    if cur is None or prev is None:
        return None, None
    diff = cur - prev
    return diff, (diff / prev * 100 if prev else 0.0)


def _trend_payload(hist, colors):
    """Datasets for the line chart: solid = actual, dashed = projected."""
    n, f = len(hist["dates"]), len(hist["forecast_dates"])
    datasets = []
    for bank, values in sorted(hist["series"].items()):
        code = bank_meta(bank)["code"]
        datasets.append({"bank": bank, "code": code, "label": f"{code} (actual)",
                         "color": colors[bank], "dashed": False, "data": values + [None] * f})
        projected = hist["forecast"].get(bank)
        if projected:
            last = max(i for i, v in enumerate(values) if v is not None)
            data = [None] * (n + f)
            data[last] = values[last]
            data[n:] = projected
            datasets.append({"bank": bank, "code": code, "label": f"{code} (projected)",
                             "color": colors[bank], "dashed": True, "data": data})
    return {"labels": [_short(d) for d in hist["dates"] + hist["forecast_dates"]],
            "datasets": datasets}


def build_payload(sel_date=None, currency=None, basis=None, days=None):
    """Validate the filters (falling back to defaults) and return everything the page needs."""
    meta = get_meta()
    codes = [c["code"] for c in meta["currencies"]]

    currency = str(currency or DEFAULTS["currency"]).upper()
    if currency not in codes:
        currency = DEFAULTS["currency"] if DEFAULTS["currency"] in codes else codes[0]
    if basis not in q.BASIS:
        basis = DEFAULTS["basis"]
    try:
        days = int(days)
    except (TypeError, ValueError):
        days = DEFAULTS["days"]
    if days not in WINDOWS:
        days = DEFAULTS["days"]
    if sel_date not in meta["dates"]:
        sel_date = meta["dates"][0]

    snap = q.snapshot(date.fromisoformat(sel_date), currency, basis)
    hist = q.history(currency, basis, days)

    rows = []
    for r in snap["rows"]:
        m = bank_meta(r["bank"])
        buy, sell = r["buy"], r["sell"]
        diff, pct = _change(buy, r["prev_buy"])
        rows.append({
            "bank": r["bank"], "code": m["code"], "domain": m["domain"],
            "buy": buy, "sell": sell,
            "spread": sell - buy if buy is not None and sell is not None else None,
            "change": diff, "change_pct": pct,
        })
    rows.sort(key=lambda r: -(r["buy"] if r["buy"] is not None else -1))

    buys = [r for r in rows if r["buy"] is not None]
    sells = [r for r in rows if r["sell"] is not None]
    both = [r for r in rows if r["spread"] is not None]
    best_buy = max(buys, key=lambda r: r["buy"]) if buys else None
    best_sell = min(sells, key=lambda r: r["sell"]) if sells else None
    for r in rows:
        r["is_best_buy"] = bool(best_buy) and r["buy"] == best_buy["buy"]
        r["is_best_sell"] = bool(best_sell) and r["sell"] == best_sell["sell"]

    projected_last = [v[-1] for v in hist["forecast"].values()]
    stats = {
        "best_buy": {"value": best_buy["buy"], "bank": best_buy["bank"]} if best_buy else None,
        "best_sell": {"value": best_sell["sell"], "bank": best_sell["bank"]} if best_sell else None,
        "avg_spread": sum(r["spread"] for r in both) / len(both) if both else None,
        "spread_n": len(both),
        "projection": sum(projected_last) / len(projected_last) if projected_last else None,
        "projection_n": len(projected_last),
    }

    colors = {b: PALETTE[i % len(PALETTE)] for i, b in enumerate(sorted(hist["series"]))}
    spread = sorted(
        ({"code": r["code"], "spread": r["spread"], "pct": r["spread"] / r["buy"] * 100}
         for r in both if r["buy"]),
        key=lambda x: x["spread"])

    analysis = []
    for bank, s in sorted(hist["stats"].items(), key=lambda kv: -kv[1]["latest"]):
        diff, pct = _change(s["latest"], s["first"])
        analysis.append({"bank": bank, "code": bank_meta(bank)["code"],
                         "domain": bank_meta(bank)["domain"], **s,
                         "change": diff, "change_pct": pct})

    return {
        "filters": {"date": sel_date, "currency": currency, "basis": basis, "days": days},
        "prev_date": snap["prev_date"],
        "rows": rows,
        "stats": stats,
        "trend": _trend_payload(hist, colors),
        "spread": spread,
        "analysis": analysis,
        "period": {"start": hist["start"], "end": hist["end"]},
    }
