"""Read-only queries against the `forex_data` PostgreSQL database (raw SQL, no models)."""
from datetime import timedelta
from statistics import mean, pstdev

from django.db import connections

DB_ALIAS = "forex_data"

# "basis" = which family of rates to compare (each bank publishes several)
BASIS = {
    "Currency": ("Currency_Buy", "Currency_Sell"),   # bank notes
    "TT": ("TT_Buy", "TT_Sell"),                     # telegraphic transfer
    "Cheque": ("Cheque_Buy", "Cheque_Sell"),
}
FORECAST_DAYS = 7
FORECAST_LOOKBACK = 14

_PIVOT = """
    (max(r.rate) FILTER (WHERE r.rate_type = %(buy)s))::float8  AS buy,
    (max(r.rate) FILTER (WHERE r.rate_type = %(sell)s))::float8 AS sell
"""


def _query(sql, params=None):
    with connections[DB_ALIAS].cursor() as cur:
        cur.execute(sql, params)
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def _query_one(sql, params=None):
    rows = _query(sql, params)
    return rows[0] if rows else None


def latest_date():
    return _query_one("SELECT max(rate_date) AS d FROM exchange_rates")["d"]


def meta():
    """Dates that have data (newest first) and currencies (most widely quoted first)."""
    dates = [r["rate_date"].isoformat() for r in _query(
        "SELECT DISTINCT rate_date FROM exchange_rates ORDER BY rate_date DESC LIMIT 365")]
    currencies = _query(
        """SELECT currency_code AS code, count(DISTINCT bank_id)::int AS banks
           FROM exchange_rates GROUP BY currency_code ORDER BY banks DESC, code""")
    return {"dates": dates, "currencies": currencies}


def snapshot(rate_date, currency, basis):
    """Buy/sell per bank on one date, plus the previous available date for the change."""
    buy_t, sell_t = BASIS[basis]
    prev = _query_one(
        "SELECT max(rate_date) AS d FROM exchange_rates WHERE rate_date < %s", (rate_date,))["d"]

    def fetch(d):
        rows = _query(
            f"""SELECT b.bank_name AS bank, {_PIVOT}
                FROM exchange_rates r JOIN banks b USING (bank_id)
                WHERE r.rate_date = %(d)s AND r.currency_code = %(cur)s
                GROUP BY b.bank_name""",
            {"d": d, "cur": currency, "buy": buy_t, "sell": sell_t})
        return {r["bank"]: r for r in rows}

    now = fetch(rate_date)
    before = fetch(prev) if prev else {}
    rows = [
        {"bank": bank, "buy": r["buy"], "sell": r["sell"],
         "prev_buy": before.get(bank, {}).get("buy")}
        for bank, r in sorted(now.items())
        if r["buy"] is not None or r["sell"] is not None
    ]
    return {"prev_date": prev.isoformat() if prev else None, "rows": rows}


def _trend(points):
    """Least-squares line through (day_number, value) points -> (slope, intercept) or None."""
    if len(points) < 3:
        return None
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    mx, my = mean(xs), mean(ys)
    denom = sum((x - mx) ** 2 for x in xs)
    if denom == 0:
        return None
    slope = sum((x - mx) * (y - my) for x, y in points) / denom
    return slope, my - slope * mx


def history(currency, basis, days):
    """Daily buying rate per bank over a window, with stats and a 7-day trend projection."""
    buy_t, sell_t = BASIS[basis]
    end = latest_date()
    start = end - timedelta(days=days - 1)
    rows = _query(
        f"""SELECT r.rate_date, b.bank_name AS bank, {_PIVOT}
            FROM exchange_rates r JOIN banks b USING (bank_id)
            WHERE r.currency_code = %(cur)s AND r.rate_date BETWEEN %(start)s AND %(end)s
            GROUP BY r.rate_date, b.bank_name ORDER BY r.rate_date""",
        {"cur": currency, "buy": buy_t, "sell": sell_t, "start": start, "end": end})

    dates = sorted({r["rate_date"] for r in rows})
    index = {d: i for i, d in enumerate(dates)}
    series = {}
    for r in rows:
        if r["buy"] is not None:
            series.setdefault(r["bank"], [None] * len(dates))[index[r["rate_date"]]] = r["buy"]

    future = [end + timedelta(days=i) for i in range(1, FORECAST_DAYS + 1)]
    stats, forecast = {}, {}
    for bank, values in series.items():
        pts = [(d.toordinal(), v) for d, v in zip(dates, values) if v is not None]
        vals = [v for _, v in pts]
        stats[bank] = {
            "latest": vals[-1], "first": vals[0], "min": min(vals), "max": max(vals),
            "avg": mean(vals), "stdev": pstdev(vals) if len(vals) > 1 else 0.0,
        }
        line = _trend(pts[-FORECAST_LOOKBACK:])
        if line:
            forecast[bank] = [line[1] + line[0] * d.toordinal() for d in future]

    return {
        "start": start.isoformat(), "end": end.isoformat(),
        "dates": [d.isoformat() for d in dates],
        "series": series, "stats": stats,
        "forecast_dates": [d.isoformat() for d in future], "forecast": forecast,
    }
